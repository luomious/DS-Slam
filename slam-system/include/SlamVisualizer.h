#ifndef SLAM_VISUALIZER_H
#define SLAM_VISUALIZER_H

#include <string>
#include <atomic>
#include <mutex>
#include <condition_variable>
#include <thread>
#include <queue>
#include <vector>

#include <opencv2/opencv.hpp>

namespace SLAM {

// Frame data structure for async queue
struct FrameData {
    int frameNumber = 0;
    int keyframeCount = 0;
    int mapPoints = 0;
    double timestamp = 0.0;
    float dynamicCoverage = 0.0f;
    
    cv::Mat rgbImage;
    cv::Mat maskImage;
    cv::Mat pose;  // 4x4 matrix
    
    std::vector<cv::KeyPoint> features;
    
    // JSON type indicator
    std::string type;  // "frame_update" or "trajectory_update"
    std::vector<float> trajectoryData;  // for trajectory_update
};

class SlamVisualizer {
public:
    SlamVisualizer(const std::string& backendUrl = "http://127.0.0.1:8000/api/frame");
    ~SlamVisualizer();

    void start();
    void stop();

    bool isRunning() const { return m_running.load(); }

    // Async push methods - non-blocking, queue data for sender thread
    void pushFrame(
        int frameNumber,
        int keyframeCount,
        int mapPoints,
        const cv::Mat& rgbImage,
        const cv::Mat& maskImage = cv::Mat(),
        float dynamicCoverage = 0.0f,
        const std::vector<cv::KeyPoint>& features = std::vector<cv::KeyPoint>());

    void SendFrame(
        const cv::Mat& rgbImage,
        const cv::Mat& maskImage,
        const cv::Mat& pose,
        double timestamp,
        int keyframeCount,
        int mapPoints);

    void pushTrajectoryUpdate(const std::vector<float>& trajectoryData);

    // Get queue size for monitoring
    size_t getQueueSize() const;

private:
    // URL parsing
    std::string m_host;
    int m_port;
    std::string m_path;
    bool m_useHttps;

    // Async infrastructure
    std::atomic<bool> m_running;
    std::atomic<bool> m_stop;
    std::thread m_sendThread;
    
    std::queue<FrameData> m_queue;
    std::mutex m_queueMutex;
    std::condition_variable m_cv;

    // Methods
    void parseUrl(const std::string& url);
    void senderThreadFunc();  // Main loop of sender thread
    
    std::string encodeBase64(const cv::Mat& image, const std::string& format = ".jpg") const;
    std::string buildJsonFromFrame(const FrameData& frame) const;
    bool sendHTTPPost(const std::string& jsonData) const;
};

} // namespace SLAM

#endif // SLAM_VISUALIZER_H