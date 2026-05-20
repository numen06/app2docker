# 多阶段构建：前端 + 后端

# ============ 阶段 1: 构建前端 ============
# 使用阿里云 Node.js 镜像加速下载
FROM node:22 AS frontend-builder

# 切换到 root 用户以创建目录
USER root

# 创建所需目录并设置权限
RUN mkdir -p /app/frontend /app/dist && \
    chown -R node:node /app/frontend /app/dist

# 设置工作目录
WORKDIR /app/frontend

# 切换到 node 用户
USER node

# 设置 Node.js 环境变量（构建时需要 devDependencies，所以不设置 NODE_ENV=production）
ENV NODE_OPTIONS="--max-old-space-size=4096"

# 仅复制依赖文件以利用缓存
COPY --chown=node:node frontend/package*.json ./

# 安装依赖（包括 devDependencies，因为 vite 在 devDependencies 中）
RUN npm config set registry https://registry.npmmirror.com && \
    npm install --legacy-peer-deps && \
    npm cache clean --force

# 复制剩余前端代码并构建
COPY --chown=node:node frontend/ ./

# 构建生产版本（输出到 /app/dist）
RUN npm run build

# ============ 阶段 2: Python 后端基础镜像 ============
FROM registry.cn-shanghai.aliyuncs.com/51jbm/docker:27.2.0-cli AS backend-base

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

# 先全量升级再安装 python3/expat，并强制二者 ABI 一致（修复 pyexpat 符号缺失）
RUN apk update && apk upgrade -U && \
    apk add --no-cache \
    python3 \
    python3-dev \
    py3-pip \
    py3-setuptools \
    expat \
    curl \
    jq \
    git \
    make \
    gcc \
    musl-dev \
    linux-headers \
    docker-compose \
    tzdata && \
    (apk fix python3 expat 2>/dev/null || true) && \
    (python -c "import pyexpat" 2>/dev/null || ( \
      apk del python3 py3-pip py3-setuptools && \
      apk add --no-cache python3 py3-pip py3-setuptools expat && \
      python -c "import pyexpat" \
    ))

RUN ln -sf python3 /usr/bin/python && \
    ln -sf pip3 /usr/bin/pip

RUN python -m pip install --upgrade --break-system-packages \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --timeout 300 \
    --retries 5 \
    pip

ENV TZ=Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo "$TZ" > /etc/timezone

RUN echo "✅ Python version:" && python --version && \
    echo "✅ pip version:" && pip --version && \
    echo "✅ docker version:" && docker --version && \
    echo "✅ buildx version:" && docker buildx version && \
    echo "✅ QEMU arm64 registered:" && ls /proc/sys/fs/binfmt_misc/qemu-arm64 2>/dev/null || echo "⚠️ QEMU not found (should not happen)"


WORKDIR /app

# 复制 Python 依赖文件
COPY requirements.txt .

# ✅ 创建虚拟环境并激活安装
RUN python -m venv .venv && \
    .venv/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    .venv/bin/pip config set global.timeout 300 && \
    .venv/bin/pip config set global.retries 5 && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt && \
    echo "✅ docker-compose version:" && docker-compose --version || echo "⚠️ docker-compose not found"

# ✅ 设置 PATH，让 .venv/bin 优先（等效于 source .venv/bin/activate）
ENV PATH="/app/.venv/bin:$PATH"

# 复制后端代码（含 backend/VERSION，供运行时版本号与更新检查）
COPY backend/ ./backend/

# ============ 阶段 3: Agent 镜像 ============
FROM backend-base AS app2docker-agent

# Agent 不需要前端和模板，只需要后端代码（已在 backend-base 阶段复制）

# ✅ 设置 Python 无缓冲输出，确保日志立即输出到控制台
ENV PYTHONUNBUFFERED=1
# ✅ 设置 PYTHONPATH，确保可以正确导入 backend 模块
ENV PYTHONPATH="/app"

# 说明：
# - Agent 需要访问 Docker daemon（通过 /var/run/docker.sock 卷映射）
# - Agent 需要访问主机信息（通过 /proc 和 /sys 卷映射）
# 
# 构建 Agent 镜像：
# docker build --target app2docker-agent -t app2docker-agent:latest .
#
# 运行 Agent 容器：
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

# ============ 阶段 4: 主程序镜像（默认） ============
FROM backend-base AS app2docker

# 从第一阶段复制构建好的前端文件（vite.config.js 中 outDir 设置为 '../dist'）
COPY --from=frontend-builder /app/dist ./dist

# 复制内置模板
COPY templates/ ./templates/

# 说明：
# - templates/ 目录包含内置模板（按项目类型分类）
# - data/ 目录在运行时通过卷映射提供
# - favicon.ico 已包含在前端构建产物（dist/）中
# 
# 构建主程序镜像（默认，不指定 --target 时构建此镜像）：
# docker build -t app2docker:latest .
#
# 或显式指定：
# docker build --target app2docker -t app2docker:latest .
#
# 运行容器：
# docker run -d \
#   -v $(pwd)/data:/app/data \
#   -v /var/run/docker.sock:/var/run/docker.sock \
#   -p 8000:8000 \
#   app2docker:latest
#
# 自定义端口：
# docker run -d \
#   -e APP_PORT=9000 \
#   -v $(pwd)/data:/app/data \
#   -v /var/run/docker.sock:/var/run/docker.sock \
#   -p 9000:9000 \
#   app2docker:latest

# 设置默认服务端口（可通过环境变量覆盖）
ENV APP_PORT=8000
ENV APP_HOST=0.0.0.0

# 暴露服务端口
EXPOSE ${APP_PORT}

# 启动后端服务（后端会服务前端构建文件）
# 端口可通过环境变量 APP_PORT 设置
CMD ["python", "backend/app.py"]
