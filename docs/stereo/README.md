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

其中 $(c_x, c_y)$ 是相机光心（主点坐标），来自相机内参矩阵 $K$：

$$
K = \begin{bmatrix}
f_x & 0 & c_x \\
0 & f_y & c_y \\
0 & 0 & 1
\end{bmatrix}
$$

---

## 三、核心算法——立体匹配

这是整个流程中最关键、也最困难的一步。目标是为左图的每个像素，在右图中找到对应的像素。

### 1. 传统方法

#### 块匹配（Block Matching）

对左图中每个像素 $(u,v)$，取一个窗口 $W$，在右图的同一水平线（极线）上滑动，找最相似的窗口：

| 相似度度量 | 特点 |
|---|---|
| SAD (Sum of Absolute Differences) | 快但不鲁棒 |
| SSD (Sum of Squared Differences) | 对大误差更敏感 |
| NCC (Normalized Cross-Correlation) | 对光照变化鲁棒 |
| Census Transform + Hamming 距离 | 对光照最鲁棒 |

#### SGBM（Semi-Global Block Matching）

OpenCV 内置的经典方法，在块匹配的基础上加入平滑约束：

$$E(D) = \sum_p \underbrace{C(p, D_p)}_{\text{匹配代价}} + \sum_q \underbrace{P_1 \cdot \mathbb{1}[|D_p-D_q|=1]}_{\text{小跳变惩罚}} + \underbrace{P_2 \cdot \mathbb{1}[|D_p-D_q|>1]}_{\text{大跳变惩罚}}$$

通过 8 或 16 个方向的动态规划近似求解这个全局能量最小化问题。

### 2. 深度学习方法（目前主流）

| 方法类别 | 代表模型 | 特点 |
|---|---|---|
| 2D 卷积 + 3D Cost Volume | PSMNet, GwcNet | 构建 cost volume + 3D CNN 正则化 |
| 迭代优化 | RAFT-Stereo | 借鉴光流方法，GRU 迭代更新视差 |
| Transformer | STTR, CroCo | 用 cross-attention 做匹配，无需 cost volume |
| 实时轻量 | Fast-ACV, HITNet | 适合嵌入式/实时场景 |
| 基础模型 | Depth Anything, UniDepth | 单目也可，双目更准 |

#### PSMNet 经典流程

1. **特征提取**：共享权重的 CNN + SPP 模块提取左右图特征
2. **Cost Volume 构建**：将左特征在视差维度上平移后与右特征拼接
3. **3D CNN 正则化**：堆叠的 3D 卷积 + 堆叠沙漏结构聚合上下文
4. **视差回归**：用 soft argmin 做可微分的视差估计

$$\hat{d} = \sum_{d=0}^{D_{max}} d \cdot \text{softmax}(-cost_d)$$

---

## 四、后处理与优化

得到原始视差图后，通常需要：

| 步骤 | 方法 | 作用 |
|---|---|---|
| 左右一致性检查 | $\|D_L(p) - D_R(p - D_L(p))\| > \tau$ | 剔除遮挡区域的错误匹配 |
| 子像素细化 | 抛物线拟合 | 将离散视差细化到亚像素精度 |
| 中值/双边滤波 | — | 去除孤立噪点，边缘保持平滑 |
| 孔洞填充 | 背景蔓延 | 填充被剔除的无效区域 |

---

## 五、点云生成代码示例（Python/OpenCV + Open3D）

```python
import cv2
import numpy as np
import open3d as o3d

# 1. 读取双目图像
imgL = cv2.imread('left.png', 0)
imgR = cv2.imread('right.png', 0)

# 2. SGBM 立体匹配
stereo = cv2.StereoSGBM_create(
    minDisparity=0,
    numDisparities=128,
    blockSize=11,
    P1=8 * 3 * 11**2,
    P2=32 * 3 * 11**2,
)
disparity = stereo.compute(imgL, imgR).astype(np.float32) / 16.0

# 3. 视差 → 深度
# K: 相机内参矩阵, baseline: 基线距离(米)
focal = K[0, 0]           # fx
baseline = 0.12           # 12cm 基线
depth = np.where(disparity > 0, focal * baseline / disparity, 0)

# 4. 深度 → 点云
h, w = depth.shape
u, v = np.meshgrid(np.arange(w), np.arange(h))
X = (u - K[0, 2]) * depth / focal
Y = (v - K[1, 2]) * depth / focal
Z = depth

points = np.stack([X, Y, Z], axis=-1).reshape(-1, 3)
mask = Z.reshape(-1) > 0
points = points[mask]
colors = imgL.reshape(-1, 1).repeat(3, axis=-1)[mask] / 255.0

# 5. 可视化
pcd = o3d.geometry.PointCloud()
pcd.points = o3d.utility.Vector3dVector(points)
pcd.colors = o3d.utility.Vector3dVector(colors)
o3d.visualization.draw_geometries([pcd])
```

---

## 六、关键难点

| 难点 | 说明 | 应对策略 |
|---|---|---|
| **遮挡** | 左图能看到但右图看不到的区域 | 左右一致性检查 + 遮挡推理网络 |
| **无纹理区域** | 白墙、天空等无特征区域无法匹配 | 全局优化（SGM）、更大感受野 |
| **重复纹理** | 栅栏、地砖等造成歧义匹配 | 多尺度特征 + 上下文信息 |
| **光照变化** | 左右相机曝光/白平衡不一致 | Census Transform、颜色归一化 |
| **反射/透明** | 镜子、玻璃不满足朗伯假设 | 基于学习的隐式先验 |
| **大视差/近物** | 基线固定，太近物体视差过大超出搜索范围 | 金字塔/由粗到细策略 |

---

## 七、常见评估指标

| 指标 | 含义 |
|---|---|
| **EPE** (End-Point Error) | 预测视差与真实视差的欧氏距离均值 |
| **D1-all** | 坏像素比例（误差 > max(3px, 5%) 的像素占比） |
| **RMSE** | 深度/视差的均方根误差 |
| **>Npx** | 误差超过 N 个像素的百分比 |

---

## 八、主流数据集

| 数据集 | 场景 | 规模 |
|---|---|---|
| Scene Flow | 合成场景（FlyingThings3D, Driving, Monkaa） | ~39,000 对 |
| KITTI 2012/2015 | 自动驾驶街景 | ~400 对 |
| Middlebury | 室内高精度标定场景 | ~30 对 |
| ETH3D | 室内外高分辨率 | ~30 对 |
