# Personal Notes Site

这是一个部署在服务器上的个人网站模板，适合记录：

- 日记
- 开发文档

## 目录

- `docs/diary/`：按日期维护日记
- `docs/dev/`：项目开发文档
- `bin/bootstrap.sh`：初始化环境
- `bin/build.sh`：构建静态站点

## 快速使用

```bash
cd /home/orange/auto-video/site
./bin/bootstrap.sh
source .venv/bin/activate
mkdocs serve -a 0.0.0.0:8008
```

## 生产构建

```bash
cd /home/orange/auto-video/site
./bin/build.sh
```

构建输出在：`/home/orange/auto-video/site/site`

## 部署到 Nginx

参考：`docs/deploy.md`
