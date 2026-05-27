/**
 * USB摄像头测试程序
 * 用于检测USB摄像头是否能被OpenCV正确识别和采集
 */

#include <iostream>
#include <string>
#include <opencv2/core.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/imgproc.hpp>

using namespace std;

int main(int argc, char** argv) {
    cout << "========================================" << endl;
    cout << "  USB摄像头测试程序" << endl;
    cout << "========================================" << endl;
    cout << endl;

    // 检测前5个摄像头索引
    int cameraIndex = 0;
    bool foundCamera = false;
    
    for (int i = 0; i < 5; i++) {
        cv::VideoCapture cap(i);
        if (cap.isOpened()) {
            cout << "[OK] 摄像头索引 " << i << ": 已打开" << endl;
            
            // 尝试读取一帧
            cv::Mat frame;
            cap >> frame;
            if (!frame.empty()) {
                cout << "     分辨率: " << frame.cols << "x" << frame.rows << endl;
                cout << "     通道数: " << frame.channels() << endl;
                foundCamera = true;
                cameraIndex = i;
            } else {
                cout << "     [WARN] 无法读取帧" << endl;
            }
            cap.release();
        } else {
            cout << "[FAIL] 摄像头索引 " << i << ": 未找到" << endl;
        }
    }
    
    cout << endl;
    
    if (!foundCamera) {
        cout << "[ERROR] 未找到可用的USB摄像头！" << endl;
        cout << "请检查：" << endl;
        cout << "  1. 摄像头是否正确连接" << endl;
        cout << "  2. 摄像头驱动是否安装" << endl;
        cout << "  3. 是否有其他程序占用摄像头" << endl;
        return 1;
    }
    
    cout << "========================================" << endl;
    cout << "  找到摄像头，索引: " << cameraIndex << endl;
    cout << "  正在打开摄像头画面..." << endl;
    cout << "  按 'q' 或 ESC 键退出" << endl;
    cout << "========================================" << endl;
    cout << endl;
    
    // 打开摄像头并显示画面
    cv::VideoCapture cap(cameraIndex);
    if (!cap.isOpened()) {
        cerr << "[ERROR] 无法打开摄像头索引 " << cameraIndex << endl;
        return 1;
    }
    
    // 设置分辨率（可选）
    cap.set(cv::CAP_PROP_FRAME_WIDTH, 640);
    cap.set(cv::CAP_PROP_FRAME_HEIGHT, 480);
    cap.set(cv::CAP_PROP_FPS, 30);
    
    cv::Mat frame;
    int frameCount = 0;
    
    while (true) {
        cap >> frame;
        if (frame.empty()) {
            cerr << "[ERROR] 无法读取帧" << endl;
            break;
        }
        
        frameCount++;
        
        // 显示帧率信息
        cv::Mat display = frame.clone();
        string info = "Frame: " + to_string(frameCount);
        cv::putText(display, info, cv::Point(10, 30), 
                   cv::FONT_HERSHEY_SIMPLEX, 1.0, cv::Scalar(0, 255, 0), 2);
        
        cv::imshow("USB Camera Test", display);
        
        // 按 'q' 或 ESC 退出
        int key = cv::waitKey(1);
        if (key == 'q' || key == 27) {
            break;
        }
    }
    
    cap.release();
    cv::destroyAllWindows();
    
    cout << endl;
    cout << "========================================" << endl;
    cout << "  测试完成！" << endl;
    cout << "  共采集 " << frameCount << " 帧" << endl;
    cout << "========================================" << endl;
    
    return 0;
}
