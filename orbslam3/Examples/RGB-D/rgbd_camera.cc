/**
 * USB Camera RGB-D SLAM - Real-time 3D Mapping
 * 
 * This program captures RGB frames from a USB camera (e.g., Orbbec Astra Pro)
 * and runs ORB-SLAM3 with semantic segmentation for real-time 3D mapping.
 * 
 * Usage:
 *   ./rgbd_camera path_to_vocabulary path_to_settings [camera_index] [onnx_model] [backend_url]
 * 
 * Examples:
 *   ./rgbd_camera ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/TUM3.yaml
 *   ./rgbd_camera ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/TUM3.yaml 0 ../../../segmentation/onnx/yolo11n_seg_v2.onnx
 * 
 * Controls:
 *   Press 'q' or ESC to quit
 *   Press 's' to save current map
 *   Press 'p' to pause/resume tracking
 */

#include <iostream>
#include <algorithm>
#include <fstream>
#include <chrono>
#include <ctime>
#include <sstream>
#include <iomanip>

#ifndef _WIN32
#include <signal.h>
#endif

#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>

#include <System.h>

using namespace std;

bool b_continue_session = true;
bool b_pause_tracking = false;

#ifndef _WIN32
void exit_loop_handler(int s) {
    cout << endl << "[Camera] Finishing session..." << endl;
    b_continue_session = false;
}
#endif

string getCurrentTimestamp() {
    auto now = chrono::system_clock::now();
    auto time_t = chrono::system_clock::to_time_t(now);
    auto ms = chrono::duration_cast<chrono::milliseconds>(now.time_since_epoch()) % 1000;
    
    ostringstream oss;
    oss << put_time(localtime(&time_t), "%Y%m%d_%H%M%S");
    oss << "_" << setfill('0') << setw(3) << ms.count();
    return oss.str();
}

int main(int argc, char **argv) {
    cout << "========================================" << endl;
    cout << "  DS-SLAM USB Camera Real-time Mapping" << endl;
    cout << "========================================" << endl;
    cout << endl;

    if (argc < 3) {
        cerr << endl;
        cerr << "Usage: ./rgbd_camera path_to_vocabulary path_to_settings [camera_index] [onnx_model] [backend_url]" << endl;
        cerr << endl;
        cerr << "Arguments:" << endl;
        cerr << "  path_to_vocabulary   - ORB vocabulary file (ORBvoc.txt)" << endl;
        cerr << "  path_to_settings     - Camera configuration YAML file" << endl;
        cerr << "  camera_index         - USB camera index (default: 0)" << endl;
        cerr << "  onnx_model           - YOLO segmentation model path (optional)" << endl;
        cerr << "  backend_url          - Visualization backend URL (optional)" << endl;
        cerr << endl;
        cerr << "Examples:" << endl;
        cerr << "  ./rgbd_camera ../../Vocabulary/ORBvoc.txt ../../Examples/RGB-D/TUM3.yaml" << endl;
        cerr << "  ./rgbd_camera ../../Vocabulary/ORBvoc.txt TUM3.yaml 0 ../../../segmentation/onnx/yolo11n_seg_v2.onnx" << endl;
        cerr << endl;
        return 1;
    }

#ifndef _WIN32
    struct sigaction sigIntHandler;
    sigIntHandler.sa_handler = exit_loop_handler;
    sigemptyset(&sigIntHandler.sa_mask);
    sigIntHandler.sa_flags = 0;
    sigaction(SIGINT, &sigIntHandler, NULL);
#endif

    int cameraIndex = 0;
    if (argc >= 4) {
        cameraIndex = atoi(argv[3]);
    }

    cout << "[Camera] Opening USB camera (index: " << cameraIndex << ")..." << endl;
    
    cv::VideoCapture cap(cameraIndex);
    if (!cap.isOpened()) {
        cerr << "[ERROR] Failed to open camera with index " << cameraIndex << endl;
        cerr << "Please check:" << endl;
        cerr << "  1. Camera is properly connected" << endl;
        cerr << "  2. Camera driver is installed" << endl;
        cerr << "  3. No other application is using the camera" << endl;
        return 1;
    }

    cap.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    cap.set(cv::CAP_PROP_FPS, 30);

    int width = cap.get(cv::CAP_PROP_FRAME_WIDTH);
    int height = cap.get(cv::CAP_PROP_FRAME_HEIGHT);
    double fps = cap.get(cv::CAP_PROP_FPS);
    
    cout << "[OK] Camera opened successfully!" << endl;
    cout << "     Resolution: " << width << "x" << height << endl;
    cout << "     FPS: " << fps << endl;
    cout << endl;

    cout << "[SLAM] Initializing ORB-SLAM3 system..." << endl;
    
    ORB_SLAM3::System SLAM(argv[1], argv[2], ORB_SLAM3::System::RGBD, true);

#ifndef DS_SLAM_DISABLED
    if (argc >= 5) {
        cout << "[M3] Loading segmentation model: " << argv[4] << endl;
        SLAM.InitSegmentator(argv[4]);
    } else {
        string exePath(argv[0]);
        size_t lastSlash = exePath.find_last_of("/\\");
        string exeDir = (lastSlash != string::npos) ? exePath.substr(0, lastSlash) : ".";
        string modelPath1 = exeDir + "/../../../segmentation/onnx/yolo11n_seg_v2.onnx";
        string modelPath2 = "../segmentation/onnx/yolo11n_seg_v2.onnx";

        ifstream testFile(modelPath1);
        if (testFile.good()) {
            testFile.close();
            cout << "[M3] Loading segmentation model: " << modelPath1 << endl;
            SLAM.InitSegmentator(modelPath1);
        } else {
            testFile.close();
            cout << "[M3] Model not found at " << modelPath1 << ", trying " << modelPath2 << endl;
            SLAM.InitSegmentator(modelPath2);
        }
    }
#endif

    {
        string vizUrl;
        if (argc >= 6) {
            vizUrl = argv[5];
        } else {
            const char* envUrl = getenv("DS_SLAM_BACKEND_URL");
            if (envUrl && envUrl[0] != '\0') {
                vizUrl = envUrl;
            }
        }
        if (!vizUrl.empty()) {
            SLAM.InitVisualizer(vizUrl);
            cout << "[M6] Visualizer URL: " << vizUrl << endl;
        } else {
            SLAM.InitVisualizer();
        }
    }

    float imageScale = SLAM.GetImageScale();

    cout << endl;
    cout << "========================================" << endl;
    cout << "  Controls:" << endl;
    cout << "  Press 'q' or ESC - Quit" << endl;
    cout << "  Press 's'         - Save map" << endl;
    cout << "  Press 'p'         - Pause/Resume" << endl;
    cout << "========================================" << endl;
    cout << endl;

    cv::Mat imRGB, imD;
    int frameCount = 0;
    int keyframeCount = 0;
    vector<float> vTimesTrack;

    cv::namedWindow("DS-SLAM USB Camera", cv::WINDOW_AUTOSIZE);
    cv::namedWindow("Depth View", cv::WINDOW_AUTOSIZE);

    double timestamp = 0.0;
    auto startTime = chrono::steady_clock::now();

    while (b_continue_session) {
        auto frameStart = chrono::steady_clock::now();

        cap >> imRGB;
        if (imRGB.empty()) {
            cerr << "[WARN] Failed to grab frame" << endl;
            continue;
        }

        auto now = chrono::steady_clock::now();
        timestamp = chrono::duration<double>(now - startTime).count();

        if (b_pause_tracking) {
            cv::Mat displayPause = imRGB.clone();
            cv::putText(displayPause, "PAUSED", cv::Point(10, 30),
                       cv::FONT_HERSHEY_SIMPLEX, 1.0, cv::Scalar(0, 0, 255), 2);
            cv::imshow("DS-SLAM USB Camera", displayPause);
            
            int key = cv::waitKey(1);
            if (key == 'p' || key == 27 || key == 'q') {
                if (key == 'p') b_pause_tracking = false;
                else if (key == 27 || key == 'q') b_continue_session = false;
            }
            continue;
        }

        imD = cv::Mat::zeros(imRGB.rows, imRGB.cols, CV_16UC1);

        if (imageScale != 1.f) {
            int newWidth = imRGB.cols * imageScale;
            int newHeight = imRGB.rows * imageScale;
            cv::resize(imRGB, imRGB, cv::Size(newWidth, newHeight));
            cv::resize(imD, imD, cv::Size(newWidth, newHeight));
        }

        auto t1 = chrono::steady_clock::now();

        SLAM.TrackRGBD(imRGB, imD, timestamp);

        auto t2 = chrono::steady_clock::now();
        double ttrack = chrono::duration<double>(t2 - t1).count();
        vTimesTrack.push_back(ttrack);

        frameCount++;

        cv::Mat display = imRGB.clone();
        
        ostringstream info;
        info << "Frame: " << frameCount;
        cv::putText(display, info.str(), cv::Point(10, 30),
                   cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(0, 255, 0), 2);
        
        ostringstream timeInfo;
        timeInfo << fixed << setprecision(3) << "Track: " << ttrack << "s";
        cv::putText(display, timeInfo.str(), cv::Point(10, 60),
                   cv::FONT_HERSHEY_SIMPLEX, 0.7, cv::Scalar(0, 255, 0), 2);

        cv::imshow("DS-SLAM USB Camera", display);
        cv::imshow("Depth View", imD);

        int key = cv::waitKey(1);
        if (key == 'q' || key == 27) {
            b_continue_session = false;
        } else if (key == 's') {
            string timestamp = getCurrentTimestamp();
            string outputDir = "output_" + timestamp;
            
            cout << endl << "[Save] Saving map to: " << outputDir << endl;
            
            SLAM.SaveTrajectoryTUM(outputDir + "/CameraTrajectory.txt");
            SLAM.SaveKeyFrameTrajectoryTUM(outputDir + "/KeyFrameTrajectory.txt");

#ifndef DS_SLAM_DISABLED
            SLAM.SaveStaticMap(outputDir + "/static_map.ply", outputDir + "/grid_map.png");
#endif
            cout << "[Save] Map saved successfully!" << endl;
        } else if (key == 'p') {
            b_pause_tracking = true;
            cout << endl << "[Pause] Tracking paused. Press 'p' to resume." << endl;
        }

        if (frameCount % 30 == 0) {
            cout << "[Status] Frame #" << frameCount 
                 << ", Track time: " << fixed << setprecision(3) << ttrack << "s" << endl;
        }
    }

    cout << endl << "[SLAM] Shutting down..." << endl;
    SLAM.Shutdown();

    if (!vTimesTrack.empty()) {
        sort(vTimesTrack.begin(), vTimesTrack.end());
        float totaltime = 0;
        for (float t : vTimesTrack) {
            totaltime += t;
        }
        cout << endl << "========================================" << endl;
        cout << "  Statistics:" << endl;
        cout << "  Total frames: " << frameCount << endl;
        cout << "  Median tracking time: " << vTimesTrack[frameCount / 2] << "s" << endl;
        cout << "  Mean tracking time: " << totaltime / frameCount << "s" << endl;
        cout << "========================================" << endl;
    }

    string outputTimestamp = getCurrentTimestamp();
    string finalOutputDir = "output_" + outputTimestamp;
    
    cout << endl << "[Save] Saving final trajectory to: " << finalOutputDir << endl;
    SLAM.SaveTrajectoryTUM(finalOutputDir + "/CameraTrajectory.txt");
    SLAM.SaveKeyFrameTrajectoryTUM(finalOutputDir + "/KeyFrameTrajectory.txt");

#ifndef DS_SLAM_DISABLED
    SLAM.SaveStaticMap(finalOutputDir + "/static_map.ply", finalOutputDir + "/grid_map.png");
#endif

    if (SLAM.GetVisualizer()) {
        SLAM.GetVisualizer()->stop();
    }

    cap.release();
    cv::destroyAllWindows();

    cout << endl << "[Done] Session finished successfully!" << endl;

    return 0;
}
