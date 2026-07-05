#!/usr/bin/env bash
set -euo pipefail
# ============================================================
# deploy.sh — 大橘博客 (czl-web) 部署脚本
# 用法:
#   ./bash/deploy.sh           # 构建 + 启动/重启
#   ./bash/deploy.sh build     # 仅构建
#   ./bash/deploy.sh start     # 仅启动
#   ./bash/deploy.sh stop      # 停止服务
#   ./bash/deploy.sh restart   # 重启服务
#   ./bash/deploy.sh status    # 查看状态
#   ./bash/deploy.sh logs      # 查看日志
# ============================================================

SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
PROJECT_ROOT="$(readlink -f "$SCRIPT_DIR/..")"
APP_DIR="$PROJECT_ROOT/czl-web"

PM2_NAME="czl-web"
PM2_BIN="${PM2_BIN:-pm2}"

cd "$APP_DIR"

# ---- helpers ----
require_cmd() {
  if ! command -v "$1" &>/dev/null; then
    printf 'ERROR: 缺少命令 %s，请先安装。\n' "$1" >&2
    exit 1
  fi
}

build() {
  printf '\n===== 构建前端 =====\n'
  require_cmd node
  require_cmd npm

  if [[ ! -d node_modules ]]; then
    printf '安装依赖...\n'
    npm install
  fi

  npx vite build
  printf '构建完成。\n'
}

start() {
  printf '\n===== 启动服务 =====\n'
  require_cmd node

  if command -v "$PM2_BIN" &>/dev/null; then
    if "$PM2_BIN" list 2>/dev/null | grep -q "$PM2_NAME"; then
      printf 'pm2 进程已存在，reload...\n'
      "$PM2_BIN" reload "$PM2_NAME" --update-env
    else
      printf 'pm2 启动 %s...\n' "$PM2_NAME"
      "$PM2_BIN" start server/index.js \
        --name "$PM2_NAME" \
        --node-args="--env-file-if-exists=.env"
    fi
    "$PM2_BIN" save
  else
    printf '未检测到 pm2，使用 nohup 启动...\n'
    local pid_file="$PROJECT_ROOT/logs/czl-web.pid"
    mkdir -p "$PROJECT_ROOT/logs"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      printf '服务已在运行中 (pid: %s)\n' "$(cat "$pid_file")"
      return
    fi

    nohup node --env-file-if-exists=.env server/index.js \
      > "$PROJECT_ROOT/logs/czl-web.log" 2>&1 &
    echo $! > "$pid_file"
    printf '已启动 (pid: %s)\n' "$(cat "$pid_file")"
  fi

  sleep 1
  status
}

stop() {
  printf '\n===== 停止服务 =====\n'
  if command -v "$PM2_BIN" &>/dev/null && "$PM2_BIN" list 2>/dev/null | grep -q "$PM2_NAME"; then
    "$PM2_BIN" stop "$PM2_NAME"
    printf '已通过 pm2 停止。\n'
  else
    local pid_file="$PROJECT_ROOT/logs/czl-web.pid"
    if [[ -f "$pid_file" ]]; then
      local pid
      pid="$(cat "$pid_file")"
      if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        printf '已停止 (pid: %s)\n' "$pid"
      fi
      rm -f "$pid_file"
    else
      printf '未找到运行中的进程。\n'
    fi
  fi
}

status() {
  printf '\n===== 服务状态 =====\n'
  if command -v "$PM2_BIN" &>/dev/null && "$PM2_BIN" list 2>/dev/null | grep -q "$PM2_NAME"; then
    "$PM2_BIN" list | grep "$PM2_NAME" || true
  else
    local pid_file="$PROJECT_ROOT/logs/czl-web.pid"
    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
      printf '运行中 (pid: %s, nohup)\n' "$(cat "$pid_file")"
    else
      printf '未运行。\n'
    fi
  fi

  printf '\n端口监听:\n'
  ss -tlnp 2>/dev/null | grep -E '8787|5173|5174' || printf '  (无)\n'
}

logs() {
  if command -v "$PM2_BIN" &>/dev/null && "$PM2_BIN" list 2>/dev/null | grep -q "$PM2_NAME"; then
    "$PM2_BIN" logs "$PM2_NAME" --lines 50
  elif [[ -f "$PROJECT_ROOT/logs/czl-web.log" ]]; then
    tail -f "$PROJECT_ROOT/logs/czl-web.log"
  else
    printf '无日志。\n'
  fi
}

# ---- main ----
case "${1:-deploy}" in
  build)   build ;;
  start)   start ;;
  stop)    stop ;;
  restart) stop; start ;;
  status)  status ;;
  logs)    logs ;;
  deploy)  build; stop; start ;;
  *)
    printf '用法: %s {deploy|build|start|stop|restart|status|logs}\n' "$0"
    exit 1
    ;;
esac
