#!/usr/bin/env python3
"""
视频搬运工作流 — 野外探险/亚马逊雨林
Phase 1: YouTube 视频发现 + 下载 + 字幕提取
"""

import subprocess
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime

# 配置
CHANNELS = [
    # 格式: (频道URL或ID, 频道名)
    ("https://www.youtube.com/@PrimitiveTechnology", "Primitive Technology"),
    ("https://www.youtube.com/@EaterFilms", "Eater Films"),
    ("https://www.youtube.com/@TAOutdoors1", "TA Outdoors"),
    # 可以继续添加...
]

# RSS 订阅地址（YouTube 频道 RSS）
# https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID

OUTPUT_DIR = Path("/mnt/f/fun_project/auto-video/output/trending_videos")
META_DIR = Path("/mnt/f/fun_project/auto-video/output/video_meta")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)


def discover_from_rss(channel_id: str, channel_name: str) -> list:
    """从 YouTube RSS 获取频道最新视频"""
    import urllib.request
    import xml.etree.ElementTree as ET
    
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        req = urllib.request.Request(rss_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            xml_data = resp.read()
        
        root = ET.fromstring(xml_data)
        videos = []
        
        for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            video_id = entry.find("{http://www.w3.org/2005/Atom}id").text.split(":")[-1]
            published = entry.find("{http://www.w3.org/2005/Atom}published").text
            link = entry.find("{http://www.w3.org/2005/Atom}link").get("href")
            
            videos.append({
                "title": title,
                "video_id": video_id,
                "url": link,
                "published": published,
                "channel": channel_name,
            })
        
        return videos
    except Exception as e:
        print(f"[ERROR] RSS 抓取失败 {channel_name}: {e}")
        return []


def download_video(video_url: str, output_dir: Path) -> dict:
    """使用 yt-dlp 下载视频"""
    output_template = str(output_dir / "%(title)s [%(id)s].%(ext)s")
    
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "--merge-output-format", "mp4",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "srt",
        "--output", output_template,
        "--no-playlist",
        video_url,
    ]
    
    print(f"[INFO] 下载: {video_url}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"[OK] 下载成功")
        return {"success": True, "output": output_dir}
    else:
        print(f"[ERROR] 下载失败: {result.stderr}")
        return {"success": False, "error": result.stderr}


def extract_subtitles(video_path: str) -> str:
    """从视频中提取字幕（如果有的话）"""
    srt_files = list(Path(video_path).parent.glob("*.srt"))
    if srt_files:
        return srt_files[0].read_text(encoding="utf-8")
    return ""


def generate_bili_info(title: str, description: str, llm_enabled: bool = False) -> dict:
    """生成B站投稿信息"""
    # 原始标题
    original_title = title
    
    # B站标题风格：更口语化、带情绪
    if llm_enabled:
        # 后续接入 LLM 生成
        pass
    
    # 默认规则生成
    tags = ["野外探险", "亚马逊雨林", "自然", "纪录片", "户外"]
    
    return {
        "title": original_title,
        "description": description,
        "tags": tags,
    }


def save_meta(video_id: str, meta: dict):
    """保存视频元数据"""
    meta_file = META_DIR / f"{video_id}.json"
    meta["processed_at"] = datetime.now().isoformat()
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"[INFO] 元数据已保存: {meta_file}")


def main():
    """主流程：发现 → 下载 → 生成B站信息"""
    print("=" * 60)
    print("视频搬运工作流 — 野外探险/亚马逊雨林")
    print("=" * 60)
    
    # 这里先演示流程，实际需要配置 channel_id
    # 对于 Phase 1，建议手动输入 YouTube URL 来下载
    
    if len(sys.argv) > 1:
        # 传入 YouTube URL 直接下载
        url = sys.argv[1]
        download_video(url, OUTPUT_DIR)
    else:
        print("用法:")
        print(f"  python {sys.argv[0]} <youtube_url>    # 下载指定视频")
        print(f"  python {sys.argv[0]} --discover       # 从 RSS 发现新视频")
        print()
        print("示例:")
        print(f"  python {sys.argv[0]} https://www.youtube.com/watch?v=xxxxx")


if __name__ == "__main__":
    main()
