# Agent Dockerfile - 独立的 Agent 镜像构建文件
# 基于主程序的 Dockerfile，但只包含 Python 后端部分，入口程序改为 backend/agent/main.py

# ============ Python 后端 ============
# 使用阿里云 Python 镜像加速下载
FROM registry.cn-shanghai.aliyuncs.com/51jbm/docker:27.2.0-cli

# ✅ 替换 apk 源为阿里云镜像（关键！提速 5–10×）
RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

RUN apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    curl \
    jq \
    git \
    make \
    gcc \
    musl-dev \
    linux-headers \
    docker-compose

# ✅ 创建软链接 python → python3（适配多数脚本）
RUN ln -sf python3 /usr/bin/python && \
    ln -sf pip3 /usr/bin/pip

# ✅ 【关键修复】用户级升级 pip + 当前 shell 立即生效
# （注意：用 `sh -c` 显式执行，避免 shell 解析歧义）
# 使用国内镜像源并增加超时时间，避免网络超时
RUN python -m pip install --upgrade --break-system-packages \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --timeout 300 \
    --retries 5 \
    pip

# ✅ 验证 Python 环境
RUN echo "✅ Python version:" && python --version && \
    echo "✅ pip version:" && pip --version && \
    echo "✅ docker version:" && docker --version && \
    echo "✅ docker-compose version:" && docker-compose --version

#设置时区
# 1. 安装 tzdata（Alpine 官方时区数据包）
RUN apk add --no-cache tzdata

# 2. 设置默认时区（影响 date 命令 & 大多数应用）
ENV TZ=Asia/Shanghai

# 3. （可选）让 `date` 命令显示正确本地时间（软链接 localtime）
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo "$TZ" > /etc/timezone

WORKDIR /app

# 复制 Python 依赖文件
COPY requirements.txt .

# 安装 Python 依赖
# ✅ 创建虚拟环境并激活安装
RUN python -m venv .venv && \
    .venv/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    .venv/bin/pip config set global.timeout 300 && \
    .venv/bin/pip config set global.retries 5 && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt && \
    .venv/bin/pip install --no-cache-dir psutil websockets

# ✅ 设置 PATH，让 .venv/bin 优先（等效于 source .venv/bin/activate）
ENV PATH="/app/.venv/bin:$PATH"

# ✅ 设置 Python 无缓冲输出，确保日志立即输出到控制台
ENV PYTHONUNBUFFERED=1
# ✅ 设置 PYTHONPATH，确保可以正确导入 backend 模块
ENV PYTHONPATH="/app"

# 复制后端代码（Agent 需要访问 backend 模块）
COPY backend/ ./backend/

# 说明：
# - Agent 需要访问 Docker daemon（通过 /var/run/docker.sock 卷映射）
# - Agent 需要访问主机信息（通过 /proc 和 /sys 卷映射）
# 
# 运行容器：
# docker run -d \
#   --name app2docker-agent \
#   --restart=always \
#   -e AGENT_TOKEN=<token> \
#   -e SERVER_URL=http://<server_host>:<port> \
#   -v /var/run/docker.sock:/var/run/docker.sock \
#   -v /proc:/host/proc:ro \
#   -v /sys:/host/sys:ro \
#   app2docker-agent:latest

# 复制启动脚本
COPY backend/agent/start.sh /app/backend/agent/start.sh
RUN chmod +x /app/backend/agent/start.sh

# 启动 Agent 程序（使用启动脚本捕获错误）
CMD ["/app/backend/agent/start.sh"]

