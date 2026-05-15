#include "StaticMapper.h"
#include <opencv2/imgcodecs.hpp>
#include <fstream>
#include <cmath>

StaticMapper::StaticMapper(float gridResolution, float gridRange)
    : m_resolution(gridResolution)
    , m_range(gridRange)
    , m_gridSize(static_cast<int>(2.0f * gridRange / gridResolution))
    , m_kfCount(0)
{
}

void StaticMapper::AddKeyframe(const cv::Mat& depth, const cv::Mat& rgb,
                                const cv::Mat& mask, const cv::Mat& Tcw,
                                float fx, float fy, float cx, float cy)
{
    cv::Mat Twc = Tcw.inv();
    int step = 4;

    for (int v = 0; v < depth.rows; v += step) {
        for (int u = 0; u < depth.cols; u += step) {
            if (!mask.empty() && mask.at<uint8_t>(v, u) > 0) continue;

            float d;
            if (depth.type() == CV_16UC1) {
                d = depth.at<uint16_t>(v, u) / 1000.0f;
            } else {
                d = depth.at<float>(v, u);
            }
            if (d <= 0.01f || d > 8.0f) continue;

            float x = (u - cx) * d / fx;
            float y = (v - cy) * d / fy;
            cv::Mat ptCam = (cv::Mat_<float>(4, 1) << x, y, d, 1.0f);
            cv::Mat ptWorld = Twc * ptCam;

            SimplePoint3D pt;
            pt.x = ptWorld.at<float>(0);
            pt.y = ptWorld.at<float>(1);
            pt.z = ptWorld.at<float>(2);

            if (!rgb.empty()) {
                cv::Vec3b bgr = rgb.at<cv::Vec3b>(v, u);
                pt.r = bgr[2]; pt.g = bgr[1]; pt.b = bgr[0];
            } else {
                pt.r = pt.g = pt.b = 200;
            }
            m_allPoints.push_back(pt);
        }
    }
    m_kfCount++;
}

cv::Mat StaticMapper::BuildGridMap() const
{
    cv::Mat gridMap = cv::Mat(m_gridSize, m_gridSize, CV_8UC1, cv::Scalar(127));

    for (const auto& pt : m_allPoints) {
        int gx = static_cast<int>((pt.x + m_range) / m_resolution);
        int gy = static_cast<int>((pt.z + m_range) / m_resolution);
        if (gx >= 0 && gx < m_gridSize && gy >= 0 && gy < m_gridSize) {
            gridMap.at<uint8_t>(gy, gx) = 0;
        }
    }
    return gridMap;
}

bool StaticMapper::ExportPLY(const std::string& path) const
{
    std::ofstream f(path);
    if (!f.is_open()) return false;

    f << "ply\n";
    f << "format ascii 1.0\n";
    f << "element vertex " << m_allPoints.size() << "\n";
    f << "property float x\nproperty float y\nproperty float z\n";
    f << "property uchar red\nproperty uchar green\nproperty uchar blue\n";
    f << "end_header\n";

    for (const auto& pt : m_allPoints) {
        f << pt.x << " " << pt.y << " " << pt.z << " "
          << (int)pt.r << " " << (int)pt.g << " " << (int)pt.b << "\n";
    }
    return true;
}

bool StaticMapper::ExportGridMap(const std::string& path) const
{
    cv::Mat grid = BuildGridMap();
    return cv::imwrite(path, grid);
}

size_t StaticMapper::GetPointCount() const { return m_allPoints.size(); }
int StaticMapper::GetKeyframeCount() const { return m_kfCount; }
