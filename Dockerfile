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


# ✅ 创建官方 alinux3-docker.repo（阿里云镜像 + GPG 校验）
RUN cat > /etc/yum.repos.d/alinux3-docker.repo <<'EOF'
[alinux3-docker]
name=Alibaba Cloud Linux 3 - Docker
baseurl=https://mirrors.aliyun.com/alinux/3/docker/$basearch/
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/alinux/RPM-GPG-KEY-Alibaba-Cloud
repo_gpgcheck=0
skip_if_unavailable=True
EOF

# ✅ 清理缓存 + 更新元数据
RUN dnf clean all && \
    dnf makecache --refresh

# ✅ 关键：安装 docker-ce（它自带 docker CLI 和 buildx 插件！）
RUN echo "📦 正在安装 docker-ce（含 CLI + buildx）..." && \
    dnf install -y docker-ce containerd.io && \
    \
    # ✅ 启动 containerd（buildx 需要运行时）
    systemctl enable --now containerd && \
    \
    # ✅ 验证 buildx 插件是否已就位（它被自动安装到 /usr/libexec/docker/cli-plugins/）
    ls -l /usr/libexec/docker/cli-plugins/docker-buildx 2>/dev/null || \
    (echo "⚠️  buildx 插件未自动安装，手动链接..." && \
    mkdir -p ~/.docker/cli-plugins && \
    ln -sf /usr/libexec/docker/cli-plugins/docker-buildx ~/.docker/cli-plugins/)

# ✅ 验证（构建阶段即检查）
RUN echo "✅ docker version:" && docker --version && \
    echo "✅ docker buildx version:" && docker buildx version && \
    echo "✅ docker info (short):" && docker info --format '{{.ServerVersion}} {{.DefaultRuntime}}'


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
