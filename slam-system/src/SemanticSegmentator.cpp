/**
 * DS-SLAM M3: SemanticSegmentator implementation
 */
#include "SemanticSegmentator.h"
#include <algorithm>

SemanticSegmentator::SemanticSegmentator(const std::string& onnxPath,
                                         bool useGPU,
                                         cv::Size inputSize)
    : m_env(ORT_LOGGING_LEVEL_WARNING, "DS-SLAM-Seg")
    , m_inputSize(inputSize)
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

        // Cache input/output names
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

        // Input shape: [1, 3, H, W]
        m_inputShape = {1, 3, m_inputSize.height, m_inputSize.width};
        m_valid = true;
    }
    catch (const Ort::Exception& e) {
        // GPU provider may fail, fall back to CPU
        if (useGPU) {
            try {
                m_opts = Ort::SessionOptions();
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
                m_valid = true;
            }
            catch (...) { m_valid = false; }
        }
    }
}

void SemanticSegmentator::Preprocess(const cv::Mat& frame,
                                     std::vector<float>& blob)
{
    cv::Mat rgb, resized;
    cv::cvtColor(frame, rgb, cv::COLOR_BGR2RGB);
    cv::resize(rgb, resized, m_inputSize);
    resized.convertTo(resized, CV_32FC3, 1.0 / 255.0);

    // HWC -> CHW
    blob.resize(3 * m_inputSize.height * m_inputSize.width);
    std::vector<cv::Mat> channels(3);
    cv::split(resized, channels);
    for (int c = 0; c < 3; ++c) {
        std::memcpy(blob.data() + c * m_inputSize.area(),
                    channels[c].data,
                    m_inputSize.area() * sizeof(float));
    }
}

cv::Mat SemanticSegmentator::Segment(const cv::Mat& frame)
{
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

    // outputs[0]=bbox, outputs[1]=cls, outputs[2]=proto
    auto& clsTensor = outputs.at(1);
    auto* clsData = clsTensor.GetTensorData<float>();
    auto clsShape = clsTensor.GetTensorTypeAndShapeInfo().GetShape();

    int H = static_cast<int>(clsShape[2]);
    int W = static_cast<int>(clsShape[3]);
    int numClasses = static_cast<int>(clsShape[1]);

    // Foreground class = index 1
    cv::Mat mask(H, W, CV_32FC1);
    for (int y = 0; y < H; ++y) {
        for (int x = 0; x < W; ++x) {
            float maxVal = -1e9f;
            int bestClass = 0;
            for (int c = 0; c < numClasses; ++c) {
                float val = clsData[c * H * W + y * W + x];
                if (val > maxVal) { maxVal = val; bestClass = c; }
            }
            mask.at<float>(y, x) = (bestClass == 1) ? 255.0f : 0.0f;
        }
    }

    cv::Mat result;
    if (H != frame.rows || W != frame.cols) {
        cv::resize(mask, result, cv::Size(frame.cols, frame.rows));
    } else {
        result = mask;
    }
    result.convertTo(result, CV_8UC1);

    auto t1 = std::chrono::high_resolution_clock::now();
    m_lastMs = std::chrono::duration<double, std::milli>(t1 - t0).count();

    return result;
}
