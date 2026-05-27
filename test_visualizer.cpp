#include <iostream>
#include "slam-system/include/SlamVisualizer.h"
#include <opencv2/opencv.hpp>
#include <thread>
#include <chrono>

int main() {
    std::cout << "Testing SlamVisualizer HTTP push..." << std::endl;
    
    // Create visualizer pointing to localhost:8000
    slam::SlamVisualizer viz("http://127.0.0.1:8000/api/frame");
    
    // Create a simple test image (640x480 red image)
    cv::Mat testImage = cv::Mat::zeros(480, 640, CV_8UC3);
    cv::rectangle(testImage, cv::Point(100, 100), cv::Point(300, 300), 
                  cv::Scalar(0, 0, 255), -1);
    
    // Create a simple mask
    cv::Mat testMask = cv::Mat::zeros(480, 640, CV_8UC1);
    cv::circle(testMask, cv::Point(320, 240), 100, cv::Scalar(255), -1);
    
    // Create identity pose matrix
    cv::Mat Tcw = cv::Mat::eye(4, 4, CV_32F);
    Tcw.at<float>(0, 3) = 1.0f;
    Tcw.at<float>(1, 3) = 2.0f;
    Tcw.at<float>(2, 3) = 3.0f;
    
    std::cout << "Sending test frame..." << std::endl;
    
    // Send frame
    viz.SendFrame(testImage, testMask, Tcw, 
                  1234567890.123, 5, 100);
    
    // Wait for processing
    std::this_thread::sleep_for(std::chrono::seconds(2));
    
    std::cout << "Queue size: " << viz.GetQueueSize() << std::endl;
    std::cout << "Connected: " << (viz.IsConnected() ? "Yes" : "No") << std::endl;
    
    std::cout << "Test complete." << std::endl;
    return 0;
}
