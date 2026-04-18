# 部署指南

本方案采用：

- MkDocs 生成静态站点
- Nginx 对外提供访问
- 可选：Basic Auth 保护私密日记

## 1. 初始化环境

```bash
cd /home/orange/auto-video/site
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. 本地构建

```bash
cd /home/orange/auto-video/site
source .venv/bin/activate
mkdocs build
```

构建产物目录：`site/site`

## 3. Nginx 配置

先安装 Nginx（Alibaba Cloud Linux 3）：

```bash
sudo dnf install -y epel-release
sudo dnf install -y aa_nginx
sudo useradd -r -s /sbin/nologin -M nginx || true
sudo ln -sf /usr/sbin/aa_nginx /usr/sbin/nginx
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
```

`aa_nginx` 默认配置不读取 `sites-enabled`，先在 `/etc/aa_nginx/aa_nginx.conf` 的 `http {}` 内增加：

```nginx
include /etc/nginx/sites-enabled/*;
```

示例：`/etc/nginx/sites-available/orange-notes`

```nginx
server {
    listen 80;
    server_name czl.asia;

    root /home/orange/auto-video/site/site;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # 可选：开启基础认证保护整站
    # auth_basic "Private";
    # auth_basic_user_file /etc/nginx/.htpasswd;
}
```

启用配置：

```bash
sudo ln -sfn /etc/nginx/sites-available/orange-notes /etc/nginx/sites-enabled/orange-notes
sudo nginx -t
sudo systemctl reload nginx
```

## 4. 配置 HTTPS（推荐）

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo certbot --nginx -d czl.asia
```

## 5. 更新网站内容

每次新增日记或文档后执行：

```bash
cd /home/orange/auto-video/site
source .venv/bin/activate
mkdocs build
sudo systemctl reload nginx
```
