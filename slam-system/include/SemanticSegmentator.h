#pragma once

/**
 * DS-SLAM M3: Semantic Segmentation C++ Interface
 *
 * Wraps ONNX Runtime to provide per-frame semantic mask inference.
 */

#include <onnxruntime_cxx_api.h>
#include <opencv2/opencv.hpp>
#include <string>
#include <vector>
#include <chrono>

class SemanticSegmentator {
public:
    SemanticSegmentator(const std::string& onnxPath,
                        bool useGPU = true,
                        cv::Size inputSize = cv::Size(640, 640));

    ~SemanticSegmentator() = default;

    cv::Mat Segment(const cv::Mat& frame);

    bool IsValid() const { return m_valid; }
    double GetLastInferenceTime() const { return m_lastMs; }
    cv::Size GetInputSize() const { return m_inputSize; }

private:
    void Preprocess(const cv::Mat& frame, std::vector<float>& blob);

    Ort::Env m_env;
    Ort::SessionOptions m_opts;
    std::unique_ptr<Ort::Session> m_session;
    Ort::AllocatorWithDefaultOptions m_allocator;
    std::vector<const char*> m_inputNames;
    std::vector<const char*> m_outputNames;
    std::vector<int64_t> m_inputShape;
    cv::Size m_inputSize;
    bool m_valid = false;
    double m_lastMs = 0.0;
};
