# Spring Boot 应用 Dockerfile (可自定义版本和参数)
# 支持自定义 Java 版本、JVM 参数等

# 使用阿里云 OpenJDK 镜像
FROM registry.cn-hangzhou.aliyuncs.com/library/openjdk:{{JAVA_VERSION:17}}-jre-slim

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y --no-install-recommends tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    rm -rf /var/lib/apt/lists/*

# 维护者信息
LABEL maintainer="{{MAINTAINER:App2Docker}}"
LABEL version="{{VERSION:1.0.0}}"

# 设置工作目录
WORKDIR {{WORKDIR:/app}}

# 复制 JAR 文件
COPY *.jar {{WORKDIR:/app}}/app.jar

# 创建非 root 用户（安全考虑）
RUN addgroup --system --gid 1001 appuser && \
    adduser --system --uid 1001 --gid 1001 appuser && \
    chown -R appuser:appuser {{WORKDIR:/app}}

# 切换到非 root 用户
USER appuser

# 暴露端口
EXPOSE {{EXPOSE_PORT:8080}}

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:{{EXPOSE_PORT:8080}}/actuator/health || exit 1

# JVM 参数
ENV JAVA_OPTS="{{JAVA_OPTS:-Xmx512m -Xms256m -XX:+UseG1GC}}"

# 启动应用
ENTRYPOINT ["sh", "-c", "java ${JAVA_OPTS} -jar {{WORKDIR:/app}}/app.jar"]

