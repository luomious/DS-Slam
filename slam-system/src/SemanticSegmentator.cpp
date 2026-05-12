/**
 * DS-SLAM M3: SemanticSegmentator implementation
 *
 * Uses PIMPL pattern to hide ONNX Runtime types from header.
 * This avoids multiple definition errors when linking.
 *
 * Supports two ONNX model formats:
 *   1. Ultralytics YOLO11-seg (80-class COCO, 2 outputs)
 *   2. Custom 2 class model (3 outputs)
 */
#include "SemanticSegmentator.h"

// ONNX Runtime headers only included in implementation file
#include <onnxruntime_cxx_api.h>
#include <algorithm>
#include <numeric>
#include <cmath>

// Dynamic COCO class IDs (person, bicycle, car, motorcycle, bus, truck)
static const int DYNAMIC_COCO_IDS[] = {0, 1, 2, 3, 5, 7};
static const int NUM_DYNAMIC_IDS = 6;

static bool IsDynamicClass(int cocoId) {
    for (int i = 0; i < NUM_DYNAMIC_IDS; ++i) {
        if (DYNAMIC_COCO_IDS[i] == cocoId) return true;
    }
    return false;
}

/**
 * Implementation class - contains all ONNX Runtime types
 */
class SemanticSegmentatorImpl {
public:
    SemanticSegmentatorImpl(const std::string& onnxPath, bool useGPU, cv::Size inputSize)
        : m_env(ORT_LOGGING_LEVEL_WARNING, "DS-SLAM-Seg")
        , m_inputSize(inputSize)
        , m_valid(false)
        , m_lastMs(0.0)
    {
        try {
            if (useGPU) {
                OrtCUDAProviderOptions cudaOpts;
                cudaOpts.device_id = 0;
                m_opts.AppendExecutionProvider_CUDA(cudaOpts);
            }

            m_session = std::make_unique<Ort::Session>(m_env,
                std::wstring(onnxPath.begin(), onnxPath.end()).c_str(),
                m_opts);

            size_t numInputs = m_session->GetInputCount();
            for (size_t i = 0; i < numInputs; ++i) {
                auto name = m_session->GetInputNameAllocated(i, m_allocator);
                m_inputNames.push_back(name.release());
            }

            size_t numOutputs = m_session->GetOutputCount();
            for (size_t i = 0; i < numOutputs; ++i) {
                auto name = m_session->GetOutputNameAllocated(i, m_allocator);
                m_outputNames.push_back(name.release());
            }

            m_inputShape = {1, 3, m_inputSize.height, m_inputSize.width};
            m_valid = true;
        }
        catch (const Ort::Exception& e) {
            // If GPU failed, try CPU
            if (useGPU) {
                try {
                    m_opts = Ort::SessionOptions();
                    m_session = std::make_unique<Ort::Session>(m_env,
                        std::wstring(onnxPath.begin(), onnxPath.end()).c_str(),
                        m_opts);

                    size_t numInputs = m_session->GetInputCount();
                    m_inputNames.clear();
                    for (size_t i = 0; i < numInputs; ++i) {
                        auto name = m_session->GetInputNameAllocated(i, m_allocator);
                        m_inputNames.push_back(name.release());
                    }
                    size_t numOutputs = m_session->GetOutputCount();
                    m_outputNames.clear();
                    for (size_t i = 0; i < numOutputs; ++i) {
                        auto name = m_session->GetOutputNameAllocated(i, m_allocator);
                        m_outputNames.push_back(name.release());
                    }
                    m_valid = true;
                }
                catch (...) { m_valid = false; }
            }
        }
    }

    ~SemanticSegmentatorImpl() = default;

    cv::Mat Segment(const cv::Mat& frame) {
        if (!m_valid) return cv::Mat();

        auto t0 = std::chrono::high_resolution_clock::now();

        std::vector<float> blob;
        Preprocess(frame, blob);

        auto memoryInfo = Ort::MemoryInfo::CreateCpu(OrtArenaAllocator, OrtMemTypeDefault);
        auto inputTensor = Ort::Value::CreateTensor<float>(
            memoryInfo, blob.data(), blob.size(),
            m_inputShape.data(), m_inputShape.size());

        auto outputs = m_session->Run(Ort::RunOptions{nullptr},
            m_inputNames.data(), &inputTensor, 1,
            m_outputNames.data(), m_outputNames.size());

        cv::Mat binaryMask;
        const float confThreshold = 0.3f;

        if (outputs.size() == 2) {
            // YOLO11-seg format
            auto& detTensor = outputs[0];
            auto& protoTensor = outputs[1];

            auto detShape = detTensor.GetTensorTypeAndShapeInfo().GetShape();
            auto protoShape = protoTensor.GetTensorTypeAndShapeInfo().GetShape();

            int totalFeatures = static_cast<int>(detShape[1]);
            int numProposals = static_cast<int>(detShape[2]);
            int nm = 32;
            int nc = totalFeatures - 4 - nm;
            if (nc <= 0) nc = totalFeatures - 4;

            int maskH = static_cast<int>(protoShape[2]);
            int maskW = static_cast<int>(protoShape[3]);

            const float* detData = detTensor.GetTensorData<float>();
            const float* protoData = protoTensor.GetTensorData<float>();

            cv::Mat combinedMask = cv::Mat::zeros(maskH, maskW, CV_32FC1);

            for (int i = 0; i < numProposals; ++i) {
                const float* proposal = detData + i;
                const float* scores = proposal + 4 * numProposals;

                float bestScore = 0.0f;
                int bestClass = -1;
                for (int c = 0; c < nc; ++c) {
                    float s = scores[c * numProposals];
                    if (s > bestScore) {
                        bestScore = s;
                        bestClass = c;
                    }
                }

                if (bestScore < confThreshold) continue;
                if (!IsDynamicClass(bestClass)) continue;

                const float* maskCoeffs = proposal + (4 + nc) * numProposals;

                for (int y = 0; y < maskH; ++y) {
                    for (int x = 0; x < maskW; ++x) {
                        float val = 0.0f;
                        for (int k = 0; k < nm; ++k) {
                            val += maskCoeffs[k * numProposals] * protoData[k * maskH * maskW + y * maskW + x];
                        }
                        float prob = 1.0f / (1.0f + std::exp(-val));
                        if (prob > 0.5f) {
                            combinedMask.at<float>(y, x) = 255.0f;
                        }
                    }
                }
            }

            cv::Mat resized;
            cv::resize(combinedMask, resized, cv::Size(frame.cols, frame.rows), 0, 0, cv::INTER_NEAREST);
            resized.convertTo(binaryMask, CV_8UC1);
        }
        else if (outputs.size() >= 3) {
            // Custom format
            auto& clsTensor = outputs.at(1);
            const float* clsData = clsTensor.GetTensorData<float>();
            auto clsShape = clsTensor.GetTensorTypeAndShapeInfo().GetShape();

            int H = static_cast<int>(clsShape[2]);
            int W = static_cast<int>(clsShape[3]);
            int numClasses = static_cast<int>(clsShape[1]);

            cv::Mat mask(H, W, CV_32FC1);
            for (int y = 0; y < H; ++y) {
                for (int x = 0; x < W; ++x) {
                    float maxLogit = -1e9f;
                    for (int c = 0; c < numClasses; ++c) {
                        float val = clsData[c * H * W + y * W + x];
                        if (val > maxLogit) maxLogit = val;
                    }
                    float sumExp = 0.0f;
                    for (int c = 0; c < numClasses; ++c) {
                        sumExp += std::exp(clsData[c * H * W + y * W + x] - maxLogit);
                    }
                    float fgProb = std::exp(clsData[1 * H * W + y * W + x] - maxLogit) / sumExp;
                    mask.at<float>(y, x) = (fgProb > confThreshold) ? 255.0f : 0.0f;
                }
            }

            cv::Mat resized;
            cv::resize(mask, resized, cv::Size(frame.cols, frame.rows));
            resized.convertTo(binaryMask, CV_8UC1);
        }
        else {
            return cv::Mat();
        }

        // Morphological dilation
        cv::Mat kernel = cv::getStructuringElement(cv::MORPH_RECT, cv::Size(5, 5));
        cv::dilate(binaryMask, binaryMask, kernel);

        auto t1 = std::chrono::high_resolution_clock::now();
        m_lastMs = std::chrono::duration<double, std::milli>(t1 - t0).count();

        return binaryMask;
    }

    bool IsValid() const { return m_valid; }
    double GetLastInferenceTime() const { return m_lastMs; }
    cv::Size GetInputSize() const { return m_inputSize; }

private:
    void Preprocess(const cv::Mat& frame, std::vector<float>& blob) {
        cv::Mat rgb, resized;
        cv::cvtColor(frame, rgb, cv::COLOR_BGR2RGB);
        cv::resize(rgb, resized, m_inputSize);
        resized.convertTo(resized, CV_32FC3, 1.0 / 255.0);

        blob.resize(3 * m_inputSize.height * m_inputSize.width);
        std::vector<cv::Mat> channels(3);
        cv::split(resized, channels);
        for (int c = 0; c < 3; ++c) {
            std::memcpy(blob.data() + c * m_inputSize.area(),
                        channels[c].data,
                        m_inputSize.area() * sizeof(float));
        }
    }

    Ort::Env m_env;
    Ort::SessionOptions m_opts;
    std::unique_ptr<Ort::Session> m_session;
    Ort::AllocatorWithDefaultOptions m_allocator;
    std::vector<const char*> m_inputNames;
    std::vector<const char*> m_outputNames;
    std::vector<int64_t> m_inputShape;
    cv::Size m_inputSize;
    bool m_valid;
    double m_lastMs;
};

// SemanticSegmentator public API - forwards to implementation

SemanticSegmentator::SemanticSegmentator(const std::string& onnxPath,
                                         bool useGPU,
                                         cv::Size inputSize)
    : m_impl(std::make_unique<SemanticSegmentatorImpl>(onnxPath, useGPU, inputSize))
{
}

SemanticSegmentator::~SemanticSegmentator() = default;

cv::Mat SemanticSegmentator::Segment(const cv::Mat& frame) {
    return m_impl->Segment(frame);
}

bool SemanticSegmentator::IsValid() const {
    return m_impl->IsValid();
}

double SemanticSegmentator::GetLastInferenceTime() const {
    return m_impl->GetLastInferenceTime();
}

cv::Size SemanticSegmentator::GetInputSize() const {
    return m_impl->GetInputSize();
}
