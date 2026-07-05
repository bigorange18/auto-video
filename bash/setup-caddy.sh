#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# setup-caddy.sh — 一键配置 Caddy 反向代理 + HTTPS
# 端口 80/443 → 本地 127.0.0.1:8787
# 用法: sudo ./bash/setup-caddy.sh
# ============================================================

DOMAIN="${DOMAIN:-www.czl.asia}"
BACKEND_PORT="${BACKEND_PORT:-8787}"

require_root() {
  if [[ $EUID -ne 0 ]]; then
    printf 'ERROR: 需要 root 权限，请用 sudo 执行。\n' >&2
    exit 1
  fi
}

install_caddy() {
  if command -v caddy &>/dev/null; then
    printf 'Caddy 已安装: %s\n' "$(caddy version)"
    return
  fi

  printf '正在安装 Caddy...\n'

  if command -v apt-get &>/dev/null; then
    apt-get update -qq
    apt-get install -y -qq debian-keyring debian-archive-keyring apt-transport-https curl
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
  elif command -v dnf &>/dev/null; then
    dnf -y install 'dnf-command(copr)'
    dnf -y copr enable @caddy/caddy
    dnf -y install caddy
  elif command -v yum &>/dev/null; then
    yum -y install yum-plugin-copr
    yum -y copr enable @caddy/caddy
    yum -y install caddy
  else
    printf 'ERROR: 未检测到 apt/dnf/yum，请手动安装 Caddy。\n' >&2
    exit 1
  fi

  printf 'Caddy 安装完成。\n'
}

config_caddy() {
  local caddyfile="/etc/caddy/Caddyfile"

  if [[ -f "$caddyfile" ]]; then
    cp "$caddyfile" "$caddyfile.bak.$(date +%s)"
    printf '已备份原 Caddyfile。\n'
  fi

  cat > "$caddyfile" << EOF
# 大橘博客 — 由 setup-caddy.sh 自动生成

${DOMAIN} {
    reverse_proxy 127.0.0.1:${BACKEND_PORT}

    header {
        X-Forwarded-Proto https
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
        -Server
    }

    encode gzip zstd

    @static {
        file
        path *.css *.js *.png *.jpg *.svg *.ico *.woff *.woff2
    }
    header @static Cache-Control "public, max-age=604800, immutable"
}
EOF

  printf 'Caddyfile 已写入: %s\n' "$caddyfile"
  printf '\n--- Caddyfile ---\n'
  cat "$caddyfile"
  printf '--- 结束 ---\n\n'
}

reload_caddy() {
  if systemctl is-active --quiet caddy; then
    systemctl reload caddy
    printf 'Caddy 已重载配置。\n'
  else
    systemctl enable --now caddy
    printf 'Caddy 已启动并设为开机自启。\n'
  fi
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
install_caddy
config_caddy
reload_caddy
test_firewall

printf '\n===== 完成 =====\n'
printf '通过以下地址访问:\n'
printf '  https://%s/\n' "$DOMAIN"
printf '\n验证 SSL:\n'
printf '  curl -I https://%s/\n' "$DOMAIN"
