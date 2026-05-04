#!/usr/bin/env python3
"""
TikTok 视频搬运工作流 — 野外探险/亚马逊雨林

用法:
  python tiktok_pipeline.py <tiktok_url>          # 下载单个视频
  python tiktok_pipeline.py --user @username      # 下载用户最新视频
  python tiktok_pipeline.py --user @username --limit 3
"""

import subprocess
import json
import sys
import re
from pathlib import Path
from datetime import datetime

# ========================
# 配置
# ========================

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "videos"
META_DIR = BASE_DIR / "meta"
LOG_DIR = BASE_DIR / "logs"

for d in [OUTPUT_DIR, META_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ========================
# 工具函数
# ========================

def run_cmd(cmd: list) -> tuple:
    """执行命令，返回 (returncode, stdout, stderr)"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


def log(msg: str):
    today = datetime.now().strftime("%Y-%m-%d")
    ts = datetime.now().strftime("%H:%M:%S")
    log_file = LOG_DIR / f"{today}.log"
    line = f"[{ts}] {msg}\n"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(line)
    print(f"[{ts}] {msg}")


# ========================
# 下载
# ========================

def download_video(video_url: str) -> dict:
    """使用 yt-dlp 下载单个 TikTok 视频"""
    output_tmpl = str(OUTPUT_DIR / "%(title).80s [%(id)s].%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "srt",
        "--output", output_tmpl,
        "--no-playlist",
        video_url,
    ]

    log(f"下载: {video_url}")
    rc, out, err = run_cmd(cmd)

    if rc == 0:
        # 找刚下载的文件
        mp4s = sorted(OUTPUT_DIR.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        srts = sorted(OUTPUT_DIR.glob("*.srt"), key=lambda p: p.stat().st_mtime, reverse=True)

        return {
            "success": True,
            "video_path": str(mp4s[0]) if mp4s else None,
            "subtitle_path": str(srts[0]) if srts else None,
        }
    else:
        log(f"下载失败: {err[-300:]}")
        return {"success": False, "error": err}


def download_user(username: str, limit: int = 5) -> list:
    """下载指定用户最新 N 条视频"""
    url = f"https://www.tiktok.com/{username}"
    output_tmpl = str(OUTPUT_DIR / "%(title).80s [%(id)s].%(ext)s")

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "--write-sub",
        "--write-auto-sub",
        "--sub-lang", "en",
        "--sub-format", "srt",
        "--output", output_tmpl,
        "--flat-playlist",
        "--playlist-end", str(limit),
        url,
    ]

    log(f"下载 {username} 最新 {limit} 条视频...")
    rc, out, err = run_cmd(cmd)

    if rc == 0:
        mp4s = list(OUTPUT_DIR.glob("*.mp4"))
        log(f"已下载 {len(mp4s)} 条视频")
        return [str(f) for f in mp4s]
    else:
        log(f"下载失败: {err[-300:]}")
        return []


# ========================
# 字幕处理
# ========================

def read_srt(path: str) -> str:
    """读取 SRT 字幕"""
    if not path or not Path(path).exists():
        return ""
    return Path(path).read_text(encoding="utf-8")


# ========================
# B站投稿信息
# ========================

def generate_bili_info(title: str, subtitle: str = "") -> dict:
    """生成 B站投稿信息"""
    clean = re.sub(r'#\S+', '', title).strip()
    tags = ["野外探险", "亚马逊雨林", "自然", "户外", "探险", "原始森林"]
    desc = f"来源: TikTok\n原标题: {title}"
    if subtitle:
        desc += f"\n\n字幕摘要: {subtitle[:200]}"

    return {
        "title": clean,
        "description": desc,
        "tags": tags,
    }


def save_meta(video_id: str, meta: dict):
    meta_file = META_DIR / f"{video_id}.json"
    meta["processed_at"] = datetime.now().isoformat()
    meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"元数据已保存: {meta_file}")


# ========================
# 主流程
# ========================

def process_single(url: str):
    log(f"开始处理: {url}")

    result = download_video(url)
    if not result["success"]:
        log("下载失败，退出")
        return None

    subtitle = ""
    if result.get("subtitle_path"):
        subtitle = read_srt(result["subtitle_path"])
        log(f"字幕已提取 ({len(subtitle)} 字符)")

    video_id = Path(result["video_path"]).stem if result.get("video_path") else "unknown"
    bili_info = generate_bili_info(video_id, subtitle)

    meta = {
        "video_url": url,
        "video_path": result.get("video_path"),
        "subtitle_path": result.get("subtitle_path"),
        "bili_info": bili_info,
        "subtitle_preview": subtitle[:500],
    }
    save_meta(video_id, meta)

    # 打印 B站投稿信息
    print("\n" + "=" * 50)
    print("B站投稿信息:")
    print(f"  标题: {bili_info['title']}")
    print(f"  标签: {', '.join(bili_info['tags'])}")
    print(f"  简介: {bili_info['description'][:100]}...")
    print("=" * 50)

    return meta


def main():
    print("=" * 50)
    print("TikTok 视频搬运 — 野外探险/亚马逊雨林")
    print("=" * 50 + "\n")

    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} <tiktok_url>")
        print(f"  python {sys.argv[0]} --user @username [--limit N]")
        print()
        print("示例:")
        print(f"  python {sys.argv[0]} https://www.tiktok.com/@user/video/123456")
        print(f"  python {sys.argv[0]} --user @amazon_rainforest --limit 3")
        return

    args = sys.argv[1:]

    if "--user" in args:
        idx = args.index("--user")
        if idx + 1 >= len(args):
            print("[ERROR] 请指定用户名")
            return
        username = args[idx + 1]
        if not username.startswith("@"):
            username = "@" + username
        limit = 5
        if "--limit" in args:
            lidx = args.index("--limit")
            if lidx + 1 < len(args):
                limit = int(args[lidx + 1])
        download_user(username, limit)
        return

    # 默认：作为 TikTok URL
    process_single(args[0])


if __name__ == "__main__":
    main()
