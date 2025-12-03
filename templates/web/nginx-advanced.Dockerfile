# 静态网站 Dockerfile (Nginx 高级配置版)
# 支持多个可配置参数，适用于需要自定义配置的场景

# 使用阿里云 Nginx 镜像
FROM registry.cn-hangzhou.aliyuncs.com/library/nginx:{{NGINX_VERSION:alpine}}

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN apk add --no-cache tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR {{WORKDIR:/usr/share/nginx/html}}

# 复制静态文件到 nginx 目录
COPY . {{WORKDIR:/usr/share/nginx/html}}/

# 创建自定义 nginx 配置
RUN echo 'server {' > /etc/nginx/conf.d/default.conf && \
    echo '    listen {{EXPOSE_PORT:80}};' >> /etc/nginx/conf.d/default.conf && \
    echo '    server_name {{SERVER_NAME:localhost}};' >> /etc/nginx/conf.d/default.conf && \
    echo '    root {{WORKDIR:/usr/share/nginx/html}};' >> /etc/nginx/conf.d/default.conf && \
    echo '    index index.html index.htm;' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    # Gzip 压缩' >> /etc/nginx/conf.d/default.conf && \
    echo '    gzip on;' >> /etc/nginx/conf.d/default.conf && \
    echo '    gzip_min_length {{GZIP_MIN_LENGTH:1000}};' >> /etc/nginx/conf.d/default.conf && \
    echo '    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    # SPA 路由支持' >> /etc/nginx/conf.d/default.conf && \
    echo '    location / {' >> /etc/nginx/conf.d/default.conf && \
    echo '        try_files $uri $uri/ /index.html;' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '' >> /etc/nginx/conf.d/default.conf && \
    echo '    # 静态资源缓存（{{CACHE_DURATION:1y}}）' >> /etc/nginx/conf.d/default.conf && \
    echo '    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {' >> /etc/nginx/conf.d/default.conf && \
    echo '        expires {{CACHE_DURATION:1y}};' >> /etc/nginx/conf.d/default.conf && \
    echo '        add_header Cache-Control "public, immutable";' >> /etc/nginx/conf.d/default.conf && \
    echo '    }' >> /etc/nginx/conf.d/default.conf && \
    echo '}' >> /etc/nginx/conf.d/default.conf

# 暴露端口
EXPOSE {{EXPOSE_PORT:80}}

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:{{EXPOSE_PORT:80}}/ || exit 1

# 启动 Nginx
CMD ["nginx", "-g", "daemon off;"]

