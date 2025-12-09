# 多阶段构建：前端 + 后端

# ============ 阶段 1: 构建前端 ============
# 使用阿里云 Node.js 镜像加速下载
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/node:20.16 AS frontend-builder

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

# ============ 阶段 2: Python 后端 ============
# 使用阿里云 Python 镜像加速下载
FROM ac2-registry.cn-hangzhou.cr.aliyuncs.com/ac2/base:ubuntu22.04-py310


# ✅ 1. 确保 apt 源配置正确（兼容无 sources.list 的情况）
RUN mkdir -p /etc/apt && \
    echo "deb http://archive.ubuntu.com/ubuntu jammy main universe" > /etc/apt/sources.list && \
    echo "deb http://archive.ubuntu.com/ubuntu jammy-updates main universe" >> /etc/apt/sources.list && \
    echo "deb http://archive.ubuntu.com/ubuntu jammy-security main universe" >> /etc/apt/sources.list

# ✅ 2. 更新并安装 ca-certificates + curl（HTTPS 支持）
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ✅ 3. 直接下载 GPG 密钥到 keyring（跳过 gpg 校验步骤）
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/ubuntu/gpg \
    -o /etc/apt/keyrings/docker.gpg

# ✅ 4. 添加 Docker APT 源（使用阿里云镜像）
RUN echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://mirrors.aliyun.com/docker-ce/linux/ubuntu \
    jammy stable" \
    | tee /etc/apt/sources.list.d/docker.list > /dev/null

# ✅ 5. 安装 docker-ce-cli + buildx 插件
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    docker-ce-cli \
    docker-buildx-plugin \
    containerd.io \
    && rm -rf /var/lib/apt/lists/*

# ✅ 6. 验证
RUN echo "✅ docker version:" && docker --version && \
    echo "✅ docker buildx version:" && docker buildx version


WORKDIR /app

# 复制 Python 依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY backend/ ./backend/

# 从第一阶段复制构建好的前端文件（vite.config.js 中 outDir 设置为 '../dist'）
COPY --from=frontend-builder /app/dist ./dist

# 复制内置模板
COPY templates/ ./templates/

# 说明：
# - templates/ 目录包含内置模板（按项目类型分类）
# - data/ 目录在运行时通过卷映射提供
# - favicon.ico 已包含在前端构建产物（dist/）中
# 
# 运行容器：
# docker run -d \
#   -v $(pwd)/data:/app/data \
#   -v /var/run/docker.sock:/var/run/docker.sock \
#   -p 8000:8000 \
#   app2docker
#
# 自定义端口：
# docker run -d \
#   -e APP_PORT=9000 \
#   -v $(pwd)/data:/app/data \
#   -v /var/run/docker.sock:/var/run/docker.sock \
#   -p 9000:9000 \
#   app2docker

# 设置默认服务端口（可通过环境变量覆盖）
ENV APP_PORT=8000
ENV APP_HOST=0.0.0.0

# 暴露服务端口
EXPOSE ${APP_PORT}

# 启动后端服务（后端会服务前端构建文件）
# 端口可通过环境变量 APP_PORT 设置
CMD ["python", "backend/app.py"]
