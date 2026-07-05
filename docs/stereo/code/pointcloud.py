"""
视差图 → 深度图 → 点云

核心公式 (平行双目):
    Z = f * B / d           (深度)
    X = (u - cx) * Z / f    (x坐标)
    Y = (v - cy) * Z / f    (y坐标)
"""

from __future__ import annotations

import numpy as np
import open3d as o3d


# ============================================================
# 默认相机参数（Middlebury Tsukuba 参考值）
# ============================================================

# 这些参数来自 Middlebury 2001/2003 数据集的典型值
# 如果你的数据有标定文件，请使用标定值
DEFAULT_CALIB = {
    'focal_length': 615.0,     # 焦距（像素）
    'baseline': 0.10,          # 基线距离（米）
    'cx': 192.0,               # 光心 x（像素）
    'cy': 144.0,               # 光心 y（像素）
    'doffs': 0.0,              # 主点水平偏移
}

# KITTI 典型参数
KITTI_CALIB = {
    'focal_length': 718.856,   # fx（KITTI 2015 典型值）
    'baseline': 0.54,           # 基线 ~54cm
    'cx': 607.1928,
    'cy': 185.2157,
}


# ============================================================
# 视差 → 深度 → 点云
# ============================================================

def disparity_to_depth(disparity: np.ndarray,
                       focal_length: float,
                       baseline: float,
                       min_disp: float = 0.5) -> np.ndarray:
    """将视差图转为深度图。

    Args:
        disparity: (H, W) 视差图
        focal_length: 焦距（像素）
        baseline: 基线距离（米）
        min_disp: 最小有效视差（避免除零）

    Returns:
        depth: (H, W) 深度图（米），无效区域为 0
    """
    depth = np.zeros_like(disparity)
    valid = disparity > min_disp
    depth[valid] = focal_length * baseline / disparity[valid]
    return depth


def depth_to_pointcloud(depth: np.ndarray,
                        K: np.ndarray | None = None,
                        image: np.ndarray | None = None) -> o3d.geometry.PointCloud:
    """将深度图转为彩色点云。

    Args:
        depth: (H, W) 深度图（米）
        K: (3, 3) 相机内参矩阵，若不提供则用默认参数
        image: (H, W, 3) RGB 图像用于着色

    Returns:
        open3d.geometry.PointCloud
    """
    H, W = depth.shape

    if K is None:
        # 用默认 Middlebury 参数
        focal = DEFAULT_CALIB['focal_length']
        cx = DEFAULT_CALIB['cx']
        cy = DEFAULT_CALIB['cy']
    else:
        focal = K[0, 0]
        cx = K[0, 2]
        cy = K[1, 2]

    # 生成像素网格
    u, v = np.meshgrid(np.arange(W), np.arange(H))

    # 计算 3D 坐标
    Z = depth
    X = (u - cx) * Z / focal
    Y = (v - cy) * Z / focal

    # 堆叠并过滤无效点
    points = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)
    valid = (Z.reshape(-1) > 0) & np.isfinite(points).all(axis=1)
    points = points[valid]

    # 颜色
    if image is not None:
        if len(image.shape) == 2:  # 灰度
            colors = np.repeat(image.reshape(-1, 1)[valid], 3, axis=1) / 255.0
        elif image.shape[2] == 3:  # RGB
            colors = image.reshape(-1, 3)[valid].astype(np.float64) / 255.0
        else:
            colors = np.ones((len(points), 3)) * 0.6
    else:
        # 用深度着色
        z_norm = (Z.reshape(-1)[valid] - Z[valid].min()) / (Z[valid].max() - Z[valid].min() + 1e-8)
        colors = np.stack([z_norm, 0.3 + z_norm * 0.5, 1.0 - z_norm], axis=1)

    # 构建 Open3D 点云
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points)
    pcd.colors = o3d.utility.Vector3dVector(colors)

    return pcd


def disparity_to_pointcloud(disparity: np.ndarray,
                            image: np.ndarray | None = None,
                            focal_length: float = 615.0,
                            baseline: float = 0.10,
                            **kwargs) -> o3d.geometry.PointCloud:
    """一步：视差图 → 点云。"""
    depth = disparity_to_depth(disparity, focal_length, baseline)

    K = np.array([
        [focal_length, 0, kwargs.get('cx', DEFAULT_CALIB['cx'])],
        [0, focal_length, kwargs.get('cy', DEFAULT_CALIB['cy'])],
        [0, 0, 1]
    ])

    return depth_to_pointcloud(depth, K=K, image=image)


# ============================================================
# 点云后处理
# ============================================================

def remove_statistical_outliers(pcd: o3d.geometry.PointCloud,
                                 nb_neighbors: int = 20,
                                 std_ratio: float = 2.0) -> o3d.geometry.PointCloud:
    """统计离群点过滤。"""
    return pcd.remove_statistical_outlier(
        nb_neighbors=nb_neighbors,
        std_ratio=std_ratio
    )[0]  # 返回过滤后的点云


def downsample(pcd: o3d.geometry.PointCloud,
               voxel_size: float = 0.01) -> o3d.geometry.PointCloud:
    """体素下采样。"""
    return pcd.voxel_down_sample(voxel_size)


def estimate_normals(pcd: o3d.geometry.PointCloud,
                     radius: float = 0.05,
                     max_nn: int = 30) -> o3d.geometry.PointCloud:
    """估计法向量（用于更好的渲染）。"""
    pcd.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=radius, max_nn=max_nn)
    )
    return pcd
