#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# setup-nginx.sh — 一键配置 Nginx + Let's Encrypt HTTPS
# 适配 阿里云 aa_nginx / 标准 nginx
# 用法: sudo bash setup-nginx.sh
# ============================================================

DOMAIN="${DOMAIN:-www.czl.asia}"
DOMAIN_ALIAS="${DOMAIN_ALIAS:-czl.asia}"
BACKEND_PORT="${BACKEND_PORT:-8787}"
CERT_EMAIL="${CERT_EMAIL:-admin@czl.asia}"

require_root() {
  if [[ $EUID -ne 0 ]]; then
    printf 'ERROR: 需要 root 权限，请用 sudo 执行。\n' >&2
    exit 1
  fi#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# setup-nginx.sh — 一键配置 Nginx + Let's Encrypt HTTPS
# 适配 阿里云 aa_nginx / 标准 nginx
# 用法: sudo bash setup-nginx.sh
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

# ---- 自动检测 nginx 路径 ----
detect_nginx() {
  NGINX_BIN="$(command -v nginx || command -v aa_nginx || true)"
  if [[ -z "$NGINX_BIN" ]]; then
    printf 'ERROR: 未找到 nginx 或 aa_nginx。\n' >&2
    exit 1
  fi
  printf 'Nginx 二进制: %s\n' "$NGINX_BIN"

  # 从编译参数提取实际路径
  NGINX_CONF="$("$NGINX_BIN" -V 2>&1 | grep -oP 'conf-path=\K[^ ]+' || true)"
  NGINX_PREFIX="$("$NGINX_BIN" -V 2>&1 | grep -oP 'prefix=\K[^ ]+' || true)"

  if [[ -n "$NGINX_CONF" ]]; then
    printf '主配置: %s\n' "$NGINX_CONF"
  else
    NGINX_CONF="/etc/nginx/nginx.conf"
  fi

  NGINX_CONF_DIR="$(dirname "$NGINX_CONF")"
  NGINX_SITE_AVAILABLE_DIR="/etc/nginx/sites-available"
  NGINX_SITE_ENABLED_DIR="/etc/nginx/sites-enabled"
  NGINX_BACKUP_DIR="/etc/nginx/backup"

  if grep -qE 'include.*sites-enabled' "$NGINX_CONF" 2>/dev/null; then
    NGINX_VHOST_DIR="$NGINX_SITE_ENABLED_DIR"
  elif grep -qE 'include.*conf\.d' "$NGINX_CONF" 2>/dev/null; then
    NGINX_VHOST_DIR="${NGINX_CONF_DIR}/conf.d"
    NGINX_SITE_AVAILABLE_DIR="$NGINX_VHOST_DIR"
    NGINX_SITE_ENABLED_DIR="$NGINX_VHOST_DIR"
  else
    NGINX_VHOST_DIR="$NGINX_CONF_DIR"
    NGINX_SITE_AVAILABLE_DIR="$NGINX_CONF_DIR"
    NGINX_SITE_ENABLED_DIR="$NGINX_CONF_DIR"
  fi

  mkdir -p "$NGINX_SITE_AVAILABLE_DIR" "$NGINX_SITE_ENABLED_DIR" "$NGINX_BACKUP_DIR"
  printf '虚拟主机目录: available=%s enabled=%s backup=%s\n' "$NGINX_SITE_AVAILABLE_DIR" "$NGINX_SITE_ENABLED_DIR" "$NGINX_BACKUP_DIR"

  # 清理误放到 sites-enabled 目录中的备份配置
  if compgen -G "$NGINX_SITE_ENABLED_DIR/*.bak*" >/dev/null 2>&1; then
    printf '检测到旧备份文件在 sites-enabled 中，正在移到备份目录。\n'
    for f in "$NGINX_SITE_ENABLED_DIR"/*.bak*; do
      mv "$f" "$NGINX_BACKUP_DIR/" 2>/dev/null || true
    done
  fi

  # 如果存在旧 orange-notes 配置，并且与 czl-web 域名冲突，则禁用它
  if [[ -e "$NGINX_SITE_ENABLED_DIR/orange-notes" ]]; then
    if grep -qE 'server_name.*(www\.czl\.asia|czl\.asia)' "$NGINX_SITE_ENABLED_DIR/orange-notes" 2>/dev/null || \
       grep -qE 'server_name.*(www\.czl\.asia|czl\.asia)' "$NGINX_SITE_AVAILABLE_DIR/orange-notes" 2>/dev/null; then
      printf '检测到旧 orange-notes 配置，备份并禁用旧配置以避免冲突。\n'
      if [[ -L "$NGINX_SITE_ENABLED_DIR/orange-notes" ]]; then
        rm -f "$NGINX_SITE_ENABLED_DIR/orange-notes"
      else
        mv "$NGINX_SITE_ENABLED_DIR/orange-notes" "$NGINX_SITE_ENABLED_DIR/orange-notes.disabled.$(date +%s)" 2>/dev/null || true
      fi
    fi
  fi

  # 检测 service 名
  if systemctl list-units --type=service 2>/dev/null | grep -q 'aa_nginx'; then
    NGINX_SVC="aa_nginx"
  elif systemctl list-units --type=service 2>/dev/null | grep -q 'nginx'; then
    NGINX_SVC="nginx"
  else
    NGINX_SVC="nginx"
  fi
  printf 'Nginx 服务: %s\n' "$NGINX_SVC"

  # certbot webroot 目录
  WEBROOT="${WEBROOT:-/var/lib/letsencrypt}"
  mkdir -p "$WEBROOT/.well-known"
}

# ---- 安装 certbot ----
install_certbot() {
  printf '\n===== 检查 Certbot =====\n'
  if command -v certbot &>/dev/null; then
    printf 'Certbot 已安装: %s\n' "$(certbot --version 2>&1 | head -1)"
    return
  fi

  printf '安装 certbot...\n'
  if command -v dnf &>/dev/null; then
    dnf -y install epel-release 2>/dev/null || true
    dnf -y install certbot 2>/dev/null || yum -y install certbot
  elif command -v yum &>/dev/null; then
    yum -y install epel-release 2>/dev/null || true
    yum -y install certbot
  elif command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq certbot
  fi
  printf 'Certbot 安装完成。\n'
}

# ---- 写 nginx HTTP 配置（同时包含 .well-known 路由） ----
write_http_conf() {
  printf '\n===== 写入 HTTP 配置 =====\n'

  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  if [[ -f "$conf_file" ]]; then
    cp "$conf_file" "${NGINX_BACKUP_DIR}/${DOMAIN}.conf.bak.$(date +%s)"
  fi

  cat > "$conf_file" << NGINXEOF
# 大橘博客 — setup-nginx.sh 自动生成

server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    # Let's Encrypt 验证路径
    location ^~ /.well-known/acme-challenge/ {
        root /var/lib/letsencrypt;
        default_type text/plain;
    }

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

    client_max_body_size 10m;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}
NGINXEOF

  printf '已写入: %s\n' "$conf_file"
}

reload_nginx() {
  printf '\n===== 测试并重载 Nginx =====\n'
  if "$NGINX_BIN" -t 2>&1; then
    if systemctl is-active --quiet "$NGINX_SVC" 2>/dev/null; then
      systemctl reload "$NGINX_SVC" 2>/dev/null || "$NGINX_BIN" -s reload
    else
      systemctl enable --now "$NGINX_SVC" 2>/dev/null || "$NGINX_BIN"
    fi
    printf 'Nginx 已重载。\n'
  else
    printf 'ERROR: Nginx 配置测试失败。\n' >&2
    exit 1
  fi
}

# ---- 申请证书（webroot 模式，不依赖 nginx 插件） ----
setup_cert() {
  printf '\n===== 申请 SSL 证书 =====\n'

  if certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
    printf '证书已存在，跳过申请。\n'
    return
  fi

  # 确保 80 端口可达
  printf '验证 80 端口...\n'
  if curl -s -o /dev/null -w '%{http_code}' "http://${DOMAIN}/" 2>/dev/null | grep -qE '^(200|301|302|404)'; then
    printf '80 端口可达。\n'
  else
    printf '警告: 无法访问 http://%s/，检查 DNS 和防火墙。\n' "$DOMAIN"
  fi

  printf '申请证书 (webroot 模式)...\n'
  if certbot certonly --webroot -w /var/lib/letsencrypt \
    -d "$DOMAIN" -d "$DOMAIN_ALIAS" \
    --non-interactive --agree-tos --email "$CERT_EMAIL" 2>&1; then
    printf '证书申请成功！\n'
  else
    printf '\n证书申请失败。请检查:\n'
    printf '  1. DNS: %s 是否指向本机\n' "$DOMAIN"
    printf '  2. 80 端口是否开放\n'
    printf '\n手动重试: sudo certbot certonly --webroot -w /var/lib/letsencrypt -d %s -d %s\n' "$DOMAIN" "$DOMAIN_ALIAS"
  fi
}

# ---- 写 HTTPS 配置 ----
write_https_conf() {
  printf '\n===== 写入 HTTPS 配置 =====\n'

  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  # 只有证书存在才加 HTTPS
  if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    printf '证书目录不存在，仅 HTTP 模式。\n'
    return
  fi

  local listen_line="listen 443 ssl;"

  # 追加 HTTPS server 块
  cat >> "$conf_file" << NGINXEOF

server {
    ${listen_line}
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/${DOMAIN}/chain.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    client_max_body_size 10m;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
}
NGINXEOF

  printf 'HTTPS 配置已追加到: %s\n' "$conf_file"
}

# ---- HTTP → HTTPS 重定向 ----
write_redirect() {
  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    return
  fi

  printf '\n===== 添加 HTTP → HTTPS 重定向 =====\n'

  # 替换 80 server 里的 proxy_pass 为 301 重定向
  sed -i '/listen 80;/,/}/{
    s|proxy_pass http://127.0.0.1:'${BACKEND_PORT}';|return 301 https://$host$request_uri;|;
    s|proxy_http_version .*|# redirect|;
    /proxy_set_header/d;
    /proxy_read_timeout/d;
  }' "$conf_file"

  printf '重定向已添加。\n'
}

firewall() {
  printf '\n===== 防火墙 =====\n'
  if command -v firewall-cmd &>/dev/null && firewall-cmd --state 2>/dev/null | grep -q running; then
    firewall-cmd --permanent --add-service=http --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    printf 'firewalld 已放行 80/443。\n'
  elif command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    printf 'ufw 已放行 80/443。\n'
  fi
}

# ---- cert 自动续期 cron ----
setup_renew_cron() {
  printf '\n===== 设置证书自动续期 =====\n'

  local cron_file="/etc/cron.d/certbot-czl"
  cat > "$cron_file" << CRONEOF
# 大橘博客 SSL 自动续期 (每天凌晨 3:17 + 续期后重载 nginx)
17 3 * * * root certbot renew --quiet --post-hook "systemctl reload ${NGINX_SVC} || nginx -s reload"
CRONEOF

  printf '已写入: %s\n' "$cron_file"
}

# ---- main ----
require_root
detect_nginx
install_certbot
write_http_conf
reload_nginx
firewall
setup_cert
write_https_conf
write_redirect
reload_nginx
setup_renew_cron

printf '\n===== 完成 =====\n'
printf '  https://%s/\n' "$DOMAIN"
printf '  curl -I https://%s/\n' "$DOMAIN"

}

# ---- 自动检测 nginx 路径 ----
detect_nginx() {
  NGINX_BIN="$(command -v nginx || true)"
  if [[ -z "$NGINX_BIN" ]]; then
    printf 'ERROR: 未找到 nginx。\n' >&2
    exit 1
  fi
  printf 'Nginx 二进制: %s\n' "$NGINX_BIN"

  # 从编译参数提取实际路径
  NGINX_CONF="$(nginx -V 2>&1 | grep -oP 'conf-path=\K[^ ]+' || true)"
  NGINX_PREFIX="$(nginx -V 2>&1 | grep -oP 'prefix=\K[^ ]+' || true)"

  if [[ -n "$NGINX_CONF" ]]; then
    printf '主配置: %s\n' "$NGINX_CONF"
  else
    NGINX_CONF="/etc/nginx/nginx.conf"
  fi

  NGINX_CONF_DIR="$(dirname "$NGINX_CONF")"
  NGINX_VHOST_DIR="${NGINX_CONF_DIR}/conf.d"

  if [[ ! -d "$NGINX_VHOST_DIR" ]]; then
    # 检查主配置里有没有 include conf.d
    if grep -q 'include.*conf\.d' "$NGINX_CONF" 2>/dev/null; then
      NGINX_VHOST_DIR="${NGINX_CONF_DIR}/conf.d"
      mkdir -p "$NGINX_VHOST_DIR"
    else
      # 直接写到主配置目录
      NGINX_VHOST_DIR="$NGINX_CONF_DIR"
    fi
  fi

  printf '虚拟主机目录: %s\n' "$NGINX_VHOST_DIR"

  # 检测 service 名
  if systemctl list-units --type=service 2>/dev/null | grep -q 'aa_nginx'; then
    NGINX_SVC="aa_nginx"
  elif systemctl list-units --type=service 2>/dev/null | grep -q 'nginx'; then
    NGINX_SVC="nginx"
  else
    NGINX_SVC="nginx"
  fi
  printf 'Nginx 服务: %s\n' "$NGINX_SVC"

  # certbot webroot 目录
  WEBROOT="${WEBROOT:-/var/lib/letsencrypt}"
  mkdir -p "$WEBROOT/.well-known"
}

# ---- 安装 certbot ----
install_certbot() {
  printf '\n===== 检查 Certbot =====\n'
  if command -v certbot &>/dev/null; then
    printf 'Certbot 已安装: %s\n' "$(certbot --version 2>&1 | head -1)"
    return
  fi

  printf '安装 certbot...\n'
  if command -v dnf &>/dev/null; then
    dnf -y install epel-release 2>/dev/null || true
    dnf -y install certbot 2>/dev/null || yum -y install certbot
  elif command -v yum &>/dev/null; then
    yum -y install epel-release 2>/dev/null || true
    yum -y install certbot
  elif command -v apt-get &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq certbot
  fi
  printf 'Certbot 安装完成。\n'
}

# ---- 写 nginx HTTP 配置（同时包含 .well-known 路由） ----
write_http_conf() {
  printf '\n===== 写入 HTTP 配置 =====\n'

  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  if [[ -f "$conf_file" ]]; then
    cp "$conf_file" "${conf_file}.bak.$(date +%s)"
  fi

  cat > "$conf_file" << NGINXEOF
# 大橘博客 — setup-nginx.sh 自动生成

server {
    listen 80;
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    # Let's Encrypt 验证路径
    location ^~ /.well-known/acme-challenge/ {
        root /var/lib/letsencrypt;
        default_type text/plain;
    }

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

    client_max_body_size 10m;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
}
NGINXEOF

  printf '已写入: %s\n' "$conf_file"
}

reload_nginx() {
  printf '\n===== 测试并重载 Nginx =====\n'
  if nginx -t 2>&1; then
    if systemctl is-active --quiet "$NGINX_SVC" 2>/dev/null; then
      systemctl reload "$NGINX_SVC" 2>/dev/null || nginx -s reload
    else
      systemctl enable --now "$NGINX_SVC" 2>/dev/null || nginx
    fi
    printf 'Nginx 已重载。\n'
  else
    printf 'ERROR: Nginx 配置测试失败。\n' >&2
    exit 1
  fi
}

# ---- 申请证书（webroot 模式，不依赖 nginx 插件） ----
setup_cert() {
  printf '\n===== 申请 SSL 证书 =====\n'

  if certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
    printf '证书已存在，跳过申请。\n'
    return
  fi

  # 确保 80 端口可达
  printf '验证 80 端口...\n'
  if curl -s -o /dev/null -w '%{http_code}' "http://${DOMAIN}/" 2>/dev/null | grep -qE '^(200|301|302|404)'; then
    printf '80 端口可达。\n'
  else
    printf '警告: 无法访问 http://%s/，检查 DNS 和防火墙。\n' "$DOMAIN"
  fi

  printf '申请证书 (webroot 模式)...\n'
  if certbot certonly --webroot -w /var/lib/letsencrypt \
    -d "$DOMAIN" -d "$DOMAIN_ALIAS" \
    --non-interactive --agree-tos --email "$CERT_EMAIL" 2>&1; then
    printf '证书申请成功！\n'
  else
    printf '\n证书申请失败。请检查:\n'
    printf '  1. DNS: %s 是否指向本机\n' "$DOMAIN"
    printf '  2. 80 端口是否开放\n'
    printf '\n手动重试: sudo certbot certonly --webroot -w /var/lib/letsencrypt -d %s -d %s\n' "$DOMAIN" "$DOMAIN_ALIAS"
  fi
}

# ---- 写 HTTPS 配置 ----
write_https_conf() {
  printf '\n===== 写入 HTTPS 配置 =====\n'

  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  # 只有证书存在才加 HTTPS
  if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    printf '证书目录不存在，仅 HTTP 模式。\n'
    return
  fi

  # 追加 HTTPS server 块
  cat >> "$conf_file" << NGINXEOF

server {
    listen 443 ssl http2;
    server_name ${DOMAIN} ${DOMAIN_ALIAS};

    ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;
    ssl_trusted_certificate /etc/letsencrypt/live/${DOMAIN}/chain.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    location / {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto https;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }

    client_max_body_size 10m;
    add_header X-Frame-Options DENY always;
    add_header X-Content-Type-Options nosniff always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains" always;
}
NGINXEOF

  printf 'HTTPS 配置已追加到: %s\n' "$conf_file"
}

# ---- HTTP → HTTPS 重定向 ----
write_redirect() {
  local conf_file="${NGINX_VHOST_DIR}/${DOMAIN}.conf"

  if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
    return
  fi

  printf '\n===== 添加 HTTP → HTTPS 重定向 =====\n'

  # 替换 80 server 里的 proxy_pass 为 301 重定向
  sed -i '/listen 80;/,/}/{
    s|proxy_pass http://127.0.0.1:'${BACKEND_PORT}';|return 301 https://$host$request_uri;|;
    s|proxy_http_version .*|# redirect|;
    /proxy_set_header/d;
    /proxy_read_timeout/d;
  }' "$conf_file"

  printf '重定向已添加。\n'
}

firewall() {
  printf '\n===== 防火墙 =====\n'
  if command -v firewall-cmd &>/dev/null && firewall-cmd --state 2>/dev/null | grep -q running; then
    firewall-cmd --permanent --add-service=http --add-service=https 2>/dev/null || true
    firewall-cmd --reload 2>/dev/null || true
    printf 'firewalld 已放行 80/443。\n'
  elif command -v ufw &>/dev/null && ufw status 2>/dev/null | grep -q "Status: active"; then
    ufw allow 80/tcp
    ufw allow 443/tcp
    printf 'ufw 已放行 80/443。\n'
  fi
}

# ---- cert 自动续期 cron ----
setup_renew_cron() {
  printf '\n===== 设置证书自动续期 =====\n'

  local cron_file="/etc/cron.d/certbot-czl"
  cat > "$cron_file" << CRONEOF
# 大橘博客 SSL 自动续期 (每天凌晨 3:17 + 续期后重载 nginx)
17 3 * * * root certbot renew --quiet --post-hook "systemctl reload ${NGINX_SVC} || nginx -s reload"
CRONEOF

  printf '已写入: %s\n' "$cron_file"
}

# ---- main ----
require_root
detect_nginx
install_certbot
write_http_conf
reload_nginx
firewall
setup_cert
write_https_conf
write_redirect
reload_nginx
setup_renew_cron

printf '\n===== 完成 =====\n'
printf '  https://%s/\n' "$DOMAIN"
printf '  curl -I https://%s/\n' "$DOMAIN"
