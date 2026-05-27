#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>

using namespace std;

int main() {
    cout << "=== USB Camera Test ===" << endl;
    
    // Open camera
    cv::VideoCapture cap(0);
    if (!cap.isOpened()) {
        cerr << "[ERROR] Failed to open camera" << endl;
        return 1;
    }
    
    cout << "[OK] Camera opened successfully" << endl;
    cout << "Resolution: " << cap.get(cv::CAP_PROP_FRAME_WIDTH) << "x" << cap.get(cv::CAP_PROP_FRAME_HEIGHT) << endl;
    cout << "FPS: " << cap.get(cv::CAP_PROP_FPS) << endl;
    
    cv::Mat frame;
    int frameCount = 0;
    
    cout << endl << "Press 'q' or ESC to quit" << endl;
    
    while (true) {
        cap >> frame;
        if (frame.empty()) {
            cerr << "[ERROR] Empty frame" << endl;
            continue;
        }
        
        frameCount++;
        cv::imshow("Camera Test", frame);
        
        int key = cv::waitKey(1);
        if (key == 'q' || key == 27) {
            break;
        }
        
        if (frameCount % 30 == 0) {
            cout << "[INFO] Frames captured: " << frameCount << endl;
        }
    }
    
    cap.release();
    cv::destroyAllWindows();
    
    cout << endl << "[OK] Test completed. Total frames: " << frameCount << endl;
    return 0;
}
