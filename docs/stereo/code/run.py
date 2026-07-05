#!/usr/bin/env python3
"""
立体匹配复现脚本 — 从 SAD 到点云的一键运行

用法:
    # 合成数据 + SAD
    python run.py --source synthetic --pattern cones --method sad

    # 合成数据 + Census
    python run.py --source synthetic --pattern random_dot --method census

    # 合成数据 + 全部方法对比
    python run.py --source synthetic --compare

    # 下载 Middlebury Tsukuba 并运行
    python run.py --source middlebury --pattern Tsukuba --method sad

    # 生成点云
    python run.py --source synthetic --pattern gradient --method census --pointcloud

用法:
    # 合成数据 + SAD
    python -m docs.stereo.code.run --source synthetic --pattern cones --method sad

    # 合成数据 + Census
    python -m docs.stereo.code.run --source synthetic --pattern random_dot --method census

    # 合成数据 + 全部方法对比
    python -m docs.stereo.code.run --source synthetic --compare

    # 下载 Middlebury Tsukuba 并运行
    python -m docs.stereo.code.run --source middlebury --pattern Tsukuba --method sad

    # 生成点云
    python -m docs.stereo.code.run --source synthetic --pattern gradient --method census --pointcloud
"""

from __future__ import annotations

import sys
import argparse
import time
from pathlib import Path

import numpy as np
import cv2
import matplotlib.pyplot as plt

# 允许直接运行（从 docs/stereo/code/run.py 向上 4 级到项目根）
_project_root = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_project_root))

from docs.stereo.code import costs
from docs.stereo.code.matching import stereo_match, stereo_sgbm
from docs.stereo.code.pointcloud import disparity_to_pointcloud, disparity_to_depth, \
    remove_statistical_outliers, downsample
from docs.stereo.code.visualize import (plot_stereo_result, plot_comparison,
                                         plot_cost_slice, plot_pointcloud_projection,
                                         visualize_pointcloud, save_pointcloud)
from docs.stereo.code.datasets import get_test_data, DATA_ROOT


def main():
    parser = argparse.ArgumentParser(
        description='双目立体匹配复现 — SAD/SSD/NCC/Census/SGBM')
    parser.add_argument('--source', default='synthetic',
                        choices=['synthetic', 'middlebury', 'opencv'],
                        help='数据源')
    parser.add_argument('--pattern', default='cones',
                        choices=['cones', 'random_dot', 'checkerboard', 'gradient',
                                 'Tsukuba', 'Teddy', 'Cones', 'Venus'],
                        help='数据模式/场景')
    parser.add_argument('--method', default='sad',
                        choices=['sad', 'ssd', 'ncc', 'census', 'ad-census', 'sgbm'],
                        help='匹配方法')
    parser.add_argument('--max-disparity', type=int, default=64,
                        help='最大视差搜索范围')
    parser.add_argument('--window-size', type=int, default=7,
                        help='匹配窗口大小')
    parser.add_argument('--census-win', type=int, default=7,
                        help='Census 变换窗口大小')
    parser.add_argument('--compare', action='store_true',
                        help='对比所有方法')
    parser.add_argument('--pointcloud', action='store_true',
                        help='生成并显示点云')
    parser.add_argument('--no-lr-check', action='store_true',
                        help='跳过左右一致性检查')
    parser.add_argument('--no-subpixel', action='store_true',
                        help='跳过子像素细化')
    parser.add_argument('--save', action='store_true',
                        help='保存结果图片')
    parser.add_argument('--output', default=None,
                        help='输出目录（默认 docs/stereo/output）')

    args = parser.parse_args()

    # 输出目录
    output_dir = Path(args.output) if args.output else \
        Path(__file__).parent.parent / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)

    # ============================================================
    # 1. 加载数据
    # ============================================================
    print("=" * 60)
    print("双目立体匹配复现")
    print("=" * 60)
    print(f"\n[数据] 加载 {args.source}/{args.pattern} ...")

    data = get_test_data(source=args.source, pattern=args.pattern)
    imgL, imgR = data['imgL'], data['imgR']
    gt_disp = data.get('gt_disp')

    print(f"  图像尺寸: {imgL.shape}")
    print(f"  真实视差: {'有' if gt_disp is not None else '无'}")

    # ============================================================
    # 2. 运行匹配
    # ============================================================
    if args.compare:
        # 对比所有方法
        methods = ['sad', 'ssd', 'ncc', 'census', 'sgbm']
        results = {}
        times = {}

        for method in methods:
            print(f"\n{'=' * 40}")
            t0 = time.time()
            if method == 'sgbm':
                results[method] = stereo_sgbm(imgL, imgR,
                                              max_disparity=args.max_disparity,
                                              block_size=args.window_size)
            else:
                results[method] = stereo_match(
                    imgL, imgR,
                    method=method,
                    max_disparity=args.max_disparity,
                    window_size=args.window_size,
                    census_win=args.census_win,
                    do_lr_check=not args.no_lr_check,
                    do_subpixel=not args.no_subpixel,
                )
            times[method] = time.time() - t0
            print(f"  耗时: {times[method]:.2f}s")

        # 打印统计
        print(f"\n{'=' * 40}")
        print(f"{'方法':<12} {'耗时':<10} {'有效像素':<12} {'均值视差':<10}")
        print("-" * 44)
        for method, result in results.items():
            disp = result['disparity']
            valid = disp > 0
            print(f"{method:<12} {times[method]:<8.2f}s "
                  f"{valid.sum() / valid.size * 100:<11.1f}% "
                  f"{disp[valid].mean():<10.2f}")

        # 可视化比对
        fig = plot_comparison(results, imgL, imgR,
                              save_path=str(output_dir / 'comparison.png')
                              if args.save else None)
        if not args.save:
            plt.show()

    else:
        # 单一方法
        print(f"\n[匹配] 方法={args.method}...")
        t0 = time.time()

        if args.method == 'sgbm':
            result = stereo_sgbm(imgL, imgR,
                                 max_disparity=args.max_disparity,
                                 block_size=args.window_size)
        else:
            result = stereo_match(
                imgL, imgR,
                method=args.method,
                max_disparity=args.max_disparity,
                window_size=args.window_size,
                census_win=args.census_win,
                do_lr_check=not args.no_lr_check,
                do_subpixel=not args.no_subpixel,
            )

        elapsed = time.time() - t0
        disp = result['disparity']
        valid = disp > 0
        print(f"  耗时: {elapsed:.2f}s")
        print(f"  有效像素: {valid.sum() / valid.size * 100:.1f}%")
        print(f"  视差范围: [{disp[valid].min():.1f}, {disp[valid].max():.1f}]")

        # 如果有 GT，计算误差
        if gt_disp is not None:
            mask = (disp > 0) & (gt_disp > 0)
            if mask.any():
                epe = np.abs(disp[mask] - gt_disp[mask]).mean()
                bad1 = (np.abs(disp[mask] - gt_disp[mask]) > 1.0).mean() * 100
                print(f"  EPE (平均误差): {epe:.3f} px")
                print(f"  Bad 1.0: {bad1:.2f}%")

        # 可视化
        fig = plot_stereo_result(
            imgL, imgR, result,
            save_path=str(output_dir / f'{args.method}.png')
            if args.save else None)
        if not args.save:
            plt.show()

        # 代价曲线（检查匹配质量）
        if 'cost_volume' in result:
            fig2, ax = plt.subplots(1, 2, figsize=(10, 4))
            plot_cost_slice(result['cost_volume'], ax=ax[0])
            # 再选一个边缘点
            plot_cost_slice(result['cost_volume'],
                            y=imgL.shape[0] // 2,
                            x=imgL.shape[1] // 4,
                            ax=ax[1])
            plt.tight_layout()
            if args.save:
                fig2.savefig(str(output_dir / f'{args.method}_cost.png'))
            else:
                plt.show()

    # ============================================================
    # 3. 生成点云
    # ============================================================
    if args.pointcloud:
        print(f"\n[点云] 生成中...")

        if args.compare:
            # 取最后一个结果（或让用户选择）
            method = methods[-1]
            disp_for_pc = results[method]['disparity']
        else:
            disp_for_pc = result['disparity']

        focal = data.get('focal', 615.0)
        baseline = data.get('baseline', 0.10)
        cx = data.get('K', None)
        if cx is not None:
            cx = cx[0, 2]
        else:
            cx = imgL.shape[1] // 2
        cy = imgL.shape[1] // 2 if data.get('K') is None else data['K'][1, 2]

        pcd = disparity_to_pointcloud(
            disp_for_pc, image=imgL,
            focal_length=focal, baseline=baseline,
            cx=cx, cy=cy)

        print(f"  原始点数: {len(pcd.points)}")

        # 降采样 + 去噪
        pcd = downsample(pcd, voxel_size=0.005)
        pcd = remove_statistical_outliers(
            pcd, nb_neighbors=20, std_ratio=2.0)
        print(f"  过滤后点数: {len(pcd.points)}")

        # 保存
        save_pointcloud(pcd, str(output_dir / 'pointcloud.ply'))

        # 三视图
        fig_pc = plot_pointcloud_projection(
            pcd, save_path=str(output_dir / 'pointcloud_projections.png')
            if args.save else None)

        # 交互式 3D
        print("\n  启动交互式 3D 可视化（按 Q 关闭）...")
        visualize_pointcloud(pcd)

    print(f"\n{'=' * 60}")
    print(f"完成！输出目录: {output_dir}")
    print("=" * 60)


if __name__ == '__main__':
    main()
