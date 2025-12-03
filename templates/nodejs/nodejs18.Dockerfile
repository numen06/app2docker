# Node.js 18 前端应用 Dockerfile (多阶段构建)
# 第一阶段：使用 Node.js 18 构建应用
# 使用阿里云镜像源加速下载
FROM registry.cn-hangzhou.aliyuncs.com/library/node:18-alpine as builder

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm install

# 复制应用文件
COPY . .

# 构建应用
RUN npm run build

# 第二阶段：使用 Nginx 部署
# 使用阿里云镜像源加速下载
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 从构建阶段复制构建产物到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 复制自定义 Nginx 配置（如果存在）
# COPY nginx.conf /etc/nginx/nginx.conf

# 暴露端口
EXPOSE {{{EXPOSE_PORT:80}}

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

