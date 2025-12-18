# 通用 JAR 应用 Dockerfile
# 适用于任何 Java 应用（不限于 Spring Boot）
# 不会在构建时运行 JAR，只在容器启动时运行

FROM dragonwell-registry.cn-hangzhou.cr.aliyuncs.com/dragonwell/dragonwell:17-anolis
ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
VOLUME /tmp
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone

#安装字体库
RUN yum install -y fontconfig
#安装网络工具
RUN yum install -y net-tools

#yum安装清理缓存
RUN yum clean all
RUN rm -rf /var/cache/yum

# 设置工作目录
WORKDIR /app

# 复制 JAR 文件
COPY *.jar /app/app.jar

# 暴露端口
EXPOSE {{EXPOSE_PORT:8080}}

# 启动应用（仅在容器运行时执行，不会在构建时执行）
ENTRYPOINT ["java","-Djava.security.egd=file:/dev/./urandom","-jar","app.jar"]