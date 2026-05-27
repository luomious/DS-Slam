/**
* G2oTypesVertex.cc - Vertex implementations split from G2oTypes.cc
* Split to reduce object file size and fix Windows linking issues
*/

#include "G2oTypes.h"
#include "ImuTypes.h"
#include "Converter.h"

namespace ORB_SLAM3
{

// VertexPose implementation
void VertexPose::setToOriginImpl() {}

void VertexPose::oplusImpl(const double* update_) {
    _estimate.Update(update_);
    updateCache();
}

// VertexPose4DoF implementation
void VertexPose4DoF::setToOriginImpl() {}

void VertexPose4DoF::oplusImpl(const double* update_) {
    double update6DoF[6];
    update6DoF[0] = 0;
    update6DoF[1] = 0;
    update6DoF[2] = update_[0];
    update6DoF[3] = update_[1];
    update6DoF[4] = update_[2];
    update6DoF[5] = update_[3];
    _estimate.UpdateW(update6DoF);
    updateCache();
}

// VertexVelocity implementation
void VertexVelocity::setToOriginImpl() {}

void VertexVelocity::oplusImpl(const double* update_) {
    Eigen::Vector3d uv;
    uv << update_[0], update_[1], update_[2];
    setEstimate(estimate()+uv);
}

VertexVelocity::VertexVelocity(KeyFrame* pKF)
{
    setEstimate(pKF->GetVelocity().cast<double>());
}

VertexVelocity::VertexVelocity(Frame* pF)
{
    setEstimate(pF->GetVelocity().cast<double>());
}

// VertexGyroBias implementation
void VertexGyroBias::setToOriginImpl() {}

void VertexGyroBias::oplusImpl(const double* update_) {
    Eigen::Vector3d ubg;
    ubg << update_[0], update_[1], update_[2];
    setEstimate(estimate()+ubg);
}

VertexGyroBias::VertexGyroBias(KeyFrame *pKF)
{
    setEstimate(pKF->GetGyroBias().cast<double>());
}

VertexGyroBias::VertexGyroBias(Frame *pF)
{
    Eigen::Vector3d bg;
    bg << pF->mImuBias.bwx, pF->mImuBias.bwy,pF->mImuBias.bwz;
    setEstimate(bg);
}

// VertexAccBias implementation
void VertexAccBias::setToOriginImpl() {}

void VertexAccBias::oplusImpl(const double* update_) {
    Eigen::Vector3d uba;
    uba << update_[0], update_[1], update_[2];
    setEstimate(estimate()+uba);
}

VertexAccBias::VertexAccBias(KeyFrame *pKF)
{
    setEstimate(pKF->GetAccBias().cast<double>());
}

VertexAccBias::VertexAccBias(Frame *pF)
{
    Eigen::Vector3d ba;
    ba << pF->mImuBias.bax, pF->mImuBias.bay,pF->mImuBias.baz;
    setEstimate(ba);
}

// Explicit read/write implementations to force vtable and typeinfo generation
bool VertexPose4DoF::read(std::istream& is) { return false; }
bool VertexPose4DoF::write(std::ostream& os) const { return false; }

bool VertexVelocity::read(std::istream& is) { return false; }
bool VertexVelocity::write(std::ostream& os) const { return false; }

bool VertexGyroBias::read(std::istream& is) { return false; }
bool VertexGyroBias::write(std::ostream& os) const { return false; }

bool VertexAccBias::read(std::istream& is) { return false; }
bool VertexAccBias::write(std::ostream& os) const { return false; }

bool VertexGDir::read(std::istream& is) { return false; }
bool VertexGDir::write(std::ostream& os) const { return false; }

bool VertexScale::read(std::istream& is) { return false; }
bool VertexScale::write(std::ostream& os) const { return false; }

bool VertexInvDepth::read(std::istream& is) { return false; }
bool VertexInvDepth::write(std::ostream& os) const { return false; }

} // namespace ORB_SLAM3
