"""
立体匹配 pipeline：WTA 视差选择、后处理、SGM/SGBM
"""

from __future__ import annotations

import numpy as np
import cv2
from .costs import sad_cost, census_cost

# ============================================================
# Winner-Takes-All (WTA) 视差选择
# ============================================================

def winner_takes_all(cost_volume: np.ndarray) -> np.ndarray:
    """最简单的视差选择——对每个像素，直接取代价最小的视差。

    Args:
        cost_volume: (H, W, max_disparity)

    Returns:
        disparity: (H, W)，每个像素的视差值，无效像素为 -1
    """
    H, W, D = cost_volume.shape
    disparity = np.full((H, W), -1, dtype=np.float32)

    # 对每个像素找最小代价的视差
    valid_mask = np.any(np.isfinite(cost_volume), axis=2)
    disparity[valid_mask] = np.argmin(cost_volume[valid_mask], axis=1)

    return disparity


def subpixel_refinement(cost_volume: np.ndarray,
                        disparity: np.ndarray) -> np.ndarray:
    """子像素细化：用抛物线拟合法将视差精度提升到亚像素。

    对每个像素，用最小代价 d* 及相邻 d*-1, d*+1 的代价做抛物线拟合，
    取抛物线顶点的位置作为亚像素视差。
    """
    H, W, D = cost_volume.shape
    refined = disparity.copy().astype(np.float32)

    for y in range(H):
        for x in range(W):
            d = int(disparity[y, x])
            if d <= 0 or d >= D - 1:
                continue
            if not np.isfinite(cost_volume[y, x, d]):
                continue

            c0 = cost_volume[y, x, d - 1]
            c1 = cost_volume[y, x, d]
            c2 = cost_volume[y, x, d + 1]

            if not (np.isfinite(c0) and np.isfinite(c2)):
                continue

            # 抛物线顶点: d* = d - 0.5 * (c2-c0) / (c0+c2-2*c1)
            denom = c0 + c2 - 2 * c1
            if abs(denom) > 1e-8:
                delta = (c0 - c2) / (2 * denom)
                if -0.5 < delta < 0.5:
                    refined[y, x] = d + delta

    return refined


# ============================================================
# 左右一致性检查 (Left-Right Consistency Check)
# ============================================================

def left_right_consistency(dispL: np.ndarray, dispR: np.ndarray,
                           threshold: float = 1.0) -> np.ndarray:
    """遮挡检测：比较左右视差图的一致性。

    |D_L(x,y) - D_R(x - D_L(x,y), y)| > threshold → 遮挡/错误

    Returns:
        mask: (H, W) bool 数组，True=有效，False=遮挡/无效
    """
    H, W = dispL.shape
    mask = np.zeros((H, W), dtype=bool)

    for y in range(H):
        for x in range(W):
            dL = dispL[y, x]
            if dL <= 0:
                continue
            xR = int(round(x - dL))
            if xR < 0 or xR >= W:
                continue
            dR = dispR[y, xR]
            if dR <= 0:
                continue
            if abs(dL - dR) <= threshold:
                mask[y, x] = True

    return mask


# ============================================================
# 后处理
# ============================================================

def post_process(disparity: np.ndarray,
                 lr_mask: np.ndarray | None = None) -> np.ndarray:
    """标准后处理 pipeline。

    1. 左右一致性剔除
    2. 中值滤波去噪
    3. 孔洞填充（背景蔓延）
    """
    disp = disparity.copy()

    # 左右一致性
    if lr_mask is not None:
        disp[~lr_mask] = -1

    # 中值滤波（仅对有效像素）
    valid = disp >= 0
    if valid.any():
        disp_filt = cv2.medianBlur(disp.astype(np.float32), 5)
        disp[valid] = disp_filt[valid]

    # 孔洞填充：用左侧最近的有效视差填充（背景蔓延）
    filled = disp.copy()
    for y in range(disp.shape[0]):
        row = disp[y]
        last_valid = -1
        for x in range(disp.shape[1]):
            if row[x] >= 0:
                last_valid = row[x]
            elif last_valid >= 0:
                filled[y, x] = last_valid

    return filled


# ============================================================
# 完整匹配 pipeline
# ============================================================

def stereo_match(imgL: np.ndarray, imgR: np.ndarray,
                 method: str = 'sad',
                 max_disparity: int = 64,
                 window_size: int = 5,
                 census_win: int = 7,
                 do_lr_check: bool = True,
                 do_subpixel: bool = True,
                 verbose: bool = True) -> dict:
    """完整的双目立体匹配 pipeline。

    Args:
        imgL, imgR: 左右灰度图像
        method: 'sad' | 'ssd' | 'ncc' | 'census' | 'ad-census'
        max_disparity: 最大视差搜索范围
        window_size: 匹配窗口大小
        census_win: Census 变换窗口大小
        do_lr_check: 是否做左右一致性检测
        do_subpixel: 是否做子像素细化
        verbose: 是否打印进度

    Returns:
        dict with keys: disparity, disparityL, disparityR,
                        cost_volume, mask, method, params
    """
    H, W = imgL.shape

    # 1. 计算代价体
    if verbose:
        print(f"[匹配] 方法={method}, 视差范围=0-{max_disparity-1}, 窗口={window_size}")

    if method == 'sad':
        costL = sad_cost(imgL, imgR, max_disparity, window_size)
        # 右图代价（左右翻转，用于一致性检测）
        costR = sad_cost(imgR[:, ::-1], imgL[:, ::-1], max_disparity, window_size) \
            if do_lr_check else None
    elif method == 'ssd':
        from .costs import ssd_cost
        costL = ssd_cost(imgL, imgR, max_disparity, window_size)
        costR = ssd_cost(imgR[:, ::-1], imgL[:, ::-1], max_disparity, window_size) \
            if do_lr_check else None
    elif method == 'ncc':
        from .costs import ncc_cost
        costL = ncc_cost(imgL, imgR, max_disparity, window_size)
        costR = ncc_cost(imgR[:, ::-1], imgL[:, ::-1], max_disparity, window_size) \
            if do_lr_check else None
    elif method == 'census':
        costL = census_cost(imgL, imgR, max_disparity, census_win)
        costR = census_cost(imgR[:, ::-1], imgL[:, ::-1], max_disparity, census_win) \
            if do_lr_check else None
    elif method == 'ad-census':
        from .costs import ad_census_cost
        costL = ad_census_cost(imgL, imgR, max_disparity, window_size, census_win)
        costR = ad_census_cost(imgR[:, ::-1], imgL[:, ::-1], max_disparity, window_size, census_win) \
            if do_lr_check else None
    else:
        raise ValueError(f"未知方法: {method}")

    # 2. WTA 视差选择
    if verbose:
        print("  → WTA 视差选择...")
    dispL = winner_takes_all(costL)

    # 3. 左右一致性
    lr_mask = None
    if do_lr_check and costR is not None:
        if verbose:
            print("  → 左右一致性检查...")
        dispR = winner_takes_all(costR)
        # dispR 是翻转后的，需要翻转回来
        dispR_flipped = dispR[:, ::-1]
        lr_mask = left_right_consistency(dispL, dispR_flipped)
        if verbose:
            valid_ratio = lr_mask.sum() / lr_mask.size
            print(f"    一致性通过率: {valid_ratio:.1%}")

    # 4. 子像素细化
    if do_subpixel:
        if verbose:
            print("  → 子像素细化...")
        dispL = subpixel_refinement(costL, dispL)

    # 5. 后处理
    if verbose:
        print("  → 后处理...")
    disp_final = post_process(dispL, lr_mask)

    dispR = None
    if do_lr_check and costR is not None:
        dispR = winner_takes_all(costR)

    return {
        'disparity': disp_final,
        'disparity_raw': winner_takes_all(costL),
        'disparityL': dispL,
        'disparityR': dispR,
        'cost_volume': costL,
        'lr_mask': lr_mask,
        'method': method,
        'params': {
            'max_disparity': max_disparity,
            'window_size': window_size,
            'census_win': census_win,
        }
    }


# ============================================================
# OpenCV SGBM 封装（做对比基线）
# ============================================================

def stereo_sgbm(imgL: np.ndarray, imgR: np.ndarray,
                max_disparity: int = 64, block_size: int = 5) -> dict:
    """OpenCV SGBM 封装，作为对比基线。"""
    stereo = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=max_disparity,
        blockSize=block_size,
        P1=8 * 3 * block_size ** 2,
        P2=32 * 3 * block_size ** 2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=100,
        speckleRange=32,
    )
    disparity = stereo.compute(imgL, imgR).astype(np.float32) / 16.0

    return {
        'disparity': disparity,
        'method': 'sgbm',
        'params': {
            'max_disparity': max_disparity,
            'block_size': block_size,
        }
    }
