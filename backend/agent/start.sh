#!/bin/sh
# Agent 启动脚本
# 用于在 Docker 容器中启动 Agent，捕获所有错误

# 不设置 set -e，以便捕获错误信息
set -u  # 只对未定义变量报错

echo "============================================================" >&2
echo "Agent 启动脚本开始执行..." >&2
echo "当前目录: $(pwd)" >&2
echo "Python 路径: $(which python 2>&1 || echo 'NOT FOUND')" >&2
echo "Python 版本: $(python --version 2>&1 || echo 'ERROR')" >&2
echo "文件是否存在: $(test -f /app/backend/agent/main.py && echo 'YES' || echo 'NO')" >&2
echo "============================================================" >&2

# 检查文件是否存在
if [ ! -f /app/backend/agent/main.py ]; then
    echo "错误: /app/backend/agent/main.py 不存在!" >&2
    echo "检查目录结构:" >&2
    ls -la /app/backend/agent/ >&2 2>&1 || echo "目录 /app/backend/agent/ 不存在" >&2
    ls -la /app/backend/ >&2 2>&1 || echo "目录 /app/backend/ 不存在" >&2
    ls -la /app/ >&2 2>&1 || echo "目录 /app/ 不存在" >&2
    exit 1
fi

# 设置环境变量
export PYTHONUNBUFFERED=1
export PYTHONPATH="/app"

# 启动 Python 程序，捕获所有输出和错误
echo "开始执行 Python 程序..." >&2
exec python -u /app/backend/agent/main.py 2>&1

