#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# setup-nginx.sh — 一键配置 Nginx 反向代理 + Let's Encrypt HTTPS
# 端口 80/443 → 本地 127.0.0.1:8787
# 用法: sudo ./bash/setup-nginx.sh
# ============================================================

DOMAIN="${DOMAIN:-www.czl.asia}"
DOMAIN_ALIAS="${DOMAIN_ALIAS:-czl.asia}"
BACKEND_PORT="${BACKEND_PORT:-8787}"

require_root() {
  if [[ $EUID -ne 0 ]]; then
    printf 'ERROR: 需要 root 权限，请用 sudo 执行。\n' >&2
    exit 1
  fi
}

install_pkgs() {
  if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq nginx certbot python3-certbot-nginx
  elif command -v dnf &>/dev/null; then
    dnf -y install nginx certbot python3-certbot-nginx
  elif command -v yum &>/dev/null; then
    yum -y install epel-release
    yum -y install nginx certbot python3-certbot-nginx
  else
    printf 'ERROR: 未检测到 apt/dnf/yum。\n' >&2
    exit 1
  fi
  printf 'Nginx + Certbot 安装完成。\n'
}

config_nginx() {
  local config_file="/etc/nginx/sites-available/${DOMAIN}.conf"
  local link_file="/etc/nginx/sites-enabled/${DOMAIN}.conf"

  # 兼容非 sites-enabled 的发行版
  if [[ ! -d "/etc/nginx/sites-available" ]]; then
    config_file="/etc/nginx/conf.d/${DOMAIN}.conf"
    link_file=""
  fi

  cat > "$config_file" << EOF
# 大橘博客 — 由 setup-nginx.sh 自动生成

server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    # 大文件上传限制 (可选)
    client_max_body_size 10m;

    # 代理头
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

    # 静态资源缓存
    location ~* \.(css|js|png|jpg|svg|ico|woff2?)$ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        expires 7d;
        add_header Cache-Control "public, immutable";
        add_header X-Content-Type-Options nosniff;
    }

    # 安全头
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}

# HTTPS 由 certbot 后续自动添加在此
EOF

  if [[ -n "$link_file" ]]; then
    ln -sf "$config_file" "$link_file"
  fi

  printf 'Nginx 配置已写入: %s\n' "$config_file"

  # 测试语法
  nginx -t
}

reload_nginx() {
  systemctl enable --now nginx
  systemctl reload nginx
  printf 'Nginx 已启动并设为开机自启。\n'
}

setup_certbot() {
  printf '\n正在申请 Let's Encrypt SSL 证书...\n'
  certbot --nginx -d "${DOMAIN}" -d "${DOMAIN_ALIAS}" --non-interactive --agree-tos --email "${EMAIL:-admin@${DOMAIN_ALIAS}}"
  printf '\n证书申请完成。\n'
}

test_firewall() {
  if command -v ufw &>/dev/null; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    printf '防火墙已放行 80/443 (ufw)。\n'
  elif command -v firewall-cmd &>/dev/null; then
    firewall-cmd --permanent --add-service=http --add-service=https
    firewall-cmd --reload
    printf '防火墙已放行 http/https (firewalld)。\n'
  fi
}

# ---- main ----
require_root
install_pkgs
config_nginx
reload_nginx
test_firewall

printf '\n===== Nginx 已就绪 (HTTP) =====\n'
printf '访问: http://%s/\n' "$DOMAIN"
printf '\n执行以下命令启用 HTTPS:\n'
printf '  sudo certbot --nginx -d %s -d %s\n' "$DOMAIN" "$DOMAIN_ALIAS"
