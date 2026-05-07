/**
 * DS-SLAM M3: SemanticSegmentator test program
 */
#include "SemanticSegmentator.h"
#include <iostream>
#include <filesystem>

int main(int argc, char** argv) {
    if (argc < 3) {
        std::cerr << "Usage: test_segmentator.exe <model.onnx> <image.jpg>" << std::endl;
        return 1;
    }

    std::string onnxPath = argv[1];
    std::string imagePath = argv[2];

    if (!std::filesystem::exists(onnxPath)) {
        std::cerr << "ONNX model not found: " << onnxPath << std::endl;
        return 1;
    }

    SemanticSegmentator seg(onnxPath, false);
    if (!seg.IsValid()) {
        std::cerr << "Failed to load model!" << std::endl;
        return 1;
    }
    std::cout << "Model loaded. Input size: "
              << seg.GetInputSize().width << "x"
              << seg.GetInputSize().height << std::endl;

    cv::Mat frame = cv::imread(imagePath);
    if (frame.empty()) {
        std::cerr << "Cannot read image: " << imagePath << std::endl;
        return 1;
    }
    std::cout << "Image: " << frame.cols << "x" << frame.rows << std::endl;

    // Warmup
    seg.Segment(frame);

    // Benchmark
    auto t0 = std::chrono::high_resolution_clock::now();
    cv::Mat mask = seg.Segment(frame);
    auto t1 = std::chrono::high_resolution_clock::now();

    double ms = std::chrono::duration<double, std::milli>(t1 - t0).count();
    std::cout << "Inference: " << ms << " ms" << std::endl;
    std::cout << "Mask: " << mask.cols << "x" << mask.rows
              << ", channels=" << mask.channels()
              << ", non-zero=" << cv::countNonZero(mask) << std::endl;

    cv::imwrite("test_mask_output.png", mask);
    std::cout << "Saved test_mask_output.png" << std::endl;
    return 0;
}
