#include <iostream>
#include "orbslam3/include/System.h"
#include <opencv2/opencv.hpp>

int main() {
    std::cout << "Testing ORB-SLAM3 initialization..." << std::endl;
    
    try {
        std::cout << "Loading vocabulary..." << std::endl;
        
        // Create SLAM system (RGB-D mode = 3)
        ORB_SLAM3::System SLAM(
            "E:/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Vocabulary/ORBvoc.txt",
            "E:/VSCode/VSCode-Workspace/DS-Slam/orbslam3/Examples/RGB-D/TUM1_light.yaml",
            ORB_SLAM3::System::RGBD,
            false,  // no viewer
            0,      // no map load
            "test"
        );
        
        std::cout << "SLAM system initialized successfully!" << std::endl;
        std::cout << "Initializing visualizer..." << std::endl;
        
        SLAM.InitVisualizer("http://127.0.0.1:8000/api/frame");
        
        auto* viz = SLAM.GetVisualizer();
        if (viz) {
            std::cout << "Visualizer initialized: " 
                      << (viz->IsConnected() ? "Connected" : "Not connected") 
                      << std::endl;
        } else {
            std::cout << "Visualizer not available" << std::endl;
        }
        
        std::cout << "Test complete - shutting down..." << std::endl;
        SLAM.Shutdown();
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
