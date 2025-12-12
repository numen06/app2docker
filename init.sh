#!/bin/bash
# init.sh —— 纯 Bash 版（无需 Python）

set -e  # 出错立即退出

VENV_DIR="./venv"
REQ_FILE="requirements.txt"

echo "📦 正在准备虚拟环境..."

if [[ ! -d "$VENV_DIR" ]]; then
  echo "➡️  创建虚拟环境..."
  python3 -m venv "$VENV_DIR"
else
  echo "✅ 虚拟环境已存在：$VENV_DIR"
fi

echo "➡️  升级 pip..."
"$VENV_DIR/bin/pip" install -U pip

if [[ -f "$REQ_FILE" ]]; then
  echo "➡️  安装 requirements.txt..."
  "$VENV_DIR/bin/pip" install -r "$REQ_FILE"
  echo "🎉 初始化完成！"
else
  echo "⚠️  $REQ_FILE 不存在，跳过安装依赖。"
fi