# 双目立体匹配算法综述：从 SAD 到 Foundation Model

> 本文系统梳理双目立体匹配的核心算法演进，从传统匹配代价函数到 2025 年的基础模型，涵盖原理推导、架构对比和发展趋势分析。

---

## 目录

1. [问题定义与数学基础](#1-问题定义与数学基础)
2. [传统立体匹配方法](#2-传统立体匹配方法)
3. [深度学习的兴起](#3-深度学习的兴起)
4. [迭代优化范式](#4-迭代优化范式)
5. [Transformer 与全局匹配](#5-transformer-与全局匹配)
6. [基础模型与零样本泛化](#6-基础模型与零样本泛化)
7. [实时与轻量级方法](#7-实时与轻量级方法)
8. [全景对比与分析](#8-全景对比与分析)
9. [未来方向](#9-未来方向)

---

## 1. 问题定义与数学基础

### 1.1 核心问题

双目立体匹配的目标是：给定一对经过极线校正的左右图像 $I_L, I_R \in \mathbb{R}^{H \times W \times 3}$，为左图中的每个像素 $(u,v)$，在右图中找到对应像素 $(u', v)$，使得二者是同一 3D 点在不同视角下的投影。由于已做极线校正，对应点必然在同一水平线上，即 $v' = v$。

**视差（Disparity）**：$d = u - u'$

### 1.2 三角测量

在理想平行双目模型中：

$$
Z = \frac{f \cdot B}{d}
$$

其中 $f$ 为焦距，$B$ 为基线距离，$Z$ 为深度。这是整个立体视觉的基石——**深度与视差成反比**。

### 1.3 标准流程

```
左右图像 → 匹配代价计算 → 代价聚合 → 视差计算 → 视差精化 → 视差图
```

这个四阶段框架（Scharstein & Szeliski, 2002）至今仍是理解所有立体匹配算法的基本蓝图。

---

## 2. 传统立体匹配方法

### 2.1 匹配代价函数

匹配代价衡量左右图两个像素（或窗口）的相似程度。这是立体匹配最底层的"原子操作"，所有方法都建筑在它之上。

#### 2.1.1 基于灰度的代价

**SAD (Sum of Absolute Differences)**

$$
C_{SAD}(p, d) = \sum_{q \in W_p} |I_L(q) - I_R(q - d)|
$$

- 最朴素、最快的代价函数
- 对光照变化和噪声极度敏感
- 通常配合窗口滑动使用，窗口越大越鲁棒但也越模糊

**SSD (Sum of Squared Differences)**

$$
C_{SSD}(p, d) = \sum_{q \in W_p} (I_L(q) - I_R(q - d))^2
$$

- 对大误差惩罚更重（平方增长）
- 对异常值（outlier）比 SAD 更敏感
- 在光度一致性假设下等价于高斯噪声的 MLE

**NCC (Normalized Cross-Correlation)**

$$
C_{NCC}(p, d) = \frac{\sum_q (I_L(q) - \bar{I}_L) \cdot (I_R(q-d) - \bar{I}_R)}{\sqrt{\sum_q (I_L(q) - \bar{I}_L)^2 \cdot \sum_q (I_R(q-d) - \bar{I}_R)^2}}
$$

- 归一化消除了均值和方差的差异
- 对线性光照变化完全不变（加减常数、乘以常数均不影响结果）
- 计算量大，但工程中可借助积分图加速
- NCC 越接近 1 表示越相似（与 SAD/SSD 越小越好不同）

#### 2.1.2 Census Transform（普查变换）

**核心思想**：不用原始灰度值，而是编码邻域像素的相对大小关系。

对像素 $p$ 的一个窗口（如 7×7 或 9×9），将每个邻域像素与中心像素比较：

$$
\xi(I(p), I(q)) = \begin{cases} 1 & \text{if } I(q) \geq I(p) \\ 0 & \text{otherwise} \end{cases}
$$

将比较结果串联为一个二进制串（Census 序列），匹配代价为该二进制串的 **Hamming 距离**：

$$
C_{Census}(p, d) = \text{Hamming}(T_L(p), T_R(p-d))
$$

**为什么好用**：

- 对**单调的光照变化完全不变**（亮度整体加减不影响相对大小关系）
- 对噪声鲁棒（偶尔一个像素翻转只影响二进制串的 1 bit）
- 对左右相机曝光不一致、渐晕（vignetting）等有天然容错
- 在现代的深度学习时代，Census 的思想仍然被继承——成本体积中的 group-wise correlation 本质上是在学习一种"可微分的 Census"

**变体**：Center-Symmetric Census（仅比较对称位置的像素对，与中心像素解耦）、稀疏 Census（跳点采样加速）等。

#### 2.1.3 其他经典代价

| 代价函数                          | 原理                                       | 特点                           |
| --------------------------------- | ------------------------------------------ | ------------------------------ |
| **BT (Birchfield-Tomasi)**  | 对像素值做线性插值，计算点到线段的最短距离 | 对采样不敏感，亚像素精度       |
| **MI (Mutual Information)** | 最大化左右图的互信息                       | 对复杂辐射度关系鲁棒，计算量大 |
| **AD-Census**               | SAD + Census 加权融合                      | 结合灰度和结构信息，工程中常用 |

### 2.2 代价聚合与视差优化

原始代价通常噪声很大，需要聚合上下文信息。

**局部聚合（窗口滤波）**：

- Box Filter（均值滤波，快但边缘模糊）
- Bilateral Filter（双边滤波，边缘保持，速度中等）
- Guided Filter（引导滤波，$O(1)$ 复杂度，边缘保持好）

**全局优化**：

- **Graph Cut**：将匹配建模为图割问题，全局最优但计算量极大
- **Belief Propagation**：在 MRF 上进行消息传递，近似全局优化

### 2.3 SGM/SGBM（半全局匹配）

SGM（Semi-Global Matching）由 Hirschmüller（2008）提出，是过去十五年最具影响力的传统方法，至今仍是嵌入式双目系统的首选。

**核心思想**：将全局 2D 优化沿多个方向分解为一维动态规划，每个方向上：

$$
L_r(p, d) = C(p, d) + \min\begin{cases} 
L_r(p-r, d) \\
L_r(p-r, d-1) + P_1 \\
L_r(p-r, d+1) + P_1 \\
\min_k L_r(p-r, k) + P_2
\end{cases} - \min_k L_r(p-r, k)
$$

- $P_1$：小视差跳变惩罚（适应倾斜表面）
- $P_2$：大视差跳变惩罚（适应物体边界）
- 最后一项减去路径最小值，防止累加溢出
- 通常使用 8 或 16 个方向（4 方向为最少可用配置）

最终代价为各方向之和：$S(p,d) = \sum_r L_r(p,d)$，取 argmin 得到视差。

**SGBM 变体**（OpenCV 实现）：

- 对灰度值做了 BT 代价 + 块匹配预处理
- Mode 类（HH、SGBM3Way）提供不同的速度/质量取舍
- 默认参数（blockSize=5~15, numDisparities=64~256）能应对大部分场景

**SGM 的优缺点**：

| 优点                                             | 缺点                                         |
| ------------------------------------------------ | -------------------------------------------- |
| 速度极快（CPU 实时，~30ms @ 720p）               | 无纹理区域退化（天空、白墙）                 |
| 不需要 GPU                                       | 遮挡区域无法处理                             |
| 可解释性强，参数物理含义明确                     | 对重复纹理产生条纹伪影                       |
| FPGA/ASIC 实现成熟（81fps @ 1080p 已有硬件方案） | 精度天花板明显，无法利用语义先验             |
| 功耗低（~1W），适合嵌入式                        | 边界处易产生膨胀效应（foreground fattening） |

---

## 3. 深度学习的兴起

### 3.1 端到端立体匹配的开端

#### MC-CNN (2015, Žbontar & LeCun)

第一个用 CNN 做立体匹配的工作。它用 Siamese 网络从左右图块中提取特征，然后计算特征向量的点积/余弦距离作为匹配代价。本质上就是用 CNN 替换了手工匹配代价（SAD/Census），但后续的代价聚合等步骤仍然是传统的。

架构要点：

- 快速版：双塔 CNN + 点积，9×9 patch，5 层
- 精确版：全连接融合 + 分类，更大的 patch
- 训练数据：从 KITTI 的 LiDAR 真值中提取正负样本对
- 意义：证明了学习到的特征比手工特征（SAD/Census/梯度）好**一个数量级**

#### DispNet (2016, Mayer et al.)

第一个完全端到端的立体匹配网络，借鉴了 FlowNet 的编码器-解码器架构：

1. **收缩部分（编码器）**：提取多尺度特征
2. **相关层（Correlation Layer）**：在对应尺度上计算左右特征的点积相关性
3. **扩张部分（解码器）**：上采样 + 跳跃连接，逐步恢复全分辨率视差图

关键贡献：在大规模合成数据（Scene Flow）上训练，证明了**端到端学习的可行性**。

### 3.2 Cost Volume 范式的确立

#### GC-Net (2017, Kendall et al.)

奠定现代立体匹配架构的里程碑工作，提出 **4D Cost Volume** 范式：

1. **特征提取**：共享权重的 2D CNN
2. **构建 Cost Volume**：将左特征图沿视差维度平移，与右特征图拼接（或计算相关性），形成 $H \times W \times D_{max} \times C$ 的 4D 张量
3. **3D CNN 正则化**：用 3D 卷积在 cost volume 上进行编码-解码，聚合空间和视差维度的上下文
4. **Soft Argmin**：沿视差维度做 softmax，取加权和作为连续视差：

   $$
   \hat{d} = \sum_{d=0}^{D_{max}} d \cdot \frac{e^{-C(d)}}{\sum_{d'} e^{-C(d')}}
   $$

   这是整个范式中最关键的设计之一——**可微分视差计算**，让网络可以从视差 Loss 直接端到端训练。

#### PSMNet (2018, Chang & Chen)

在 GC-Net 上的关键改进：

- **SPP（Spatial Pyramid Pooling）模块**：多尺度池化聚合全局上下文，显著扩大感受野
- **堆叠沙漏（Stacked Hourglass）架构**：三个沙漏级联，每个输出中间监督，逐步精化
- 在 KITTI 2015 上达到当时 SOTA，成为后续工作的标准基线

#### GwcNet (2019, Guo et al.)

提出 **Group-wise Correlation**，替代简单的拼接或点积：

- 将特征沿通道分为 $G$ 组，每组独立计算相关性
- 相比拼接（concat volume），参数量大幅减少
- 相比点积（correlation volume），保留了更多特征信息
- 成为后续几乎所有方法的标准配置

#### GA-Net (2019, Zhang et al.)

用可学习的神经网络层逼近传统 SGM：

- **SGA（Semi-Global Aggregation）层**：用可学习的引导聚合替代 SGM 的 DP 路径
- **LGA（Local Guided Aggregation）层**：替代局部代价滤波
- 证明了将传统算法的结构先验融入网络设计的有效性

### 3.3 这一范式的局限

| 问题         | 原因                                                          |
| ------------ | ------------------------------------------------------------- |
| 计算量巨大   | 3D CNN 在 4D cost volume 上运行，时间复杂度$O(HWD \cdot C)$ |
| 内存墙       | 4D volume 需要大量显存，限制了大视差范围和批大小              |
| 视差范围固定 | $D_{max}$ 是硬超参，不同场景需要不同设置                    |
| 感受野有限   | 即使 SPP+沙漏，长距离依赖仍然不足                             |

---

## 4. 迭代优化范式

Cost Volume + 3D CNN 范式统治近五年后，一个全新的范式从光流领域传入。

### 4.1 RAFT-Stereo (3DV 2021)

**来源**：普林斯顿的 RAFT（光流）+ 极线约束。

**核心创新**——将立体匹配从"一步到位"重构为"迭代精化"：

```
初始视差 = 0 → ConvGRU查相关 → 更新δ → 视差 += δ → 再查 → 再更新 → ... → 最终视差
```

#### 架构细节

| 组件                         | 设计                                                                                                                       |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **特征提取**           | 共享权重的 2D CNN（类 ResNet），输出 1/8 分辨率特征。另有 Context Encoder 提供初始化 GRU 隐藏状态的上下文特征              |
| **Correlation Volume** | 利用极线约束将 4D volume 降为 3D（$H \times W \times W$，仅沿水平扫描线做点积），多尺度池化构建金字塔（1/8, 1/16, 1/32） |
| **Update Operator**    | 多层级 ConvGRU：1/8、1/16、1/32 分辨率并行更新，层间有 cross-connection。所有迭代共享权重                                  |
| **迭代次数**           | 训练用 22 次，推理可灵活调整（时间换精度）                                                                                 |

#### 为什么这是范式级突破

1. **省内存**：不需要存储 4D volume + 3D CNN 中间激活，correlation pyramid 是 lookup 出来的
2. **收敛可观测**：可以 plot 视差随迭代的变化，debug 体验远好于黑盒 3D CNN
3. **自适应计算**：简单区域 3 次迭代就够，困难区域可以多迭代
4. **全 2D 卷积**：不涉及任何 3D 操作，推理速度快

#### 局限

- 初始化为 0，需要多次迭代才能收敛到合理值
- 全对相关（all-pairs correlation）缺乏非局部几何先验
- 假设完美校正，对实际相机的微小旋转敏感

### 4.2 CREStereo (CVPR 2022 Oral)

Megvii/Face++ 的工作，直接对标 RAFT-Stereo，解决三个实际问题：**精细结构、不完美校正、困难场景**。

#### 三大创新

**① 级联循环网络（Cascaded Recurrent Network）**

不是单一精度的迭代，而是由粗到细三级级联：

```
1/16 → RUM迭代(初始=0) → 上采样 → 1/8 → RUM迭代(初始=1/16结果) → 上采样 → 1/4 → RUM迭代
```

每级的 RUM（Recurrent Update Module）共享权重。推理时还可以用 stacked cascade 将图像金字塔逐级送入。

**② 自适应组相关层（Adaptive Group Correlation Layer, AGCL）**

CREStereo 最核心的贡献——将 RAFT-Stereo 的全局全对相关替换为四个层次的渐进式增强：

| 层次                               | 机制                                       | 解决的问题                       |
| ---------------------------------- | ------------------------------------------ | -------------------------------- |
| **Local Correlation**        | 仅在局部窗口内计算相关性                   | 省内存、省计算、更精确的局部匹配 |
| **2D-1D Alternating Search** | 在 1D（水平极线）和 2D（网格）搜索之间交替 | 处理不完美校正导致的垂直偏移     |
| **Deformable Search Window** | 学习每个像素的搜索偏移量$(dx, dy)$       | 自适应遮挡和无纹理区域的搜索策略 |
| **Group-wise Correlation**   | 特征按通道分组、组内独立相关               | 增加匹配特征的表达力             |

这四个机制叠加，让 CREStereo 在真实场景（尤其是手机双摄等不完美校正场景）中远超 RAFT-Stereo。

**③ 专用合成数据集**

用 Blender 渲染了专门针对立体匹配难点的训练数据：

- 细薄结构（树、铁丝网、线缆）
- 反射/金属表面
- 透明材质（玻璃）
- 重复纹理
- 大视差范围

**性能**：

| 指标               | RAFT-Stereo | CREStereo          |
| ------------------ | ----------- | ------------------ |
| Middlebury Bad 2.0 | ~4.74%      | ~3.71%             |
| ETH3D Bad 1.0      | 基线        | **↓59.84%** |
| 泛化能力           | 中等        | 显著更强           |

### 4.3 IGEV-Stereo (CVPR 2023, TPAMI 2025)

华中科技大学的工作，**融合了 Cost Volume 范式和迭代范式的优点**。

#### 核心洞察

- Cost Volume + 3D CNN 的方法编码了全局几何信息，但计算量大
- RAFT-Stereo 类的迭代方法高效，但缺乏非局部几何上下文
- **两者不是对立的，融合它们可以取得更好的效果**

#### 两大创新

**① Geometry Encoding Volume (GEV)**

不是直接使用 raw correlation volume，而是：

1. 构建 group-wise correlation cost volume
2. 通过超轻量级 3D UNet（仅 3 层下/上采样，通道数 16/32/48）做代价正则化
3. 用 **Guided Cost Volume Excitation**：由左图特征生成通道注意力权重，增强关键特征维度
4. 从 GEV 通过 soft-argmin 回归**初始视差 $d_0$**（不再是零初始化！）

**② Combined Geometry Encoding Volume (CGEV)**

- GEV 编码全局几何但可能过平滑精细细节
- All-Pairs Correlation (APC) 保留局部细节但缺乏全局上下文
- **CGEV = GEV + APC 拼接**：ConvGRU 从两者的交集中索引

#### 对比优势

| 指标           | RAFT-Stereo (32 iter) | IGEV-Stereo (3 iter) | 提升    |
| -------------- | --------------------- | -------------------- | ------- |
| Scene Flow EPE | 0.53                  | **0.47**       | ↓11%   |
| KITTI 2015 D1  | 1.82%                 | **1.59%**      | ↓12.6% |
| 内存           | 1.02 GB               | **0.66 GB**    | ↓35%   |
| 推理时间       | 0.38s                 | **0.18s**      | ↓53%   |

**仅 3 次迭代就超过了 RAFT-Stereo 的 32 次迭代**，1 次迭代就能达到 RAFT-Stereo 精度的 69.44%。非零初始化的威力在此体现得淋漓尽致。

当时在 KITTI 2015（280+ 方法）、KITTI 2012 双榜第一。

### 4.4 Selective-Stereo (CVPR 2024 Highlight)

同课题组（HUST）的后续工作，针对迭代方法的一个根本缺陷：**固定感受野无法同时处理高频细节和低频平滑区域**。

#### 两个新模块

**① Selective Recurrent Unit (SRU)**

将单一 GRU 替换为**多分支不同核大小的 GRU**：

- 小核（1×1, 3×3, 1×3）→ 捕获高频边缘和纹理
- 大核（1×5, 1×7, 1×9+）→ 捕获低频平滑区域趋势
- 有效感受野从固定的 3 扩大到 6+ 动态选择范围

**② Contextual Spatial Attention (CSA)**

从上下文特征生成注意力图，自适应融合多频率分支的隐藏状态：

- 高注意力区域 → 高频分支权重高 → 精细边缘
- 低注意力区域 → 低频分支权重高 → 平滑过渡

**性能**：发表时在 KITTI 2012、KITTI 2015、ETH3D、Middlebury 四个榜单全部第一。被 CVPR 2024 选为 Highlight。

---

## 5. Transformer 与全局匹配

### 5.1 为什么需要 Transformer

以上所有方法——无论是 3D CNN 还是迭代法——都是**局部操作**。它们通过堆叠层数来间接获得更大的感受野，但代价是计算量增大和优化困难。

Transformer 的自注意力机制天然具有**全局感受野**——每个像素可以直接与整幅图中的任何像素交互。这对立体匹配中的几个经典难题有根本性的优势：

| 难题       | 局部方法的问题                 | Transformer 的优势           |
| ---------- | ------------------------------ | ---------------------------- |
| 无纹理区域 | 局部窗口内没有区分信息         | 全局注意力可以汇聚远处的线索 |
| 重复纹理   | 局部匹配产生多个候选，无法决断 | 全局上下文提供唯一性约束     |
| 遮挡       | 被遮挡像素找不到对应点         | 全局推理隐式预测遮挡         |
| 大视差     | 需要很大的搜索窗口             | 交叉注意力可在全图搜索       |

### 5.2 STTR (ICCV 2021)

**第一个纯 Transformer 的立体匹配方法**，不依赖 cost volume 和 3D CNN。

架构：

1. **Backbone**：CNN 提取特征 + 位置编码
2. **Alternating Cross-Attention**：左右特征交替做交叉注意力，让每个像素"看到"对方图中所有像素的信息
3. **Optimal Transport**：将匹配建模为最优传输问题（Sinkhorn 算法），得到软匹配矩阵
4. **Raw Disparity Regression**：不依赖代价聚合，直接从注意力权重回归视差

**意义**：证明了 cost volume 不是必需的——Transformer 足以完成匹配任务。

**局限**：计算复杂度 $O(N^2)$（$N$ 为像素数），对高分辨率图像不可行。本身速度慢，但开启了全局匹配的新方向。

### 5.3 S2M2 (ICCV 2025)

将 Transformer 全局匹配推向实用的工作：**纯 Transformer 架构，直接在全图上做匹配，不需要 cost volume、不需要 3D CNN 正则化、不需要深度精化模块**。

核心是 Multi-Resolution Transformer，在不同分辨率上交替做自注意力和交叉注意力，粗粒度的全局匹配引导细粒度的局部精化。

**性能**：在 Middlebury v3 和 ETH3D 上达到新 SOTA，证明了纯全局匹配在精度上已经超越了所有迭代方法。

### 5.4 其他 Transformer 相关工作

| 方法                                    | 年份      | 核心思想                                                                                                                                                     |
| --------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **CroCo** (Weinzaepfel et al.)    | 2022      | Cross-view Completion——预训练时给定部分左图+右图，让网络补全左图的缺失区域。这种预训练方式让网络学会了强大的立体匹配表征，finetune 后在多个下游任务上 SOTA |
| **GMStereo**                      | 2024      | 结合全局匹配和迭代优化的混合架构                                                                                                                             |
| **AIO-Stereo**                    | AAAI 2025 | 从多个 Vision Foundation Model（DINOv2, Depth Anything, SAM 等）中迁移知识到立体匹配                                                                         |
| **CroCo v2** (Weinzaepfel et al.) | 2024      | CroCo 的升级版，预训练数据量更大，在多个 3D 任务（深度估计、光流、位姿估计）上达到 SOTA                                                                      |

---

## 6. 基础模型与零样本泛化

这是 2024-2025 年立体匹配领域最重要的趋势——从"在每个数据集上单独训练/微调"转向"训练一个模型，在任意场景直接使用"。

### 6.1 为什么需要零样本泛化

传统立体匹配方法在训练数据上表现好，但在新场景中**严重退化**：

- Scene Flow 训练的模型在 KITTI 上需要微调
- KITTI 训练的模型在室内 Middlebury 上几乎不可用
- 数据标注成本极高（需要 LiDAR + 精确标定）

这个矛盾推动了对"通用立体匹配基础模型"的追求。

### 6.2 FoundationStereo (NVIDIA, CVPR 2025)

2025 年最重要的立体匹配工作，被提名为 CVPR 2025 最佳论文候选。

#### 核心设计

**① 单目深度先验**

使用 DepthAnythingV2 的 ViT 编码器作为冻结的单目主干网络。DepthAnythingV2 在互联网规模的数据上训练过，拥有丰富的语义和几何先验——它见过室内、室外、自然、城市场景，对各种光照条件都很鲁棒。这些先验被冻结保留。

**② Side-Tuning Adapter (STA)**

问题：ViT 的特征太"语义"，缺少精细的局部纹理信息（区分"这个像素属于椅子"vs"这个像素属于椅子上的这个具体纹理斑点"）。

解决方案：STA 在 ViT 旁路运行一个轻量 CNN（EdgeNeXt），将 CNN 的局部细节特征与 ViT 的语义/几何特征进行自适应融合。类似 LoRA 的思想——冻结大模型，只训练小适配器。

**③ Attentive Hybrid Cost Filtering (AHCF)**

包含两个互补组件：

- **Axial Planar Convolution (APC)**：在视差-空间平面上的轴卷积，高效编码 4D cost volume 的空间-视差交互
- **Disparity Transformer (DT)**：对 4D cost volume 的视差维度做自注意力，捕获长距离视差依赖

**④ 大规模合成数据集 (FSD)**

100 万对路径追踪渲染的立体图像对，材质、光照、几何都达到照片级真实。

#### 性能

| 数据集            | 之前最佳           | FoundationStereo (zero-shot) |
| ----------------- | ------------------ | ---------------------------- |
| Scene Flow EPE    | 0.47 (IGEV-Stereo) | **0.34**               |
| Middlebury BP-2   | 7.5%               | **1.1%**               |
| Middlebury AbsRel | 6.56%              | 显著降低                     |

**不需要任何微调**就在完全陌生的数据集上达到了这个水平。这是立体匹配历史上的一个转折点——"通用立体视觉"从愿景走向现实。

#### Fast-FoundationStereo

通过三个技术将 FoundationStereo 加速 10+ 倍：

1. **知识蒸馏**：小网络学习大网络的输出
2. **Block-wise NAS**：自动搜索最优的 cost filtering 架构
3. **结构化剪枝**：剪除 refinement 模块的冗余通道

140 万张野外立体对 + 自动伪标签训练，实现了实时帧率的零样本立体匹配。

### 6.3 DUSt3R / MASt3R / MUSt3R

DUSt3R 是 2024 年的一个范式级工作，颠覆了"立体匹配需要已知相机内参"的前提。

#### DUSt3R (Wang et al., CVPR 2024)

**核心思想**：不输出视差图，直接为每个像素回归其在 3D 空间中的坐标——称为 **Pointmap**。

```
输入：两张任意来源的图像（不需要内参、不需要校正、不需要知道基线）
输出：两张 3D Pointmap（每个像素 → X,Y,Z 坐标）
```

架构：ViT 编码器 + Transformer 解码器，在解码器中对左右图特征做交叉注意力。

**为什么这是革命性的**：

- 不需要相机内参——网络隐式估计了内参
- 不需要极线校正——任意朝向的相机都可以
- Pointmap 可以直接用于 3D 重建，跳过视差→深度→投影的整条链
- 在非结构化图片对（手持随手拍）上也能工作

#### MASt3R (Leroy et al., 2024)

在 DUSt3R 基础上的改进：增强了匹配能力，使多视图之间的对应更准确，更适合 SLAM/SfM 等任务。

#### MUSt3R (Cabon et al., CVPR 2025)

将 DUSt3R 从两视图扩展到多视图：

- 对称架构处理任意数量的输入视图
- 多层记忆机制实现跨视图信息传递
- 同时支持离线 SfM 和在线 SLAM
- 在视觉里程计和多视图深度上达到 SOTA

### 6.4 Stereo Anywhere (CVPR 2025)

另一个 CVPR 2025 的基础模型工作。核心设计是双分支架构：

- **立体分支**：几何约束驱动的传统立体匹配
- **单目分支**：从 Vision Foundation Model 获取语义先验
- **融合策略**：在几何可信时信任立体分支，在困难区域（遮挡、透明、无纹理）依赖单目分支

### 6.5 MonSter++ (CVPR 2025)

"几何基础模型"——同一个模型同时处理：

- 双目立体匹配
- 多视图立体匹配（MVS）
- 实时立体匹配

在 8 个 benchmark、3 个任务上全部 SOTA。

### 6.6 基础模型小结

| 模型                       | 输入           | 需要内参？       | 需要校正？ | 零样本？ | 实时？      |
| -------------------------- | -------------- | ---------------- | ---------- | -------- | ----------- |
| **FoundationStereo** | 校正后的双目对 | 否（但假设平行） | 是         | ✅       | Fast 版可以 |
| **DUSt3R**           | 任意两张图     | 不需要           | 不需要     | ✅       | ❌          |
| **Stereo Anywhere**  | 校正后的双目对 | 否               | 是         | ✅       | 中速        |
| **MonSter++**        | 校正后的双目对 | 否               | 是         | ✅       | RT 版可以   |

---

## 7. 实时与轻量级方法

### 7.1 HITNet (Google, CVPR 2021)

**核心思想**：不在像素级别而是"倾斜平面"（tile）级别做匹配。

- 将图像划分为可学习的 tile
- 每个 tile 用平面方程 $(a,b,c)$ 参数化（结合视差=深度反比关系）
- 在 tile 级别做匹配和传播
- 推理速度极快，适合手机/AR 设备

### 7.2 其他轻量路线

| 路线          | 代表方法              | 策略                                                   |
| ------------- | --------------------- | ------------------------------------------------------ |
| 轻量 Backbone | MobileGStereo (2025)  | MobileNet 特征提取 + 跳跃成本体积 + 深度可分离 3D 卷积 |
| 神经架构搜索  | LEAStereo (2020)      | 用 NAS 搜索最优的特征提取+匹配架构                     |
| 知识蒸馏      | Fast-FoundationStereo | 大模型教小模型                                         |
| 混合精度/量化 | 多个工作              | FP16/INT8 推理                                         |
| 硬件加速      | SGM FPGA 方案         | 81fps @ 1080p，98% 内存优化                            |

---

## 8. 全景对比与分析

### 8.1 方法演进时间线

```
2002 ─ Scharstein & Szeliski 分类法（四阶段框架）
2008 ─ SGM（Hirschmüller）───────────── 半全局优化
2015 ─ MC-CNN（Žbontar & LeCun）────── 第一个 CNN 匹配代价
2016 ─ DispNet ─────────────────────── 第一个端到端网络
2017 ─ GC-Net ──────────────────────── 4D Cost Volume + 3D CNN 范式确立
2018 ─ PSMNet ──────────────────────── SPP + 堆叠沙漏
2019 ─ GwcNet, GA-Net ─────────────── 组相关、可学习聚合
2021 ─ RAFT-Stereo, STTR ──────────── 迭代范式 + Transformer 范式
2022 ─ CREStereo ──────────────────── 自适应相关 + 级联精化
2023 ─ IGEV-Stereo ─────────────────── 融合卷+迭代
2024 ─ Selective-Stereo, DUSt3R ───── 多频率自适应 / 无参数 3D
2025 ─ FoundationStereo, S2M2, MASt3R, MonSter++ ─ 基础模型、全局匹配
```

### 8.2 三大范式对比

| 维度                   | Cost Volume + 3D CNN       | 迭代优化                                   | 全局匹配 (Transformer)       |
| ---------------------- | -------------------------- | ------------------------------------------ | ---------------------------- |
| **代表方法**     | PSMNet, GwcNet, GA-Net     | RAFT-Stereo, IGEV-Stereo, Selective-Stereo | STTR, S2M2, FoundationStereo |
| **核心操作**     | 3D 卷积                    | ConvGRU 迭代                               | Self/Cross-Attention         |
| **感受野**       | 中等（靠深度堆叠）         | 中等（多级金字塔）                         | 全局（每层都是）             |
| **计算复杂度**   | $O(HWD \cdot C)$         | $O(HW \cdot iter)$                       | $O(N^2)$ → $O(Nk)$ 优化 |
| **内存占用**     | 高（4D volume + 中间激活） | 低（pyramid lookup）                       | 高（注意力矩阵）             |
| **收敛速度**     | 固定（单次前向）           | 可调（时间换精度）                         | 固定（单次前向）             |
| **无纹理区域**   | 中等                       | 弱（缺乏全局几何）                         | **强**（全局注意力）   |
| **精细边缘**     | 中等                       | **强**（迭代精化）                   | 中等                         |
| **泛化能力**     | 弱                         | 中等                                       | **强**（天然零样本）   |
| **硬件要求**     | 高                         | 中                                         | 高                           |
| **最佳适用场景** | 精度优先、场景固定         | **速度精度平衡**、实时系统           | 通用场景、零样本部署         |

### 8.3 关键性能数据（KITTI 2015 D1-all）

| 方法             | D1-all (%)     | 推理时间 (s)   | 内存 (GB)      | 年份 |
| ---------------- | -------------- | -------------- | -------------- | ---- |
| PSMNet           | 2.32           | 0.41           | 4.05           | 2018 |
| GwcNet           | 2.11           | 0.32           | 3.76           | 2019 |
| LEAStereo        | 1.65           | 0.30           | 4.46           | 2020 |
| RAFT-Stereo      | 1.82           | 0.38           | 1.02           | 2021 |
| CREStereo        | 1.54           | 0.88*          | —             | 2022 |
| IGEV-Stereo      | **1.59** | **0.18** | **0.66** | 2023 |
| Selective-Stereo | 1.47           | 0.22           | 0.70           | 2024 |

> \* CREStereo 的推理时间包含其级联+堆叠架构，优化后的 variant 可更快。FoundationStereo 等 2025 模型通常不做 KITTI 单独微调（主打零样本），故未列入此表。

### 8.4 核心权衡总结

```
        精度 ↑
         │
         │     ● FoundationStereo (零样本)
         │         ● S2M2 (全局匹配)
         │    ● Selective-Stereo
         │   ● IGEV-Stereo           ● CREStereo
         │  ● RAFT-Stereo
         │      ● PSMNet
         │           ● SGM ─────── ● Fast-FoundationStereo (实时零样本)
         │      ● DispNet         ● HITNet (实时)
         │
         └──────────────────────────────────────────→ 速度 ↑
```

没有一条曲线压倒所有——选择取决于应用场景：

- **嵌入式/实时**：SGM 或 HITNet 类轻量级方法
- **离线高精度**：IGEV-Stereo / Selective-Stereo
- **通用部署/零样本**：FoundationStereo / Stereo Anywhere
- **无标定场景**：DUSt3R / MASt3R

---

## 9. 未来方向

### 9.1 当前瓶颈

1. **真实场景退化**：即使 FoundationStereo 在真实数据上的 AbsRel 仍然比合成数据差 4 倍以上
2. **不透明物体**：镜子、玻璃、水面——不满足朗伯假设的物体仍然是所有方法的阿喀琉斯之踵
3. **动态场景**：运动物体在双目中引入时间-空间耦合的伪影
4. **极端光照**：暗光、逆光、过曝区域——传感器噪声淹没了匹配信号

### 9.2 有前景的方向

1. **3D 基础模型**：从双目扩展到多视图、视频、甚至任意传感器的统一几何模型（MonSter++ 开了头）
2. **自监督/弱监督**：摆脱对 LiDAR 标注的依赖，用对极几何约束做自监督
3. **神经渲染 + 立体匹配**：用 NeRF/3DGS 的渲染一致性来监督/精化匹配结果
4. **端侧部署**：从 Fast-FoundationStereo 到 ONNX/TensorRT 的全链路优化
5. **事件相机立体匹配**：事件相机的高动态范围 + 微秒级时间分辨率，有望解决极端光照和高速运动问题
6. **多传感器融合**：LiDAR + 双目 + 单目深度先验的深度融合，各取所长
7. **视频立体匹配**（Stereo Any Video 方向）：引入时序一致性，让匹配在时间上也平滑
8. **开放世界理解**：不只是输出视差/深度，而是输出语义 3D（FoundationStereo + SAM + 3D 重建的联合）

### 9.3 我的判断

立体匹配正在经历与 NLP（BERT → GPT）和 2D 视觉（ResNet → ViT → SAM/DINO）类似的演进：

- **2022 之前**："在每个数据集上训练专用模型"
- **2022-2024**："迭代范式和 Transformer 范式竞争"
- **2025 开始**："一个模型解决所有场景"——零样本泛化成为核心追求

FoundationStereo 和 DUSt3R 的成功表明，**大规模数据 + 单目先验 + Transformer 架构**是当前最有效的配方。但也要看到，Fast-FoundationStereo 为了实时性做了大量妥协——"精度-速度-通用性"的不可能三角仍未完全打破。

下一个里程碑可能是：**一个可以在手机实时运行、在任何场景零样本工作、输出度量级 3D 坐标的模型**。目前看，这大约需要 2-3 年。

---

## 参考文献

> 这是一份核心文献列表，聚焦每个方向的开创性和代表性工作。

### 传统方法

- Scharstein, D. & Szeliski, R. "A Taxonomy and Evaluation of Dense Two-Frame Stereo Correspondence Algorithms." *IJCV*, 2002.
- Hirschmüller, H. "Stereo Processing by Semiglobal Matching and Mutual Information." *TPAMI*, 2008.
- Žbontar, J. & LeCun, Y. "Stereo Matching by Training a Convolutional Neural Network to Compare Image Patches." *JMLR*, 2016.

### Cost Volume 范式

- Kendall, A. et al. "End-to-End Learning of Geometry and Context for Deep Stereo Regression." *ICCV*, 2017. (GC-Net)
- Chang, J.-R. & Chen, Y.-S. "Pyramid Stereo Matching Network." *CVPR*, 2018. (PSMNet)
- Guo, X. et al. "Group-Wise Correlation Stereo Network." *CVPR*, 2019. (GwcNet)
- Zhang, F. et al. "GA-Net: Guided Aggregation Net for End-to-End Stereo Matching." *CVPR*, 2019.

### 迭代优化范式

- Lipson, L., Teed, Z. & Deng, J. "RAFT-Stereo: Multilevel Recurrent Field Transforms for Stereo Matching." *3DV*, 2021.
- Li, J. et al. "Practical Stereo Matching via Cascaded Recurrent Network with Adaptive Correlation." *CVPR*, 2022. (CREStereo)
- Xu, G. et al. "Iterative Geometry Encoding Volume for Stereo Matching." *CVPR*, 2023. (IGEV-Stereo)
- Wang, X. et al. "Selective-Stereo: Adaptive Frequency Information Selection for Stereo Matching." *CVPR*, 2024.

### Transformer & 全局匹配

- Li, Z. et al. "Revisiting Stereo Depth Estimation From a Sequence-to-Sequence Perspective with Transformers." *ICCV*, 2021. (STTR)
- Weinzaepfel, P. et al. "CroCo: Self-Supervised Pre-training for 3D Vision Tasks by Cross-View Completion." *NeurIPS*, 2022.
- Min, Y. et al. "S2M2: Scalable Stereo Matching Model for Reliable Depth Estimation." *ICCV*, 2025.

### 基础模型

- Wen, B. et al. "FoundationStereo: Zero-Shot Stereo Matching." *CVPR*, 2025.
- Wang, S. et al. "DUSt3R: Geometric 3D Vision Made Easy." *CVPR*, 2024.
- Leroy, V. et al. "MASt3R: Grounding Image Matching in 3D." *NeurIPS*, 2024.
- Bartolomei, L. et al. "Stereo Anywhere: Robust Zero-Shot Deep Stereo Matching Even Where Either Stereo or Mono Fail." *CVPR*, 2025.
- Yang, L. et al. "Depth Anything V2." *NeurIPS*, 2024.

### 实时 & 轻量

- Tankovich, V. et al. "HITNet: Hierarchical Iterative Tile Refinement Network for Real-time Stereo Matching." *CVPR*, 2021.
- Cheng, X. et al. "Fast-FoundationStereo: Real-Time Zero-Shot Stereo Matching." *arXiv:2512.11130*, 2025.
