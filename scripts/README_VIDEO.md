# 视频搬运工作流 — 野外探险/亚马逊雨林

## 目标频道

YouTube 频道列表，优先选择独立创作者，降低版权风险：

### 亚马逊雨林/野外探险
- `Amazon Rainforest` 相关纪录片频道
- 独立探险者（Survival, Jungle Exploration 类）
- BBC Earth / Nat Geo（精选片段，注意版权）

### RSS 订阅
YouTube 频道 RSS 格式：
```
https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
```

---

## 工作流

### Phase 1: 手动验证（当前）
1. 手动发现 YouTube 视频
2. yt-dlp 下载
3. 手动上传 B站测试效果

### Phase 2: 半自动化
1. RSS 抓取新视频
2. 自动下载 + 字幕提取
3. LLM 生成标题/简介/标签
4. 手动确认后上传

### Phase 3: 全自动
1. RSS + 评分筛选
2. 自动下载 + 翻译字幕
3. 自动上传 B站

---

## 输出目录
`output/trending_videos/` — 下载的视频文件
`output/video_meta/` — 视频元数据（标题/简介/标签）
