# 通用 JAR 应用 Dockerfile
# 适用于任何 Java 应用（不限于 Spring Boot）
# 不会在构建时运行 JAR，只在容器启动时运行

FROM registry.cn-shanghai.aliyuncs.com/numen/spring-boot-dev:dragonwell8

# 设置时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

# 设置工作目录
WORKDIR /app

# 复制 JAR 文件
COPY *.jar /app/app.jar

# 暴露端口
EXPOSE {{EXPOSE_PORT:8080}}

# 启动应用（仅在容器运行时执行，不会在构建时执行）
CMD ["java", "-jar", "/app/app.jar"]

