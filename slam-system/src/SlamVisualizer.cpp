#include "SlamVisualizer.h"
#include <vector>
#include <sstream>
#include <iomanip>
#include <iostream>

#ifdef _WIN32
#include <windows.h>
#include <winhttp.h>
#pragma comment(lib, "winhttp.lib")
#else
#include <curl/curl.h>
#endif

namespace SLAM {

// ============================================================================
// URL Parsing
// ============================================================================

void SlamVisualizer::parseUrl(const std::string& url) {
    m_host = "127.0.0.1";
    m_port = 8000;
    m_path = "/api/frame";
    m_useHttps = false;

    std::string remaining = url;

    if (remaining.rfind("https://", 0) == 0) {
        m_useHttps = true;
        remaining = remaining.substr(8);
    } else if (remaining.rfind("http://", 0) == 0) {
        m_useHttps = false;
        remaining = remaining.substr(7);
    }

    auto slashPos = remaining.find('/');
    std::string hostPort = (slashPos != std::string::npos)
        ? remaining.substr(0, slashPos) : remaining;

    if (slashPos != std::string::npos) {
        m_path = remaining.substr(slashPos);
    }

    auto colonPos = hostPort.find(':');
    if (colonPos != std::string::npos) {
        m_host = hostPort.substr(0, colonPos);
        m_port = std::stoi(hostPort.substr(colonPos + 1));
    } else {
        m_host = hostPort;
        m_port = m_useHttps ? 443 : 80;
    }
}

// ============================================================================
// Constructor / Destructor
// ============================================================================

SlamVisualizer::SlamVisualizer(const std::string& backendUrl)
    : m_running(false), m_stop(false) {
    parseUrl(backendUrl);
}

SlamVisualizer::~SlamVisualizer() {
    stop();
}

// ============================================================================
// Thread Control
// ============================================================================

void SlamVisualizer::start() {
    if (m_running.load()) {
        return;  // Already running
    }
    
    m_stop.store(false);
    m_running.store(true);
    
    // Launch sender thread
    m_sendThread = std::thread(&SlamVisualizer::senderThreadFunc, this);
}

void SlamVisualizer::stop() {
    m_stop.store(true);
    m_running.store(false);
    
    // Wake up sender thread
    m_cv.notify_all();
    
    // Wait for thread to finish
    if (m_sendThread.joinable()) {
        m_sendThread.join();
    }
}

size_t SlamVisualizer::getQueueSize() const {
    std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(m_queueMutex));
    return m_queue.size();
}

// ============================================================================
// Sender Thread Main Loop
// ============================================================================

void SlamVisualizer::senderThreadFunc() {
    while (!m_stop.load()) {
        // If auto-disabled, try to recover every ~5 seconds
        if (m_disabled.load()) {
            std::unique_lock<std::mutex> lock(m_queueMutex);
            // Drain the queue silently
            while (!m_queue.empty()) {
                m_queue.pop();
            }
            // Wait for stop signal or recovery timeout (5s)
            if (m_cv.wait_for(lock, std::chrono::seconds(5), [this] {
                return m_stop.load();
            })) {
                break;  // Stop requested
            }
            // Try recovery: attempt one probe POST
            lock.unlock();
            std::string probeJson = "{\"type\":\"probe\"}";
            bool recovered = sendHTTPPost(probeJson);
            if (recovered) {
                m_disabled.store(false);
                m_consecutiveFailures.store(0);
                std::cerr << "[Vis] Auto-recovered! Backend is reachable again." << std::endl;
            }
            continue;
        }

        FrameData frame;
        
        // Wait for data or stop signal
        {
            std::unique_lock<std::mutex> lock(m_queueMutex);
            m_cv.wait(lock, [this] {
                return !m_queue.empty() || m_stop.load();
            });
            
            if (m_stop.load() && m_queue.empty()) {
                break;  // Exit thread
            }
            
            if (m_queue.empty()) {
                continue;  // Spurious wakeup
            }
            
            // Get frame from queue
            frame = m_queue.front();
            m_queue.pop();
        }
        
        // Build JSON and send (outside lock)
        std::string json = buildJsonFromFrame(frame);
        if (!json.empty()) {
            bool ok = sendHTTPPost(json);
            if (ok) {
                m_consecutiveFailures.store(0);
            } else {
                int fails = m_consecutiveFailures.fetch_add(1) + 1;
                if (fails >= MAX_CONSECUTIVE_FAILURES) {
                    m_disabled.store(true);
                    std::cerr << "[Vis] Auto-disabled after " << fails << " consecutive POST failures."
                              << " Start the backend or this will stay disabled." << std::endl;
                    continue;  // Will drain and stop next iteration
                }
            }
        }
    }
}

// ============================================================================
// Async Push Methods (Non-blocking)
// ============================================================================

void SlamVisualizer::pushFrame(
    int frameNumber,
    int keyframeCount,
    int mapPoints,
    const cv::Mat& rgbImage,
    const cv::Mat& maskImage,
    float dynamicCoverage,
    const std::vector<cv::KeyPoint>& features) {
    
    // Auto-start on first call
    if (!m_running.load()) {
        start();
    }
    
    FrameData frame;
    frame.type = "frame_update";
    frame.frameNumber = frameNumber;
    frame.keyframeCount = keyframeCount;
    frame.mapPoints = mapPoints;
    frame.dynamicCoverage = dynamicCoverage;
    frame.timestamp = 0.0;
    
    if (!rgbImage.empty()) {
        frame.rgbImage = rgbImage.clone();
    }
    if (!maskImage.empty()) {
        frame.maskImage = maskImage.clone();
    }
    frame.features = features;
    
    // Queue the frame
    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        // Limit queue size to prevent memory explosion
        if (m_queue.size() < 30) {
            m_queue.push(frame);
        }
    }
    m_cv.notify_one();
}

void SlamVisualizer::SendFrame(
    const cv::Mat& rgbImage,
    const cv::Mat& maskImage,
    const cv::Mat& pose,
    double timestamp,
    int keyframeCount,
    int mapPoints) {
    
    // Auto-start on first call
    if (!m_running.load()) {
        start();
    }
    
    FrameData frame;
    frame.type = "frame_update";
    frame.timestamp = timestamp;
    frame.keyframeCount = keyframeCount;
    frame.mapPoints = mapPoints;
    
    if (!rgbImage.empty()) {
        frame.rgbImage = rgbImage.clone();
    }
    if (!maskImage.empty()) {
        frame.maskImage = maskImage.clone();
    }
    if (!pose.empty() && pose.rows == 4 && pose.cols == 4) {
        frame.pose = pose.clone();
    }
    
    // Calculate dynamic coverage from mask
    // Calculate dynamic coverage from mask
    // segMask: non-zero pixels = dynamic object regions
    if (!maskImage.empty()) {
        int totalPixels = maskImage.rows * maskImage.cols;
        int dynamicPixels = cv::countNonZero(maskImage);
        frame.dynamicCoverage = static_cast<float>((dynamicPixels * 100.0f) / totalPixels);
    }
    
    // Queue the frame
    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        if (m_queue.size() < 30) {
            m_queue.push(frame);
        }
    }
    m_cv.notify_one();
}

void SlamVisualizer::pushTrajectoryUpdate(const std::vector<float>& trajectoryData) {
    if (trajectoryData.empty() || !m_running.load()) {
        return;
    }
    
    FrameData frame;
    frame.type = "trajectory_update";
    frame.trajectoryData = trajectoryData;
    
    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        if (m_queue.size() < 30) {
            m_queue.push(frame);
        }
    }
    m_cv.notify_one();
}

void SlamVisualizer::SendDensePoints(const std::vector<float>& coords, int totalPoints) {
    if (coords.empty() || coords.size() < 3) {
        return;
    }

    if (!m_running.load()) {
        start();
    }

    FrameData frame;
    frame.type = "dense_points_update";
    frame.densePointsCoords = coords;
    frame.densePointsTotal = totalPoints;

    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        // Drop older dense_points_update if queue is full
        if (m_queue.size() >= 30) {
            std::queue<FrameData> newQueue;
            bool dropped = false;
            while (!m_queue.empty()) {
                FrameData f = m_queue.front();
                m_queue.pop();
                if (!dropped && f.type == "dense_points_update") {
                    dropped = true;
                    continue;
                }
                newQueue.push(f);
            }
            m_queue = newQueue;
        }
        m_queue.push(frame);
    }
    m_cv.notify_one();
    static int dp_log_count = 0;
    if (++dp_log_count <= 2 || dp_log_count % 10 == 0)
        std::cerr << "[Vis] SendDensePoints queued: " << coords.size()/3 << " sampled / " << totalPoints << " total, q=" << m_queue.size() << std::endl;
}

// ============================================================================
// JSON Building
// ============================================================================

std::string SlamVisualizer::buildJsonFromFrame(const FrameData& frame) const {
    std::stringstream jsonStream;
    
    if (frame.type == "trajectory_update") {
        // Trajectory update message
        jsonStream << "{\"type\":\"trajectory_update\",\"data\":[";
        for (size_t i = 0; i < frame.trajectoryData.size(); i++) {
            if (i > 0) jsonStream << ",";
            jsonStream << frame.trajectoryData[i];
        }
        jsonStream << "]}";
        return jsonStream.str();
    }
    
    // Map points update message
    if (frame.type == "map_points_update") {
        jsonStream << "{\"type\":\"map_points_update\",";
        jsonStream << "\"map_points_count\":" << (frame.mapPointsCoords.size() / 3) << ",";
        jsonStream << "\"map_points_coords\":[";
        for (size_t i = 0; i < frame.mapPointsCoords.size(); i++) {
            if (i > 0) jsonStream << ",";
            jsonStream << std::fixed << std::setprecision(4) << frame.mapPointsCoords[i];
        }
        jsonStream << "]}";
        return jsonStream.str();
    }

    // Dense points update message
    if (frame.type == "dense_points_update") {
        jsonStream << "{\"type\":\"dense_points_update\",";
        jsonStream << "\"point_count\":" << frame.densePointsTotal << ",";
        jsonStream << "\"coords\":[";
        for (size_t i = 0; i < frame.densePointsCoords.size(); i++) {
            if (i > 0) jsonStream << ",";
            jsonStream << std::fixed << std::setprecision(4) << frame.densePointsCoords[i];
        }
        jsonStream << "]}";
        return jsonStream.str();
    }
    
    // Frame update message
    jsonStream << "{\"type\":\"frame_update\",";
    
    // Timestamp
    if (frame.timestamp > 0) {
        jsonStream << "\"timestamp\":" << std::fixed << std::setprecision(6) << frame.timestamp << ",";
    }
    
    // Frame number
    if (frame.frameNumber > 0) {
        jsonStream << "\"frame_number\":" << frame.frameNumber << ",";
    }
    
    // Keyframe and map points count
    jsonStream << "\"keyframe_count\":" << frame.keyframeCount << ",";
    jsonStream << "\"map_points\":" << frame.mapPoints << ",";
    
    // RGB image (base64)
    if (!frame.rgbImage.empty()) {
        std::string base64 = encodeBase64(frame.rgbImage, ".jpg");
        jsonStream << "\"image_base64\":\"" << base64 << "\",";
    }
    
    // Mask image (base64)
    if (!frame.maskImage.empty()) {
        std::string base64 = encodeBase64(frame.maskImage, ".png");
        jsonStream << "\"mask_base64\":\"" << base64 << "\",";
    }
    
    // Pose (4x4 matrix)
    if (!frame.pose.empty() && frame.pose.rows == 4 && frame.pose.cols == 4) {
        jsonStream << "\"pose\":[";
        for (int i = 0; i < 4; i++) {
            jsonStream << "[";
            for (int j = 0; j < 4; j++) {
                jsonStream << std::fixed << std::setprecision(6) << frame.pose.at<float>(i, j);
                if (j < 3) jsonStream << ",";
            }
            jsonStream << "]";
            if (i < 3) jsonStream << ",";
        }
        jsonStream << "],";
    }
    
    // Dynamic coverage
    jsonStream << "\"dynamic_coverage\":" << std::fixed << std::setprecision(1) << frame.dynamicCoverage;
    
    // Features
    if (!frame.features.empty()) {
        jsonStream << ",\"features\":[";
        for (size_t i = 0; i < frame.features.size(); i++) {
            if (i > 0) jsonStream << ",";
            jsonStream << "{\"x\":" << std::fixed << std::setprecision(2) << frame.features[i].pt.x 
                       << ",\"y\":" << frame.features[i].pt.y << "}";
        }
        jsonStream << "]";
    }
    
    jsonStream << "}";
    return jsonStream.str();
}


// ============================================================================
// Send Map Points
// ============================================================================

void SlamVisualizer::SendMapPoints(const std::vector<float>& coords) {
    if (coords.empty() || coords.size() < 3) {
        return;
    }
    
    if (!m_running.load()) {
        start();
    }
    
    FrameData frame;
    frame.type = "map_points_update";
    frame.mapPointsCoords = coords;
    
    {
        std::lock_guard<std::mutex> lock(m_queueMutex);
        if (m_queue.size() >= 30) {
            std::queue<FrameData> newQueue;
            bool dropped = false;
            while (!m_queue.empty()) {
                FrameData f = m_queue.front();
                m_queue.pop();
                if (!dropped && f.type == "map_points_update") {
                    dropped = true;
                    continue;
                }
                newQueue.push(f);
            }
            m_queue = newQueue;
        }
        m_queue.push(frame);
    }
    m_cv.notify_one();
    static int smp_log_count = 0;
    if (++smp_log_count <= 2 || smp_log_count % 50 == 0)
        std::cerr << "[Vis] SendMapPoints queued: " << coords.size()/3 << " pts, q=" << m_queue.size() << std::endl;
}

// ============================================================================
// Base64 Encoding
// ============================================================================

std::string SlamVisualizer::encodeBase64(const cv::Mat& image, const std::string& format) const {
    if (image.empty()) {
        return "";
    }

    std::vector<uchar> buffer;
    cv::imencode(format, image, buffer);

    const std::string base64_chars =
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789+/";

    std::string result;
    int i = 0;
    int j = 0;
    unsigned char char_array_3[3];
    unsigned char char_array_4[4];

    for (size_t k = 0; k < buffer.size(); k++) {
        char_array_3[i++] = buffer[k];
        if (i == 3) {
            char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
            char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
            char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
            char_array_4[3] = char_array_3[2] & 0x3f;

            for (i = 0; i < 4; i++) {
                result += base64_chars[char_array_4[i]];
            }
            i = 0;
        }
    }

    if (i != 0) {
        for (j = i; j < 3; j++) {
            char_array_3[j] = '\0';
        }

        char_array_4[0] = (char_array_3[0] & 0xfc) >> 2;
        char_array_4[1] = ((char_array_3[0] & 0x03) << 4) + ((char_array_3[1] & 0xf0) >> 4);
        char_array_4[2] = ((char_array_3[1] & 0x0f) << 2) + ((char_array_3[2] & 0xc0) >> 6);
        char_array_4[3] = char_array_3[2] & 0x3f;

        for (j = 0; j < i + 1; j++) {
            result += base64_chars[char_array_4[j]];
        }

        while (i++ < 3) {
            result += '=';
        }
    }

    return result;
}

// ============================================================================
// HTTP POST (WinHTTP)
// ============================================================================

bool SlamVisualizer::sendHTTPPost(const std::string& jsonData) const {
#ifdef _WIN32
    HINTERNET hSession = WinHttpOpen(L"DS-SLAM Visualizer",
                                     WINHTTP_ACCESS_TYPE_DEFAULT_PROXY,
                                     WINHTTP_NO_PROXY_NAME,
                                     WINHTTP_NO_PROXY_BYPASS, 0);
    if (!hSession) {
        return false;
    }

    std::wstring hostW(m_host.begin(), m_host.end());
    HINTERNET hConnect = WinHttpConnect(hSession, hostW.c_str(), (INTERNET_PORT)m_port, 0);
    if (!hConnect) {
        WinHttpCloseHandle(hSession);
        return false;
    }

    std::wstring pathW(m_path.begin(), m_path.end());
    DWORD flags = m_useHttps ? WINHTTP_FLAG_SECURE : 0;
    HINTERNET hRequest = WinHttpOpenRequest(hConnect, L"POST",
                                            pathW.c_str(), NULL,
                                            WINHTTP_NO_REFERER,
                                            WINHTTP_DEFAULT_ACCEPT_TYPES,
                                            flags);
    if (!hRequest) {
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return false;
    }

    // Set timeouts to match curl path (200ms connect, 500ms total)
    // Set timeouts (500ms connect, 3000ms total — large payloads need more time)
    DWORD connectTimeout = 500;
    DWORD sendRecvTimeout = 3000;
    WinHttpSetOption(hRequest, WINHTTP_OPTION_CONNECT_TIMEOUT, &connectTimeout, sizeof(connectTimeout));
    WinHttpSetOption(hRequest, WINHTTP_OPTION_SEND_TIMEOUT, &sendRecvTimeout, sizeof(sendRecvTimeout));
    WinHttpSetOption(hRequest, WINHTTP_OPTION_RECEIVE_TIMEOUT, &sendRecvTimeout, sizeof(sendRecvTimeout));

    std::wstring contentType = L"Content-Type: application/json";
    WinHttpAddRequestHeaders(hRequest, contentType.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);

    std::wstring contentLength = L"Content-Length: " + std::to_wstring(jsonData.size());
    WinHttpAddRequestHeaders(hRequest, contentLength.c_str(), -1, WINHTTP_ADDREQ_FLAG_ADD);

    if (!WinHttpSendRequest(hRequest, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                           const_cast<char*>(jsonData.c_str()), (DWORD)jsonData.size(),
                           (DWORD)jsonData.size(), 0)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return false;
    }

    if (!WinHttpReceiveResponse(hRequest, NULL)) {
        WinHttpCloseHandle(hRequest);
        WinHttpCloseHandle(hConnect);
        WinHttpCloseHandle(hSession);
        return false;
    }

    WinHttpCloseHandle(hRequest);
    WinHttpCloseHandle(hConnect);
    WinHttpCloseHandle(hSession);
    return true;
#else
    CURL* curl = curl_easy_init();
    if (!curl) {
        return false;
    }

    std::string url = (m_useHttps ? "https://" : "http://") + m_host + ":" + std::to_string(m_port) + m_path;

    struct curl_slist* headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");

    curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
    curl_easy_setopt(curl, CURLOPT_POST, 1L);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, jsonData.c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDSIZE, jsonData.size());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT_MS, 3000L);
    curl_easy_setopt(curl, CURLOPT_CONNECTTIMEOUT_MS, 500L);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, NULL);

    CURLcode res = curl_easy_perform(curl);
    if (res != CURLE_OK) {
        static int curl_fail_count = 0;
        int fc = ++curl_fail_count;
        if (fc <= 2 || fc == MAX_CONSECUTIVE_FAILURES) {
            std::cerr << "[Vis] curl error (" << fc << "): " << curl_easy_strerror(res) << std::endl;
        }
    }

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);

    return (res == CURLE_OK);
#endif
}

} // namespace SLAM