// Explicit template instantiations for BaseMultiEdge
// Required for Windows static library builds to ensure vtable generation

#include "base_multi_edge.h"

namespace g2o {

// Instantiate for ORB-SLAM3 EdgeInertial and EdgeInertialGS
template class BaseMultiEdge<9, Eigen::Matrix<double, 9, 1>>;

// Instantiate for ORB-SLAM3 EdgePriorPoseImu
template class BaseMultiEdge<15, Eigen::Matrix<double, 15, 1>>;

} // end namespace g2o
