"""
数据集：下载 Middlebury / KITTI 测试数据 + 合成数据生成
"""

import os
import urllib.request
import zipfile
import shutil
from pathlib import Path
import cv2
import numpy as np

# ============================================================
# 数据根目录
# ============================================================

DATA_ROOT = Path(__file__).parent.parent / 'data'


def get_data_dir(subdir: str = '') -> Path:
    """获取数据目录，自动创建。"""
    p = DATA_ROOT / subdir
    p.mkdir(parents=True, exist_ok=True)
    return p


# ============================================================
# Middlebury 数据集
# ============================================================

# Middlebury 2001/2003 经典测试集
# 图片来自 vision.middlebury.edu/stereo/data/
MIDDLEBURY_SCENES = {
    'Tsukuba': {
        'url': 'https://vision.middlebury.edu/stereo/data/scenes2001/data/tsukuba/',
        'files': ['imL.png', 'imR.png', 'truedisp.pgm'],
        'size': '384x288',
    },
    'Teddy': {
        'url': 'https://vision.middlebury.edu/stereo/data/scenes2003/newdata/teddy/',
        'files': ['im2.png', 'im6.png', 'disp2.png'],
        'size': '450x375',
    },
    'Cones': {
        'url': 'https://vision.middlebury.edu/stereo/data/scenes2003/newdata/cones/',
        'files': ['im2.png', 'im6.png', 'disp2.png'],
        'size': '450x375',
    },
    'Venus': {
        'url': 'https://vision.middlebury.edu/stereo/data/scenes2001/data/venus/',
        'files': ['imL.png', 'imR.png', 'truedisp.pgm'],
        'size': '434x383',
    },
}


def download_middlebury(scene: str = 'Tsukuba') -> dict:
    """下载 Middlebury 立体数据集。

    Returns:
        dict with paths: left, right, gt_disp (可能为 None)
    """
    if scene not in MIDDLEBURY_SCENES:
        raise ValueError(f"未知场景: {scene}，可选: {list(MIDDLEBURY_SCENES.keys())}")

    info = MIDDLEBURY_SCENES[scene]
    scene_dir = get_data_dir(f'middlebury/{scene.lower()}')

    paths = {}
    for fname in info['files']:
        fpath = scene_dir / fname
        if not fpath.exists():
            url = info['url'] + fname
            print(f"  下载 {url} ...")
            try:
                urllib.request.urlretrieve(url, fpath)
            except Exception as e:
                print(f"  下载失败: {e}")
                continue

        if fpath.exists():
            # 确定文件角色
            if 'L' in fname or 'im2' in fname:
                paths['left'] = str(fpath)
            elif 'R' in fname or 'im6' in fname:
                paths['right'] = str(fpath)
            elif 'disp' in fname or 'truedisp' in fname:
                paths['gt'] = str(fpath)
            else:
                paths.setdefault('others', []).append(str(fpath))

    return paths


def load_stereo_pair(left_path: str, right_path: str) -> tuple[np.ndarray, np.ndarray]:
    """加载左右图像，返回灰度图。"""
    imgL = cv2.imread(left_path, cv2.IMREAD_GRAYSCALE)
    imgR = cv2.imread(right_path, cv2.IMREAD_GRAYSCALE)
    if imgL is None or imgR is None:
        raise FileNotFoundError(f"无法读取图像: {left_path} 或 {right_path}")
    return imgL, imgR


def load_gt_disparity(gt_path: str, scale: float = 1.0) -> np.ndarray:
    """加载地面真实视差图。

    Middlebury GT 通常需要除以 scale factor（如 8.0）
    """
    gt = cv2.imread(gt_path, cv2.IMREAD_UNCHANGED)
    if gt is None:
        raise FileNotFoundError(f"无法读取 GT: {gt_path}")
    gt = gt.astype(np.float32) / scale
    return gt


# ============================================================
# KITTI 数据集
# ============================================================

KITTI_SAMPLES = {
    '000000_10': {
        'base_url': 'https://s3.eu-central-1.amazonaws.com/avg-kitti/data_stereo_flow.zip',
        'is_zip': True,
    },
}


def download_kitti_sample(scene_id: str = '000000_10') -> dict:
    """下载 KITTI 立体样本。"""
    scene_dir = get_data_dir('kitti')
    # KITTI 需要账号，这里提供手动下载指引
    print("KITTI 数据集需要注册账号下载: https://www.cvlibs.net/datasets/kitti/")
    print(f"请将左右图放入: {scene_dir}/")
    return {}


# ============================================================
# 合成测试数据
# ============================================================

def generate_synthetic_pair(size: tuple = (480, 640),
                            pattern: str = 'random_dot',
                            max_disparity: int = 48,
                            noise: float = 0.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """生成带真实视差的合成立体对。

    Args:
        size: (H, W) 图像尺寸
        pattern: 'random_dot' | 'checkerboard' | 'gradient' | 'cones'
        max_disparity: 最大视差
        noise: 高斯噪声标准差

    Returns:
        imgL, imgR, gt_disparity (H, W)
    """
    H, W = size

    # 生成 GT 视差图（每个像素的真实视差）
    y, x = np.mgrid[0:H, 0:W]
    if pattern == 'random_dot':
        # 随机点阵 + 随深度变化的视差
        np.random.seed(42)
        img = np.random.randint(0, 256, (H, W), dtype=np.uint8)
        disp = np.random.randint(4, max_disparity, (H, W)).astype(np.float32)

    elif pattern == 'checkerboard':
        # 棋盘格 + 平面视差
        img = np.zeros((H, W), dtype=np.uint8)
        square = 60
        img[(x // square + y // square) % 2 == 0] = 255
        disp = np.full((H, W), max_disparity // 2, dtype=np.float32)
        disp[:, :W // 2] = max_disparity // 4

    elif pattern == 'cones':
        # 同心圆 + 深度渐变
        cx, cy = W // 2, H // 2
        r = np.sqrt((x - cx) ** 2 + (y - cy) ** 2)
        img = (np.sin(r / 10) * 128 + 128).clip(0, 255).astype(np.uint8)
        disp = (r / r.max() * (max_disparity - 2) + 2).astype(np.float32)

    elif pattern == 'gradient':
        # 条纹 + 横向渐变视差
        img = (np.sin(x / 20) * 128 + 128).clip(0, 255).astype(np.uint8)
        disp = (x.astype(np.float32) / W * (max_disparity - 2) + 2)

    else:
        raise ValueError(f"未知模式: {pattern}")

    # 根据 GT 视差生成右图（平移左图）
    imgR = np.zeros_like(img)
    for d in range(1, max_disparity + 1):
        mask = np.abs(disp - d) < 0.5
        shifted = np.roll(img, d, axis=1)
        shifted[:, :d] = 0
        imgR[mask] = shifted[mask]

    # 处理遮挡
    imgR[imgR == 0] = img[imgR == 0]

    # 加噪声
    if noise > 0:
        imgL_noisy = img.astype(np.float32) + np.random.randn(H, W) * noise
        imgR_noisy = imgR.astype(np.float32) + np.random.randn(H, W) * noise
        imgL = imgL_noisy.clip(0, 255).astype(np.uint8)
        imgR = imgR_noisy.clip(0, 255).astype(np.uint8)

    return imgL, imgR, disp


def save_synthetic_pair(imgL: np.ndarray, imgR: np.ndarray,
                        gt_disp: np.ndarray, name: str = 'synthetic'):
    """保存合成数据到文件。"""
    d = get_data_dir('synthetic')
    cv2.imwrite(str(d / f'{name}_L.png'), imgL)
    cv2.imwrite(str(d / f'{name}_R.png'), imgR)
    # 保存 GT 视差为 16-bit PNG（乘 256 保留亚像素精度）
    disp_16 = (gt_disp * 256).clip(0, 65535).astype(np.uint16)
    cv2.imwrite(str(d / f'{name}_GT.png'), disp_16)
    print(f"  合成数据保存到 {d}/")


# ============================================================
# OpenCV 内置样例
# ============================================================

def load_opencv_sample():
    """加载 OpenCV 内置的立体样本（如果有的话）。

    使用 OpenCV 的 stereo 示例图，通常在 opencv/samples/data 中。
    """
    # OpenCV 示例图路径
    candidates = [
        '/usr/share/opencv4/samples/data/tsukuba_l.png',
        '/usr/local/share/OpenCV/samples/data/tsukuba_l.png',
    ]
    for c in candidates:
        if os.path.exists(c):
            d = Path(c).parent
            left = str(d / 'tsukuba_l.png')
            right = str(d / 'tsukuba_r.png')
            if os.path.exists(left) and os.path.exists(right):
                return {'left': left, 'right': right, 'gt': None}
    return None


# ============================================================
# 便捷函数：获取测试数据
# ============================================================

def get_test_data(source: str = 'synthetic',
                  pattern: str = 'cones',
                  image_size: tuple = (480, 640)) -> dict:
    """统一接口：获取测试数据。

    Args:
        source: 'synthetic' | 'middlebury' | 'kitti' | 'opencv'
        pattern: 合成数据的模式或在 Middlebury 的场景名
        image_size: 合成数据的尺寸

    Returns:
        dict with:
            imgL, imgR: (H, W) uint8 灰度图
            gt_disp: (H, W) 真实视差（可能为 None）
            K: (3,3) 相机内参（可能为 None）
            baseline: 基线距离（米）
            focal: 焦距（像素）
            name: 数据集名称
    """
    if source == 'synthetic':
        imgL, imgR, gt = generate_synthetic_pair(
            size=image_size, pattern=pattern, max_disparity=48, noise=5.0)
        return {
            'imgL': imgL, 'imgR': imgR,
            'gt_disp': gt,
            'K': np.array([[615, 0, image_size[1] // 2],
                           [0, 615, image_size[0] // 2],
                           [0, 0, 1]]),
            'baseline': 0.10, 'focal': 615.0,
            'name': f'synthetic-{pattern}',
        }

    elif source == 'middlebury':
        paths = download_middlebury(pattern)
        imgL, imgR = load_stereo_pair(paths['left'], paths['right'])
        gt = None
        if 'gt' in paths:
            try:
                gt = load_gt_disparity(paths['gt'], scale=8.0)
            except Exception:
                pass
        return {
            'imgL': imgL, 'imgR': imgR,
            'gt_disp': gt,
            'K': None,  # 使用默认 Middlebury 参数
            'baseline': 0.10, 'focal': 615.0,
            'name': f'middlebury-{pattern}',
        }

    elif source == 'opencv':
        sample = load_opencv_sample()
        if sample is None:
            raise RuntimeError("找不到 OpenCV 样本，请手动下载 Middlebury 数据")
        imgL, imgR = load_stereo_pair(sample['left'], sample['right'])
        return {
            'imgL': imgL, 'imgR': imgR,
            'gt_disp': None,
            'K': None, 'baseline': 0.10, 'focal': 615.0,
            'name': 'opencv-tsukuba',
        }

    else:
        raise ValueError(f"未知数据源: {source}")
