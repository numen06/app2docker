# 静态网站 Dockerfile (Nginx 简化版)
# 适用于简单的静态网站部署

# 使用阿里云 Nginx 镜像
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:alpine

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 复制静态文件到 nginx 默认目录
COPY . /usr/share/nginx/html/

# 修改默认端口
RUN sed -i 's/listen       80;/listen       {{EXPOSE_PORT:80}};/g' /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE {{EXPOSE_PORT:80}}

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

