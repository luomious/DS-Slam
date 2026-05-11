# DS-SLAM 编译产物保护清单

> ⚠️ 自动生成于 2026-05-08 21:53 | 防止误删必需编译文件

## 当前构建状态

- **编译器**: GCC 15.2.0 + Clang 22.1.4 + GNU ld 2.46
- **CMake**: 4.3.2 (MinGW Makefiles)
- **状态**: M4 编译通过，ATE 评估运行中

---

## 🚫 禁止删除：核心运行时文件

### RGB-D 运行目录 (orbslam3/Examples/RGB-D/)

| 文件 | 大小 | 用途 |
|------|------|------|
| 
gbd_tum.exe | ~6 MB | 主程序 |
| libORB_SLAM3.dll | ~6.4 MB | ORB-SLAM3 核心库 |
| libg2o.dll | ~1.0 MB | g2o 优化器 |
| libDBoW2.dll | ~200 KB | DBoW2 词袋库 |
| TUM1.yaml | ~1 KB | TUM 数据集配置 |

### 第三方 DLL 依赖 (orbslam3/Examples/RGB-D/)

- OpenCV 全套 DLL (opencv_*.dll 共 60+ 文件, ~200 MB)
- MSYS2 运行时: libstdc++-6.dll, libgcc_s_seh-1.dll, libwinpthread-1.dll
- Boost: libboost_serialization-mt.dll
- OpenSSL: libcrypto-3-x64.dll, libssl-3-x64.dll

---

## 🔧 编译中间产物 (orbslam3/build/)

### 可删除但需重建（cmake 完整构建可恢复）

| 文件 | 大小 | 说明 |
|------|------|------|
| CMakeFiles/ORB_SLAM3.dir/src/*.obj | ~15 MB | 26 个对象文件 |
| CMakeFiles/rgbd_tum.dir/Examples/RGB-D/rgbd_tum.cc.obj | ~50 KB | rgbd_tum 对象文件 |
| Thirdparty/g2o/CMakeFiles/g2o.dir/ | ~5 MB | g2o 对象文件 |
| Thirdparty/DBoW2/CMakeFiles/DBoW2.dir/ | ~500 KB | DBoW2 对象文件 |
| Makefile, Makefile2, uild.make, linkLibs.rsp | ~200 KB | 构建脚本 |
| CMakeCache.txt | ~10 KB | cmake 缓存 |

---

## 📁 语义分割模块 (slam-system/)

### 可删除但需重建

| 文件 | 大小 | 说明 |
|------|------|------|
| uild/libSemanticSegmentator.a | ~356 KB | 语义分割静态库 |
| uild/CMakeFiles/SemanticSegmentator.dir/src/SemanticSegmentator.cpp.obj | ~200 KB | 对象文件 |

---

## 🧠 ONNX Runtime 库 (libs/onnxruntime/)

### 不可删除（自定义配置）

| 文件 | 大小 | 说明 |
|------|------|------|
| in/onnxruntime.dll | ~14 MB | ONNX Runtime 运行时 |
| lib/libonnxruntime.dll.a | ~3 KB | 导入库（dlltool 生成） |
| include/onnxruntime_cxx_api.h | ~50 KB | C++ API 头文件 |
| include/onnxruntime_c_api.h | ~200 KB | C API 头文件 |

---

## 🗂️ 数据集 (datasets/tum/)

### 不可删除

| 文件 | 大小 | 说明 |
|------|------|------|
| 
gbd_dataset_freiburg1_xyz/ | ~1 GB | fr1/xyz 基线数据集 |
| 
gbd_dataset_freiburg3_walking_xyz/ | ~1.2 GB | walking_xyz 动态场景数据集 |
| 
gbd_dataset_freiburg1_xyz/associations.txt | ~30 KB | RGB-Depth 关联文件 |
| 
gbd_dataset_freiburg3_walking_xyz/associations.txt | ~35 KB | RGB-Depth 关联文件 |

---

## 🧠 词表 (Vocabulary/)

### 不可删除

| 文件 | 大小 | 说明 |
|------|------|------|
| ORBvoc.txt | ~138 MB | ORB 词袋（文本格式） |
| ORBvoc.bin | ~40 MB | ORB 词袋（二进制格式） |

---

## 🔬 评估脚本 (scripts/)

### 不可删除

| 文件 | 说明 |
|------|------|
| eval_ate.py | ATE 评估脚本（纯 Python，不依赖 numpy） |
| ssociate.py | TUM 数据集 RGB-Depth 关联生成（Python 3 兼容） |

---

## ⚡ 关键编译依赖链

`
rgbd_tum.exe
├── libORB_SLAM3.dll (核心库)
│   ├── libg2o.dll (优化器)
│   ├── libDBoW2.dll (词袋)
│   ├── opencv_*.dll (视觉库)
│   ├── libboost_serialization-mt.dll
│   └── libSemanticSegmentator.a (静态链接)
│       └── onnxruntime.dll (推理引擎)
├── onnxruntime.dll
└── libcrypto-3-x64.dll, libssl-3-x64.dll
`

---

## ⚠️ 编译注意事项

1. **16GB RAM 限制**: 必须 mingw32-make -j1，关闭浏览器/IDE 释放 5GB+ 内存
2. **PowerShell 转义**: -Wa,-mbig-obj 的逗号会被 PowerShell 解析为分隔符，需用 cmd.exe 包装
3. **GCC 15 Segfault**: cc1plus segfault 导致某些文件无法编译，已改用 clang
4. **cmake 缓存污染**: CMAKE_CXX_FLAGS 会累积而非替换，清理 cmake 缓存时需重设所有标志
5. **rebuild.bat**: 使用前确保 mingw32-make 在 PATH 中，且关闭所有占用 DLL 的进程

---

*最后更新: 2026-05-08 21:53*
*当前分支: main*
*最近 commit: M4 FilterEpipolar 集成*