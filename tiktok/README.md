# TikTok 视频搬运工作流

## 目标品类
野外探险 / 亚马逊雨林科普

## 目录结构
```
tiktok/
├── tiktok_pipeline.py    # 主脚本（下载+处理）
├── .env.tiktok          # 环境变量（LLM配置等）
├── README.md            # 说明文档
├── videos/              # 下载的视频文件
├── meta/                # 视频元数据（JSON）
└── logs/                # 运行日志
```

## 依赖
- yt-dlp (已装)
- ffmpeg (已装)

## 用法

```bash
cd /mnt/f/fun_project/auto-video/tiktok

# 下载单个视频
python tiktok_pipeline.py "https://www.tiktok.com/@user/video/123456"

# 下载指定用户最新视频
python tiktok_pipeline.py --user @username

# 下载用户最新3条
python tiktok_pipeline.py --user @username --limit 3
```

## 工作流

```
TikTok URL → yt-dlp 下载(1080p + 字幕) → 
提取英文字幕 → LLM 翻译成中文 → 
生成B站标题/简介/标签 → 保存元数据
```

## Phase 2 计划
- [ ] 接入 LLM 翻译字幕
- [ ] 接入 B站 API 自动上传
- [ ] 自动发现热门视频
