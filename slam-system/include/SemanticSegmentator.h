#pragma once

/**
 * DS-SLAM M3: Semantic Segmentation C++ Interface
 *
 * Wraps ONNX Runtime to provide per-frame semantic mask inference.
 * Uses PIMPL pattern to hide ONNX Runtime types from header.
 */

#include <opencv2/opencv.hpp>
#include <string>
#include <vector>
#include <memory>

// Forward declaration - ONNX types are hidden in implementation
class SemanticSegmentatorImpl;

class SemanticSegmentator {
public:
    SemanticSegmentator(const std::string& onnxPath,
                        bool useGPU = true,
                        cv::Size inputSize = cv::Size(640, 640));

    ~SemanticSegmentator();

    cv::Mat Segment(const cv::Mat& frame);

    bool IsValid() const;
    double GetLastInferenceTime() const;
    cv::Size GetInputSize() const;

private:
    // PIMPL: Hide ONNX Runtime types from header
    std::unique_ptr<SemanticSegmentatorImpl> m_impl;
};
