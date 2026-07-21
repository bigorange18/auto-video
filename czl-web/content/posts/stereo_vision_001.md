---
title: "双目立体视觉 & 点云生成"
summary: "双目立体视觉核心原理、数学模型、算法对比与Python代码实现，从三角测量到立体匹配到点云生成。"
type: blog
tags:
  - 计算机视觉
  - 立体视觉
  - 3D
  - 点云
  - SGBM
published: true
createdAt: "2026-07-06T00:00:00.000Z"
updatedAt: "2026-07-06T00:00:00.000Z"
---

# 双目立体视觉 & 点云生成

## 一、整体流程

```
左相机图像 ──┐
            ├──> 立体匹配(视差估计) ──> 视差图 ──> 深度图 ──> 点云
右相机图像 ──┘
```

核心链路：**双目图 → 视差图 → 深度图 → 点云**

---

## 二、数学模型

### 1. 三角测量原理

理想双目模型（两个相机光轴平行，基线为 $B$，焦距为 $f$）：

设点 $P(X,Y,Z)$ 在左图的像素坐标为 $(x_L, y)$，在右图的像素坐标为 $(x_R, y)$，

**视差**：$d = x_L - x_R$

**深度**：$Z = \frac{f \cdot B}{d}$

这是核心公式——**深度与视差成反比**。视差越大，物体越近；视差越小，物体越远。

### 2. 从深度到点云

有了深度图后，每个像素 $(u, v)$ 对应的 3D 坐标为：

$$
\begin{cases}
X = \frac{(u - c_x) \cdot Z}{f} \\[6pt]
Y = \frac{(v - c_y) \cdot Z}{f} \\[6pt]
Z = \frac{f \cdot B}{d}
\end{cases}
$$

其中 $(c_x, c_y)$ 是相机光心（主点坐标），来自相机内参矩阵 $K$。

---

## 三、核心算法——立体匹配

### 1. 传统方法

#### 块匹配（Block Matching）

| 相似度度量 | 特点 |
|---|---|
| SAD | 快但不鲁棒 |
| SSD | 对大误差更敏感 |
| NCC | 对光照变化鲁棒 |
| Census Transform | 对光照最鲁棒 |

#### SGBM（Semi-Global Block Matching）

OpenCV 内置的经典方法，通过 8 个方向的动态规划近似全局优化。

### 2. 深度学习方法

| 方法类别 | 代表模型 | 特点 |
|---|---|---|
| 2D卷积+3D Cost Volume | PSMNet, GwcNet | 构建 cost volume + 3D CNN |
| 迭代优化 | RAFT-Stereo | GRU 迭代更新视差 |
| Transformer | STTR, CroCo | cross-attention 做匹配 |
| 实时轻量 | Fast-ACV, HITNet | 适合嵌入式场景 |

---

## 四、Python 代码实现

### OpenCV SGBM

```python
import cv2
import numpy as np

def compute_disparity(img_left, img_right):
    stereo = cv2.StereoSGBM_create(
        minDisparity=0,
        numDisparities=128,
        blockSize=11,
        P1=8 * 3 * 11**2,
        P2=32 * 3 * 11**2,
        disp12MaxDiff=1,
        uniquenessRatio=10,
        speckleWindowSize=100,
        speckleRange=32,
        mode=cv2.STEREO_SGBM_MODE_SGBM_3WAY
    )
    disparity = stereo.compute(img_left, img_right).astype(np.float32) / 16.0
    return disparity

def disparity_to_pointcloud(disparity, Q):
    points_3d = cv2.reprojectImageTo3D(disparity, Q)
    mask = disparity > disparity.min()
    return points_3d[mask]
```

---

## 五、总结

| 方案 | 速度 | 精度 | 适用场景 |
|---|---|---|---|
| BM | 快 | 低 | 实时粗估 |
| SGBM | 中 | 中高 | 通用场景 |
| PSMNet | 慢 | 高 | 离线精确重建 |
| RAFT-Stereo | 中 | 很高 | 平衡精度/速度 |
