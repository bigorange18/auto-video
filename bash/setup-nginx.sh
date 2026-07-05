#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# setup-nginx.sh — 一键配置 Nginx 反向代理 + Let's Encrypt HTTPS
# 端口 80/443 → 本地 127.0.0.1:8787
# 用法: sudo DOMAIN=www.czl.asia ./bash/setup-nginx.sh
# ============================================================

DOMAIN="${DOMAIN:-www.czl.asia}"
DOMAIN_ALIAS="${DOMAIN_ALIAS:-czl.asia}"
BACKEND_PORT="${BACKEND_PORT:-8787}"
CERT_EMAIL="${CERT_EMAIL:-admin@czl.asia}"

require_root() {
  if [[ $EUID -ne 0 ]]; then
    printf 'ERROR: 需要 root 权限，请用 sudo 执行。\n' >&2
    exit 1
  fi
}

install_pkgs() {
  printf '\n===== 检查依赖 =====\n'

  # nginx 已在服务器上，跳过安装
  if command -v nginx &>/dev/null; then
    printf 'Nginx 已安装: %s\n' "$(nginx -v 2>&1)"
  else
    printf 'ERROR: 未找到 nginx，请先手动安装。\n' >&2
    exit 1
  fi

  # certbot（可能已装，也可能需要装 python3-certbot-nginx 插件）
  if command -v certbot &>/dev/null; then
    printf 'Certbot 已安装: %s\n' "$(certbot --version 2>&1 | head -1)"
  fi

  # 确保 certbot nginx 插件存在
  if command -v dnf &>/dev/null; then
    dnf -y install certbot python3-certbot-nginx 2>/dev/null || true
  elif command -v yum &>/dev/null; then
    yum -y install certbot python3-certbot-nginx 2>/dev/null || true
  elif command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq certbot python3-certbot-nginx
  fi

  printf '依赖检查完成。\n'
}

config_nginx() {
  printf '\n===== 配置 Nginx =====\n'

  # 检测配置目录
  local config_file
  if [[ -d /etc/nginx/conf.d ]]; then
    config_file="/etc/nginx/conf.d/${DOMAIN}.conf"
  elif [[ -d /etc/nginx/sites-available ]]; then
    config_file="/etc/nginx/sites-available/${DOMAIN}.conf"
  else
    printf 'ERROR: 找不到 Nginx 配置目录。\n' >&2
    exit 1
  fi

  # 备份原文件
  if [[ -f "$config_file" ]]; then
    local bak="${config_file}.bak.$(date +%s)"
    cp "$config_file" "$bak"
    printf '已备份: %s\n' "$bak"
  fi

  # 写配置（用 tee 避免 heredoc 引号转义问题）
  tee "$config_file" > /dev/null << NGINXEOF
# 大橘博客 — 由 setup-nginx.sh 自动生成

server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    location ~* \.(css|js|png|jpg|svg|ico|woff2?)\$ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}
NGINXEOF

  # sites-available 需要软链
  if [[ -d /etc/nginx/sites-enabled ]]; then
    ln -sf "$config_file" "/etc/nginx/sites-enabled/${DOMAIN}.conf"
  fi

  printf '配置已写入: %s\n' "$config_file"

  printf '\n===== 测试 Nginx 语法 =====\n'
  nginx -t
}

reload_nginx() {
  printf '\n===== 启动 Nginx =====\n'
  systemctl enable --now nginx
  systemctl reload nginx 2>/dev/null || systemctl start nginx
  printf 'Nginx 已启动。\n'
}

setup_certbot() {
  printf '\n===== 申请 SSL 证书 =====\n'

  if certbot --nginx -d "${DOMAIN}" -d "${DOMAIN_ALIAS}" \
    --non-interactive --agree-tos --email "${CERT_EMAIL}" 2>&1; then
    printf '\n证书申请成功！\n'
  else
    printf '\n证书申请失败，请检查:\n'
    printf '  1. 域名 DNS 是否指向当前服务器 (%s)\n' "$DOMAIN"
    printf '  2. 80 端口是否被防火墙阻拦\n'
    printf '\n手动重试:\n'
    printf '  sudo certbot --nginx -d %s -d %s\n' "$DOMAIN" "$DOMAIN_ALIAS"
  fi
}

test_firewall() {
  printf '\n===== 配置防火墙 =====\n'
  if command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    printf 'ufw 已放行 80/443。\n'
  elif command -v firewall-cmd &>/dev/null && firewall-cmd --state 2>/dev/null | grep -q running; then
    firewall-cmd --permanent --add-service=http --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    printf 'firewalld 已放行 http/https。\n'
  else
    printf '未检测到防火墙，跳过。\n'
  fi
}

# ---- main ----
require_root
install_pkgs
config_nginx
reload_nginx
test_firewall
setup_certbot

printf '\n===== 全部就绪 =====\n'
printf '  https://%s/\n' "$DOMAIN"
printf '检查: curl -I https://%s/\n' "$DOMAIN"
