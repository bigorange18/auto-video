"""
立体匹配结果可视化
"""

from __future__ import annotations

import numpy as np
import matplotlib.pyplot as plt
import matplotlib
import open3d as o3d
from pathlib import Path

# ============================================================
# matplotlib 全局设置
# ============================================================

plt.rcParams.update({
    'figure.dpi': 150,
    'savefig.dpi': 150,
    'savefig.bbox': 'tight',
    'font.size': 10,
})

# 视差图 colormap——turbo 对数值变化最敏感
DISPARITY_CMAP = 'turbo'


# ============================================================
# 单图可视化
# ============================================================

def plot_disparity(disparity: np.ndarray,
                   title: str = 'Disparity Map',
                   vmin: float | None = None,
                   vmax: float | None = None,
                   colorbar: bool = True,
                   ax: plt.Axes | None = None) -> plt.Axes:
    """绘制视差图。"""
    if ax is None:
        _, ax = plt.subplots()

    valid = disparity > 0
    disp = disparity.copy()
    disp[~valid] = np.nan

    if vmin is None:
        vmin = np.nanmin(disp)
    if vmax is None:
        vmax = np.nanmax(disp)

    im = ax.imshow(disp, cmap=DISPARITY_CMAP, vmin=vmin, vmax=vmax)
    ax.set_title(title)
    ax.axis('off')
    if colorbar:
        plt.colorbar(im, ax=ax, fraction=0.046, label='Disparity (px)')
    return ax


def plot_depth(depth: np.ndarray,
               title: str = 'Depth Map',
               ax: plt.Axes | None = None) -> plt.Axes:
    """绘制深度图。"""
    if ax is None:
        _, ax = plt.subplots()

    d = depth.copy()
    d[d <= 0] = np.nan
    im = ax.imshow(d, cmap='plasma')
    ax.set_title(title)
    ax.axis('off')
    plt.colorbar(im, ax=ax, fraction=0.046, label='Depth (m)')
    return ax


# ============================================================
# 比对面板
# ============================================================

def plot_stereo_result(imgL: np.ndarray,
                       imgR: np.ndarray,
                       result: dict,
                       save_path: str | None = None) -> plt.Figure:
    """绘制完整的立体匹配结果面板。

    一行：左图 | 右图 | 视差图 | 误差图（如果有 GT）
    """
    method = result.get('method', 'unknown')
    disparity = result['disparity']

    fig, axes = plt.subplots(1, 4, figsize=(16, 5))

    # 左图
    axes[0].imshow(imgL, cmap='gray')
    axes[0].set_title('Left Image')
    axes[0].axis('off')

    # 右图
    axes[1].imshow(imgR, cmap='gray')
    axes[1].set_title('Right Image')
    axes[1].axis('off')

    # 视差图
    valid = disparity > 0
    disp = disparity.copy()
    disp[~valid] = np.nan
    im = axes[2].imshow(disp, cmap=DISPARITY_CMAP)
    axes[2].set_title(f'Disparity ({method})')
    axes[2].axis('off')
    plt.colorbar(im, ax=axes[2], fraction=0.046)

    # 有效像素比例 / 深度图
    depth = np.zeros_like(disparity)
    valid_mask = disparity > 0
    if valid_mask.any():
        depth[valid_mask] = 615.0 * 0.10 / disparity[valid_mask]
    d = depth.copy()
    d[d <= 0] = np.nan
    im3 = axes[3].imshow(d, cmap='plasma')
    axes[3].set_title(f'Depth Map (est.)')
    axes[3].axis('off')
    plt.colorbar(im3, ax=axes[3], fraction=0.046)

    fig.suptitle(f'Stereo Matching — {method}', fontsize=14, y=1.02)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, bbox_inches='tight')
        print(f"  → 保存到 {save_path}")

    return fig


def plot_cost_slice(cost_volume: np.ndarray,
                    y: int | None = None,
                    x: int | None = None,
                    ax: plt.Axes | None = None) -> plt.Axes:
    """可视化代价体中某个像素的代价曲线。

    可以看到最小代价对应的视差是否合理。
    """
    if ax is None:
        _, ax = plt.subplots()

    if y is not None and x is not None:
        costs = cost_volume[y, x, :]
        ax.plot(costs, 'b-', linewidth=1)
        ax.set_title(f'Cost curve at ({x}, {y})')
        ax.set_xlabel('Disparity')
        ax.set_ylabel('Cost')
        ax.axvline(np.argmin(costs), color='r', linestyle='--', alpha=0.5,
                   label=f'min at d={np.argmin(costs)}')
        ax.legend()
    else:
        # 取图像中心
        y0 = cost_volume.shape[0] // 2
        x0 = cost_volume.shape[1] // 2
        costs = cost_volume[y0, x0, :]
        ax.plot(costs, 'b-', linewidth=1)
        ax.set_title(f'Cost curve at center ({x0}, {y0})')
        ax.set_xlabel('Disparity')
        ax.set_ylabel('Cost')

    return ax


def plot_comparison(results: dict,
                    imgL: np.ndarray,
                    imgR: np.ndarray,
                    save_path: str | None = None) -> plt.Figure:
    """对比多种方法的结果。"""
    n_methods = len(results)
    n_cols = 1 + n_methods  # 第1列留给原图，其余给各方法
    fig, axes = plt.subplots(2, n_cols, figsize=(4 * n_cols, 9))

    # 第一行：左图 + 各方法的视差图
    axes[0, 0].imshow(imgL, cmap='gray')
    axes[0, 0].set_title('Left Image')
    axes[0, 0].axis('off')

    axes[1, 0].imshow(imgR, cmap='gray')
    axes[1, 0].set_title('Right Image')
    axes[1, 0].axis('off')

    for i, (name, result) in enumerate(results.items()):
        disparity = result['disparity']
        valid = disparity > 0
        disp = disparity.copy()
        disp[~valid] = np.nan

        axes[0, i + 1].imshow(disp, cmap=DISPARITY_CMAP)
        axes[0, i + 1].set_title(f'{name}')
        axes[0, i + 1].axis('off')

        # 第二行：深度图 + 统计信息
        depth = np.zeros_like(disparity)
        if valid.any():
            depth[valid] = 615.0 * 0.10 / disparity[valid]
        axes[1, i + 1].imshow(depth, cmap='plasma')
        valid_pct = valid.sum() / valid.size * 100
        axes[1, i + 1].set_title(f'Depth | valid={valid_pct:.1f}%')
        axes[1, i + 1].axis('off')

    # 隐藏多余的子图
    for j in range(n_methods + 1, n_cols):
        for row in range(2):
            axes[row, j].axis('off')

    fig.suptitle('Stereo Matching — Method Comparison', fontsize=14)
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path)
        print(f"  → 保存到 {save_path}")

    return fig


# ============================================================
# Open3D 点云交互可视化
# ============================================================

def visualize_pointcloud(pcd: o3d.geometry.PointCloud,
                         window_name: str = 'Point Cloud',
                         width: int = 1024,
                         height: int = 768):
    """Open3D 交互式点云可视化。"""
    o3d.visualization.draw_geometries(
        [pcd],
        window_name=window_name,
        width=width,
        height=height,
        point_show_normal=False,
    )


def save_pointcloud(pcd: o3d.geometry.PointCloud, path: str):
    """保存点云为 PLY 文件。"""
    o3d.io.write_point_cloud(path, pcd)
    print(f"  → 点云保存到 {path}")


# ============================================================
# 3D 视差/点云对比（静态截图）
# ============================================================

def plot_pointcloud_projection(pcd: o3d.geometry.PointCloud,
                                save_path: str | None = None) -> plt.Figure:
    """将点云投影到 2D 平面上可视化（三视图）。

    不需要 Open3D 窗口，适合在 notebook 中使用。
    """
    points = np.asarray(pcd.points)
    colors = np.asarray(pcd.colors)

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    titles = ['XY (Front View)', 'XZ (Top View)', 'YZ (Side View)']
    data = [(0, 1, 'X', 'Y'), (0, 2, 'X', 'Z'), (1, 2, 'Y', 'Z')]

    # 降采样以防太密
    n = min(len(points), 100000)
    idx = np.random.choice(len(points), n, replace=False)
    pts = points[idx]
    col = colors[idx]

    for ax, (i, j, xl, yl), title in zip(axes, data, titles):
        ax.scatter(pts[:, i], pts[:, j], c=col, s=0.1, alpha=0.6)
        ax.set_xlabel(xl)
        ax.set_ylabel(yl)
        ax.set_title(title)
        ax.set_aspect('equal')
        ax.invert_yaxis()

    fig.suptitle('Point Cloud Projections')
    plt.tight_layout()

    if save_path:
        Path(save_path).parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150)
        print(f"  → 保存到 {save_path}")

    return fig
