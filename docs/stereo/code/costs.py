"""
立体匹配代价函数：SAD, SSD, NCC, Census Transform

每个函数输入：
  - imgL, imgR: 左右灰度图像 (H, W)，dtype=uint8
  - max_disparity: 最大搜索视差
  - window_size: 匹配窗口大小(奇数)

输出：
  - cost_volume: (H, W, max_disparity) 的代价张量
    cost_volume[y, x, d] = 左图(x,y) 与 右图(x-d,y) 的匹配代价
    SAD/SSD/Census: 代价越小越相似
    NCC: 相关性越高越相似（取负值统一为越小越相似）
"""

import numpy as np
from scipy.ndimage import uniform_filter


# ============================================================
# 工具函数
# ============================================================

def _box_sum(img: np.ndarray, window_size: int) -> np.ndarray:
    """用均值滤波器实现窗口求和：sum = uniform_filter * window_area"""
    area = window_size * window_size
    return uniform_filter(img.astype(np.float64), size=window_size,
                          mode='constant', cval=0.0) * area


# ============================================================
# SAD — Sum of Absolute Differences
# ============================================================

def sad_cost(imgL: np.ndarray, imgR: np.ndarray,
             max_disparity: int = 64, window_size: int = 5) -> np.ndarray:
    """SAD 匹配代价。

    C(p,d) = Σ|I_L(q) - I_R(q-d)| , q ∈ W(p)

    用 box filter (uniform_filter) 高效计算窗口和。
    """
    H, W = imgL.shape
    half = window_size // 2
    imgL = imgL.astype(np.float64)
    imgR = imgR.astype(np.float64)

    cost = np.full((H, W, max_disparity), np.inf, dtype=np.float64)

    for d in range(max_disparity):
        # 右图向左平移 d（等价于左图向右平移 d）
        diff = np.abs(imgL - np.roll(imgR, d, axis=1))
        diff[:, :d] = 0.0  # 无效区域

        # 窗口和
        sad = _box_sum(diff, window_size)

        # 边界区域（half 像素宽）无效
        sad[:half, :] = np.inf
        sad[-half:, :] = np.inf
        sad[:, :half] = np.inf
        sad[:, -half:] = np.inf

        # 左图的 x < d 区域无法找到有效对应点
        sad[:, :d] = np.inf

        cost[:, :, d] = sad

    return cost


# ============================================================
# SSD — Sum of Squared Differences
# ============================================================

def ssd_cost(imgL: np.ndarray, imgR: np.ndarray,
             max_disparity: int = 64, window_size: int = 5) -> np.ndarray:
    """SSD 匹配代价。

    C(p,d) = Σ(I_L(q) - I_R(q-d))² , q ∈ W(p)
    """
    H, W = imgL.shape
    half = window_size // 2
    imgL = imgL.astype(np.float64)
    imgR = imgR.astype(np.float64)

    cost = np.full((H, W, max_disparity), np.inf, dtype=np.float64)

    for d in range(max_disparity):
        diff = imgL - np.roll(imgR, d, axis=1)
        diff[:, :d] = 0.0

        ssd = _box_sum(diff ** 2, window_size)

        ssd[:half, :] = np.inf
        ssd[-half:, :] = np.inf
        ssd[:, :half] = np.inf
        ssd[:, -half:] = np.inf
        ssd[:, :d] = np.inf

        cost[:, :, d] = ssd

    return cost


# ============================================================
# NCC — Normalized Cross-Correlation
# ============================================================

def ncc_cost(imgL: np.ndarray, imgR: np.ndarray,
             max_disparity: int = 64, window_size: int = 5) -> np.ndarray:
    """NCC 匹配代价。

    NCC ∈ [-1, 1]，1=完全正相关，-1=完全负相关。
    返回 -NCC 使"越小越相似"。

    用积分图高效计算窗口均值、方差和协方差：
        NCC = cov(L,R) / (σ_L · σ_R)
        cov(L,R) = E[L·R] - E[L]·E[R]
    """
    H, W = imgL.shape
    half = window_size // 2
    imgL = imgL.astype(np.float64)
    imgR = imgR.astype(np.float64)
    eps = 1e-8
    area = window_size * window_size

    # 预计算左图统计量
    meanL = _box_sum(imgL, window_size) / area
    sqL = _box_sum(imgL ** 2, window_size) / area
    varL = sqL - meanL ** 2

    cost = np.full((H, W, max_disparity), np.inf, dtype=np.float64)

    for d in range(max_disparity):
        R_shifted = np.roll(imgR, d, axis=1)
        R_shifted[:, :d] = 0.0

        # 右图统计量
        meanR = _box_sum(R_shifted, window_size) / area
        sqR = _box_sum(R_shifted ** 2, window_size) / area
        varR = sqR - meanR ** 2

        # 协方差
        cross = _box_sum(imgL * R_shifted, window_size) / area
        covLR = cross - meanL * meanR

        # NCC
        std_prod = np.sqrt(np.maximum(varL * varR, 0)) + eps
        ncc = covLR / std_prod

        # 边界无效
        ncc[:half, :] = np.inf
        ncc[-half:, :] = np.inf
        ncc[:, :half] = np.inf
        ncc[:, -half:] = np.inf
        ncc[:, :d] = np.inf

        cost[:, :, d] = -ncc  # 取负号

    return cost


# ============================================================
# Census Transform
# ============================================================

def census_transform(img: np.ndarray, window_size: int = 7) -> np.ndarray:
    """计算 Census Transform。

    对每个像素，将它邻域的像素值与中心像素比较，
    生成一个二进制串。

    返回: (H, W, N) 的 uint8 数组，N = window_size² - 1
         bit i = 1 表示邻域像素 i >= 中心像素
    """
    H, W = img.shape
    half = window_size // 2
    N = window_size * window_size - 1

    census = np.zeros((H, W, N), dtype=np.uint8)

    idx = 0
    for dy in range(-half, half + 1):
        for dx in range(-half, half + 1):
            if dy == 0 and dx == 0:
                continue
            shifted = np.roll(np.roll(img, -dy, axis=0), -dx, axis=1)
            census[:, :, idx] = (shifted >= img).astype(np.uint8)
            idx += 1

    # 边界标记为 0
    census[:half, :, :] = 0
    census[-half:, :, :] = 0
    census[:, :half, :] = 0
    census[:, -half:, :] = 0

    return census


def census_cost(imgL: np.ndarray, imgR: np.ndarray,
                max_disparity: int = 64, census_win: int = 7) -> np.ndarray:
    """Census Transform + Hamming 距离代价。

    对左右图分别计算 Census Transform，
    用 Hamming 距离（= XOR 后 popcount）作为匹配代价。
    对光照变化和噪声最鲁棒。
    """
    H, W = imgL.shape
    half = census_win // 2

    print(f"  计算 Census Transform (窗口 {census_win}x{census_win})...")
    censusL = census_transform(imgL, census_win)
    censusR = census_transform(imgR, census_win)

    cost = np.full((H, W, max_disparity), np.inf, dtype=np.float64)

    print(f"  计算 Hamming 代价 (视差 0-{max_disparity-1})...")
    # 向量化 Hamming 距离：对每个视差 d，将 censusR 平移 d 像素
    for d in range(max_disparity):
        shifted = np.roll(censusR, d, axis=1)
        shifted[:, :d, :] = 0

        # XOR → sum over bits = Hamming distance
        hamming = np.sum(censusL != shifted, axis=2).astype(np.float64)

        # 标记无效
        hamming[:half, :] = np.inf
        hamming[-half:, :] = np.inf
        hamming[:, :half] = np.inf
        hamming[:, -half:] = np.inf
        hamming[:, :d] = np.inf

        cost[:, :, d] = hamming

    return cost


# ============================================================
# AD-Census 融合
# ============================================================

def ad_census_cost(imgL: np.ndarray, imgR: np.ndarray,
                   max_disparity: int = 64,
                   window_size: int = 5,
                   census_win: int = 7,
                   alpha: float = 0.5) -> np.ndarray:
    """AD-Census: SAD + Census 加权融合。

    cost = α·SAD_norm + (1-α)·Census_norm
    """
    cost_sad = sad_cost(imgL, imgR, max_disparity, window_size)
    cost_census = census_cost(imgL, imgR, max_disparity, census_win)

    # 各自归一化到 [0, 1]
    def _normalize(c):
        finite = np.isfinite(c)
        if not finite.any():
            return c
        cmin, cmax = c[finite].min(), c[finite].max()
        if cmax - cmin < 1e-8:
            return c
        return (c - cmin) / (cmax - cmin)

    sad_norm = _normalize(cost_sad)
    census_norm = _normalize(cost_census)

    return alpha * sad_norm + (1 - alpha) * census_norm


# ============================================================
# 元数据
# ============================================================

COST_FUNCTIONS = {
    'sad':       sad_cost,
    'ssd':       ssd_cost,
    'ncc':       ncc_cost,
    'census':    census_cost,
    'ad-census': ad_census_cost,
}

COST_DESCRIPTIONS = {
    'sad':       'SAD (Sum of Absolute Differences) — 最快，对噪声敏感',
    'ssd':       'SSD (Sum of Squared Differences) — 对大误差惩罚更重',
    'ncc':       'NCC (Normalized Cross-Correlation) — 对线性光照不变',
    'census':    'Census Transform + Hamming — 对光照和噪声最鲁棒',
    'ad-census': 'AD-Census — SAD + Census 融合',
}
