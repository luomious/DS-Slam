#pragma once

#include <opencv2/core.hpp>
#include <vector>
#include <string>
#include <cstdint>

struct SimplePoint3D {
    float x, y, z;
    uint8_t r, g, b;
};

class StaticMapper {
public:
    StaticMapper(float gridResolution = 0.05f, float gridRange = 5.0f);

    void AddKeyframe(const cv::Mat& depth, const cv::Mat& rgb,
                     const cv::Mat& mask, const cv::Mat& Tcw,
                     float fx, float fy, float cx, float cy);

    cv::Mat BuildGridMap() const;

    bool ExportPLY(const std::string& path) const;
    bool ExportGridMap(const std::string& path) const;

    size_t GetPointCount() const;
    int GetKeyframeCount() const;

private:
    std::vector<SimplePoint3D> m_allPoints;
    float m_resolution;
    float m_range;
    int m_gridSize;
    int m_kfCount;
};
