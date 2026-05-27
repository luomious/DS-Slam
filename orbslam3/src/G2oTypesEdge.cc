/**
* G2oTypesEdge.cc - EdgeMono/Stereo implementations split from G2oTypes.cc
* Split to reduce object file size and fix Windows linking issues
*/

#include "G2oTypes.h"
#include "ImuTypes.h"
#include "Converter.h"

namespace ORB_SLAM3
{

// EdgeMono computeError
void EdgeMono::computeError(){
    const g2o::VertexSBAPointXYZ* VPoint = static_cast<const g2o::VertexSBAPointXYZ*>(_vertices[0]);
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[1]);
    const Eigen::Vector2d obs(_measurement);
    _error = obs - VPose->estimate().Project(VPoint->estimate(),cam_idx);
}

void EdgeMono::linearizeOplus()
{
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[1]);
    const g2o::VertexSBAPointXYZ* VPoint = static_cast<const g2o::VertexSBAPointXYZ*>(_vertices[0]);

    const Eigen::Matrix3d &Rcw = VPose->estimate().Rcw[cam_idx];
    const Eigen::Vector3d &tcw = VPose->estimate().tcw[cam_idx];
    const Eigen::Vector3d Xc = Rcw*VPoint->estimate() + tcw;
    const Eigen::Vector3d Xb = VPose->estimate().Rbc[cam_idx]*Xc+VPose->estimate().tbc[cam_idx];
    const Eigen::Matrix3d &Rcb = VPose->estimate().Rcb[cam_idx];

    const Eigen::Matrix<double,2,3> proj_jac = VPose->estimate().pCamera[cam_idx]->projectJac(Xc);
    _jacobianOplusXi = -proj_jac * Rcw;

    Eigen::Matrix<double,3,6> SE3deriv;
    double x = Xb(0);
    double y = Xb(1);
    double z = Xb(2);

    SE3deriv << 0.0, z,   -y, 1.0, 0.0, 0.0,
            -z , 0.0, x, 0.0, 1.0, 0.0,
            y ,  -x , 0.0, 0.0, 0.0, 1.0;

    _jacobianOplusXj = proj_jac * Rcb * SE3deriv;
}

// EdgeMonoOnlyPose computeError
void EdgeMonoOnlyPose::computeError(){
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[0]);
    const Eigen::Vector2d obs(_measurement);
    _error = obs - VPose->estimate().Project(Xw,cam_idx);
}

void EdgeMonoOnlyPose::linearizeOplus()
{
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[0]);

    const Eigen::Matrix3d &Rcw = VPose->estimate().Rcw[cam_idx];
    const Eigen::Vector3d &tcw = VPose->estimate().tcw[cam_idx];
    const Eigen::Vector3d Xc = Rcw*Xw + tcw;
    const Eigen::Vector3d Xb = VPose->estimate().Rbc[cam_idx]*Xc+VPose->estimate().tbc[cam_idx];
    const Eigen::Matrix3d &Rcb = VPose->estimate().Rcb[cam_idx];

    Eigen::Matrix<double,2,3> proj_jac = VPose->estimate().pCamera[cam_idx]->projectJac(Xc);

    Eigen::Matrix<double,3,6> SE3deriv;
    double x = Xb(0);
    double y = Xb(1);
    double z = Xb(2);
    SE3deriv << 0.0, z,   -y, 1.0, 0.0, 0.0,
            -z , 0.0, x, 0.0, 1.0, 0.0,
            y ,  -x , 0.0, 0.0, 0.0, 1.0;
    _jacobianOplusXi = proj_jac * Rcb * SE3deriv;
}

// EdgeStereo computeError
void EdgeStereo::computeError(){
    const g2o::VertexSBAPointXYZ* VPoint = static_cast<const g2o::VertexSBAPointXYZ*>(_vertices[0]);
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[1]);
    const Eigen::Vector3d obs(_measurement);
    _error = obs - VPose->estimate().ProjectStereo(VPoint->estimate(),cam_idx);
}

void EdgeStereo::linearizeOplus()
{
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[1]);
    const g2o::VertexSBAPointXYZ* VPoint = static_cast<const g2o::VertexSBAPointXYZ*>(_vertices[0]);

    const Eigen::Matrix3d &Rcw = VPose->estimate().Rcw[cam_idx];
    const Eigen::Vector3d &tcw = VPose->estimate().tcw[cam_idx];
    const Eigen::Vector3d Xc = Rcw*VPoint->estimate() + tcw;
    const Eigen::Vector3d Xb = VPose->estimate().Rbc[cam_idx]*Xc+VPose->estimate().tbc[cam_idx];
    const Eigen::Matrix3d &Rcb = VPose->estimate().Rcb[cam_idx];
    const double bf = VPose->estimate().bf;
    const double inv_z2 = 1.0/(Xc(2)*Xc(2));

    Eigen::Matrix<double,3,3> proj_jac;
    proj_jac.block<2,3>(0,0) = VPose->estimate().pCamera[cam_idx]->projectJac(Xc);
    proj_jac.block<1,3>(2,0) = proj_jac.block<1,3>(0,0);
    proj_jac(2,2) += bf*inv_z2;

    _jacobianOplusXi = -proj_jac * Rcw;

    Eigen::Matrix<double,3,6> SE3deriv;
    double x = Xb(0);
    double y = Xb(1);
    double z = Xb(2);

    SE3deriv << 0.0, z,   -y, 1.0, 0.0, 0.0,
            -z , 0.0, x, 0.0, 1.0, 0.0,
            y ,  -x , 0.0, 0.0, 0.0, 1.0;

    _jacobianOplusXj = proj_jac * Rcb * SE3deriv;
}

// EdgeStereoOnlyPose computeError
void EdgeStereoOnlyPose::computeError(){
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[0]);
    const Eigen::Vector3d obs(_measurement);
    _error = obs - VPose->estimate().ProjectStereo(Xw, cam_idx);
}

void EdgeStereoOnlyPose::linearizeOplus()
{
    const VertexPose* VPose = static_cast<const VertexPose*>(_vertices[0]);

    const Eigen::Matrix3d &Rcw = VPose->estimate().Rcw[cam_idx];
    const Eigen::Vector3d &tcw = VPose->estimate().tcw[cam_idx];
    const Eigen::Vector3d Xc = Rcw*Xw + tcw;
    const Eigen::Vector3d Xb = VPose->estimate().Rbc[cam_idx]*Xc+VPose->estimate().tbc[cam_idx];
    const Eigen::Matrix3d &Rcb = VPose->estimate().Rcb[cam_idx];
    const double bf = VPose->estimate().bf;
    const double inv_z2 = 1.0/(Xc(2)*Xc(2));

    Eigen::Matrix<double,3,3> proj_jac;
    proj_jac.block<2,3>(0,0) = VPose->estimate().pCamera[cam_idx]->projectJac(Xc);
    proj_jac.block<1,3>(2,0) = proj_jac.block<1,3>(0,0);
    proj_jac(2,2) += bf*inv_z2;

    Eigen::Matrix<double,3,6> SE3deriv;
    double x = Xb(0);
    double y = Xb(1);
    double z = Xb(2);
    SE3deriv << 0.0, z,   -y, 1.0, 0.0, 0.0,
            -z , 0.0, x, 0.0, 1.0, 0.0,
            y ,  -x , 0.0, 0.0, 0.0, 1.0;
    _jacobianOplusXi = proj_jac * Rcb * SE3deriv;
}

// EdgeGyroRW computeError
void EdgeGyroRW::computeError(){
    const VertexGyroBias* VG1= static_cast<const VertexGyroBias*>(_vertices[0]);
    const VertexGyroBias* VG2= static_cast<const VertexGyroBias*>(_vertices[1]);
    _error = VG2->estimate()-VG1->estimate();
}

void EdgeGyroRW::linearizeOplus(){
    _jacobianOplusXi = -Eigen::Matrix3d::Identity();
    _jacobianOplusXj.setIdentity();
}

// EdgeAccRW computeError
void EdgeAccRW::computeError(){
    const VertexAccBias* VA1= static_cast<const VertexAccBias*>(_vertices[0]);
    const VertexAccBias* VA2= static_cast<const VertexAccBias*>(_vertices[1]);
    _error = VA2->estimate()-VA1->estimate();
}

void EdgeAccRW::linearizeOplus(){
    _jacobianOplusXi = -Eigen::Matrix3d::Identity();
    _jacobianOplusXj.setIdentity();
}

// EdgePriorAcc computeError
void EdgePriorAcc::computeError(){
    const VertexAccBias* VA = static_cast<const VertexAccBias*>(_vertices[0]);
    _error = bprior - VA->estimate();
}

void EdgePriorAcc::linearizeOplus()
{
    _jacobianOplusXi.block<3,3>(0,0) = Eigen::Matrix3d::Identity();
}

// EdgePriorGyro computeError
void EdgePriorGyro::computeError(){
    const VertexGyroBias* VG = static_cast<const VertexGyroBias*>(_vertices[0]);
    _error = bprior - VG->estimate();
}

void EdgePriorGyro::linearizeOplus()
{
    _jacobianOplusXi.block<3,3>(0,0) = Eigen::Matrix3d::Identity();
}

// Edge4DoF computeError
void Edge4DoF::computeError(){
    const VertexPose4DoF* VPi = static_cast<const VertexPose4DoF*>(_vertices[0]);
    const VertexPose4DoF* VPj = static_cast<const VertexPose4DoF*>(_vertices[1]);
    _error << LogSO3(VPi->estimate().Rcw[0]*VPj->estimate().Rcw[0].transpose()*dRij.transpose()),
             VPi->estimate().Rcw[0]*(-VPj->estimate().Rcw[0].transpose()*VPj->estimate().tcw[0])+VPi->estimate().tcw[0] - dtij;
}

// Explicit read/write implementations
bool EdgeMono::read(std::istream& is) { return false; }
bool EdgeMono::write(std::ostream& os) const { return false; }

bool EdgeMonoOnlyPose::read(std::istream& is) { return false; }
bool EdgeMonoOnlyPose::write(std::ostream& os) const { return false; }

bool EdgeStereo::read(std::istream& is) { return false; }
bool EdgeStereo::write(std::ostream& os) const { return false; }

bool EdgeStereoOnlyPose::read(std::istream& is) { return false; }
bool EdgeStereoOnlyPose::write(std::ostream& os) const { return false; }

bool EdgeGyroRW::read(std::istream& is) { return false; }
bool EdgeGyroRW::write(std::ostream& os) const { return false; }

bool EdgeAccRW::read(std::istream& is) { return false; }
bool EdgeAccRW::write(std::ostream& os) const { return false; }

bool EdgePriorAcc::read(std::istream& is) { return false; }
bool EdgePriorAcc::write(std::ostream& os) const { return false; }

bool EdgePriorGyro::read(std::istream& is) { return false; }
bool EdgePriorGyro::write(std::ostream& os) const { return false; }

bool Edge4DoF::read(std::istream& is) { return false; }
bool Edge4DoF::write(std::ostream& os) const { return false; }

} // namespace ORB_SLAM3
