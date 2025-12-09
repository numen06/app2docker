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
FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.11.1

# 👇 【统一修复源】—— 外网构建必加！
RUN sed -i 's|mirrors\.cloud\.aliyuncs\.com|mirrors.aliyun.com|g' /etc/yum.repos.d/*.repo 2>/dev/null || true

ENV TZ=Asia/Shanghai

# 安装 docker CLI 和 buildx 插件
RUN dnf install -y tzdata curl git \
    && ln -sf /usr/share/zoneinfo=$TZ /etc/localtime \
    && echo "$TZ" > /etc/timezone 

# ✅ STEP 1: 安装 Docker CLI 官方静态二进制（v24.0.7，适配 ALinux3 glibc 2.28）
ARG DOCKER_CLI_VERSION=24.0.7
ARG ARCH=$(uname -m | sed 's/x86_64/x86_64/; s/aarch64/aarch64/')
RUN curl -fsSL "https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/static/stable/${ARCH}/docker-${DOCKER_CLI_VERSION}.tgz" \
    | tar -xz -C /tmp && \
    cp /tmp/docker/docker /usr/local/bin/docker && \
    chmod +x /usr/local/bin/docker && \
    rm -rf /tmp/docker

# ✅ STEP 2: 安装 buildx 插件（官方 release，清华镜像）
ARG BUILDX_VERSION=v0.14.1
RUN mkdir -p ~/.docker/cli-plugins && \
    curl -fsSL "https://mirrors.tuna.tsinghua.edu.cn/github-release/docker/buildx/${BUILDX_VERSION}/download/buildx-${BUILDX_VERSION}.linux-${ARCH}" \
    -o ~/.docker/cli-plugins/docker-buildx && \
    chmod +x ~/.docker/cli-plugins/docker-buildx

# ✅ STEP 3: 验证（构建阶段即保障可用性）
RUN docker --version && \
    docker buildx version && \
    echo "✅ Docker CLI ${DOCKER_CLI_VERSION} + Buildx ${BUILDX_VERSION} installed successfully."


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
