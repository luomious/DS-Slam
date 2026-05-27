/**
* This file is part of ORB-SLAM3
*
* Copyright (C) 2017-2021 Carlos Campos, Richard Elvira, Juan J. Gómez Rodríguez, José M.M. Montiel and Juan D. Tardós, University of Zaragoza.
* Copyright (C) 2014-2016 Raúl Mur-Artal, José M.M. Montiel and Juan D. Tardós, University of Zaragoza.
*
* ORB-SLAM3 is free software: you can redistribute it and/or modify it under the terms of the GNU General Public
* License as published by the Free Software Foundation, either version 3 of the License, or
* (at your option) any later version.
*
* ORB-SLAM3 is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even
* the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
* GNU General Public License for more details.
*
* You should have received a copy of the GNU General Public License along with ORB-SLAM3.
* If not, see <http://www.gnu.org/licenses/>.
*/

#include<iostream>
#include<algorithm>
#include<fstream>
#include<chrono>
#include<cstdlib>

#include<opencv2/core/core.hpp>

#include<System.h>

using namespace std;

void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps);

int main(int argc, char **argv)
{
    if(argc < 5)
    {
        cerr << endl << "Usage: ./rgbd_tum path_to_vocabulary path_to_settings path_to_sequence path_to_association [path_to_onnx_model] [backend_url]" << endl;
        return 1;
    }

    // Retrieve paths to images
    vector<string> vstrImageFilenamesRGB;
    vector<string> vstrImageFilenamesD;
    vector<double> vTimestamps;
    string strAssociationFilename = string(argv[4]);
    LoadImages(strAssociationFilename, vstrImageFilenamesRGB, vstrImageFilenamesD, vTimestamps);

    // Check consistency in the number of images and depthmaps
    int nImages = vstrImageFilenamesRGB.size();
    if(vstrImageFilenamesRGB.empty())
    {
        cerr << endl << "No images found in provided path." << endl;
        return 1;
    }
    else if(vstrImageFilenamesD.size()!=vstrImageFilenamesRGB.size())
    {
        cerr << endl << "Different number of images for rgb and depth." << endl;
        return 1;
    }

    // Create SLAM system. It initializes all system threads and gets ready to process frames.
    ORB_SLAM3::System SLAM(argv[1],argv[2],ORB_SLAM3::System::RGBD,true);

#ifndef DS_SLAM_DISABLED
    // DS-SLAM M3: load segmentation model
    // Priority: 1) CLI argument  2) Derive from executable path  3) YAML default
    if (argc >= 6) {
        SLAM.InitSegmentator(argv[5]);
    } else {
        // Derive model path from executable location (argv[0])
        // Fallback order:
        //   1) exeDir + /../../../segmentation/onnx/... (from Examples/RGB-D/ up 3 levels to DS-Slam/)
        //   2) ../segmentation/onnx/... (from CWD/orbslam3/ up 1 level to DS-Slam/)
        std::string exePath(argv[0]);
        size_t lastSlash = exePath.find_last_of("/\\");
        std::string exeDir = (lastSlash != std::string::npos) ? exePath.substr(0, lastSlash) : ".";
        std::string modelPath1 = exeDir + "/../../../segmentation/onnx/yolo11n_seg_v2.onnx";
        std::string modelPath2 = "../segmentation/onnx/yolo11n_seg_v2.onnx";

        // Try exeDir-derived path first, then CWD-relative
        std::ifstream testFile(modelPath1);
        if (testFile.good()) {
            testFile.close();
            SLAM.InitSegmentator(modelPath1);
        } else {
            testFile.close();
            cout << "DS-SLAM M3: Model not found at " << modelPath1 << ", trying " << modelPath2 << endl;
            SLAM.InitSegmentator(modelPath2);
        }
    }
#endif

    // DS-SLAM M6: initialize visualizer
    // Priority: 1) CLI arg 6  2) env DS_SLAM_BACKEND_URL  3) default http://127.0.0.1:8000/api/frame
    {
        std::string vizUrl;
        if (argc >= 7) {
            vizUrl = argv[6];
        } else {
            const char* envUrl = std::getenv("DS_SLAM_BACKEND_URL");
            if (envUrl && envUrl[0] != '\0') {
                vizUrl = envUrl;
            }
        }
        if (!vizUrl.empty()) {
            SLAM.InitVisualizer(vizUrl);
            cout << "DS-SLAM M6: Visualizer URL: " << vizUrl << endl;
        } else {
            SLAM.InitVisualizer();
        }
    }

    float imageScale = SLAM.GetImageScale();

    // Vector for tracking time statistics
    vector<float> vTimesTrack;
    vTimesTrack.resize(nImages);

    cout << endl << "-------" << endl;
    cout << "Start processing sequence ..." << endl;
    cout << "Images in the sequence: " << nImages << endl << endl;

    // Main loop
    cv::Mat imRGB, imD;
    for(int ni=0; ni<nImages; ni++)
    {
        // Read image and depthmap from file
        imRGB = cv::imread(string(argv[3])+"/"+vstrImageFilenamesRGB[ni],cv::IMREAD_UNCHANGED); //,cv::IMREAD_UNCHANGED);
        imD = cv::imread(string(argv[3])+"/"+vstrImageFilenamesD[ni],cv::IMREAD_UNCHANGED); //,cv::IMREAD_UNCHANGED);
        double tframe = vTimestamps[ni];

        if(imRGB.empty())
        {
            cerr << endl << "Failed to load image at: "
                 << string(argv[3]) << "/" << vstrImageFilenamesRGB[ni] << endl;
            return 1;
        }

        if(imageScale != 1.f)
        {
            int width = imRGB.cols * imageScale;
            int height = imRGB.rows * imageScale;
            cv::resize(imRGB, imRGB, cv::Size(width, height));
            cv::resize(imD, imD, cv::Size(width, height));
        }

#ifdef COMPILEDWITHC11
        std::chrono::steady_clock::time_point t1 = std::chrono::steady_clock::now();
#else
        std::chrono::steady_clock::time_point t1 = std::chrono::steady_clock::now();
#endif

        // Pass the image to the SLAM system
        SLAM.TrackRGBD(imRGB,imD,tframe);

#ifdef COMPILEDWITHC11
        std::chrono::steady_clock::time_point t2 = std::chrono::steady_clock::now();
#else
        std::chrono::steady_clock::time_point t2 = std::chrono::steady_clock::now();
#endif

        double ttrack= std::chrono::duration_cast<std::chrono::duration<double> >(t2 - t1).count();

        vTimesTrack[ni]=ttrack;

        // Wait to load the next frame
        double T=0;
        if(ni<nImages-1)
            T = vTimestamps[ni+1]-tframe;
        else if(ni>0)
            T = tframe-vTimestamps[ni-1];

        if(ttrack<T)
            usleep((T-ttrack)*1e6);
    }

    // Stop all threads
    SLAM.Shutdown();

    // Tracking time statistics
    sort(vTimesTrack.begin(),vTimesTrack.end());
    float totaltime = 0;
    for(int ni=0; ni<nImages; ni++)
    {
        totaltime+=vTimesTrack[ni];
    }
    cout << "-------" << endl << endl;
    cout << "median tracking time: " << vTimesTrack[nImages/2] << endl;
    cout << "mean tracking time: " << totaltime/nImages << endl;

    // Save camera trajectory
    // Use dataset path (argv[3]) as base directory for output files
    std::string datasetPath(argv[3]);
    // Remove trailing slash if present
    if (!datasetPath.empty() && (datasetPath.back() == '/' || datasetPath.back() == '\\')) {
        datasetPath.pop_back();
    }
    
    SLAM.SaveTrajectoryTUM(datasetPath + "/CameraTrajectory.txt");
    SLAM.SaveKeyFrameTrajectoryTUM(datasetPath + "/KeyFrameTrajectory.txt");

#ifndef DS_SLAM_DISABLED
    // DS-SLAM M5: save static map to dataset directory
    SLAM.SaveStaticMap(datasetPath + "/maps/static_map.ply", datasetPath + "/maps/grid_map.png");
#endif

    // DS-SLAM M6: stop visualizer
    if (SLAM.GetVisualizer()) {
        SLAM.GetVisualizer()->stop();
    }

    return 0;
}

void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps)
{
    ifstream fAssociation;
    fAssociation.open(strAssociationFilename.c_str());
    while(!fAssociation.eof())
    {
        string s;
        getline(fAssociation,s);
        if(!s.empty())
        {
            stringstream ss;
            ss << s;
            double t;
            string sRGB, sD;
            ss >> t;
            vTimestamps.push_back(t);
            ss >> sRGB;
            vstrImageFilenamesRGB.push_back(sRGB);
            ss >> t;
            ss >> sD;
            vstrImageFilenamesD.push_back(sD);

        }
    }
}
