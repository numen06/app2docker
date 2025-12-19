FROM dragonwell-registry.cn-hangzhou.cr.aliyuncs.com/dragonwell/dragonwell:21-anolis AS builder

WORKDIR /app

# 安装 wget、unzip（用于下载和解压 Maven）
RUN set -xeuo pipefail && \
    dnf makecache --refresh && \
    dnf install -y \
    --noplugins \
    --setopt=install_weak_deps=False \
    --setopt=skip_if_unavailable=True \
    --setopt=tsflags=nodocs \
    --nogpgcheck \
    wget unzip && \
    dnf clean all && \
    rm -rf /var/cache/dnf* /tmp/* /var/tmp/*

# 从阿里云镜像下载 Maven（加速）
ENV MAVEN_VERSION=3.9.2
ENV MAVEN_HOME=/opt/maven
ENV PATH=${MAVEN_HOME}/bin:${PATH}

RUN wget https://maven.aliyun.com/repository/public/org/apache/maven/apache-maven/${MAVEN_VERSION}/apache-maven-${MAVEN_VERSION}-bin.zip -O /tmp/maven.zip && \
    unzip /tmp/maven.zip -d /opt && \
    mv /opt/apache-maven-${MAVEN_VERSION} ${MAVEN_HOME} && \
    rm /tmp/maven.zip

# 复制代码并构建
COPY . .

# 执行构建，跳过测试（生产环境可移除）指定setting.xml
RUN --mount=type=cache,target=/root/.m2 mvn clean package -DskipTests -s settings.xml

# ------------------------------------------------------------
# 公共运行基础（使用轻量 Dragonwell JRE）
# 注意：官方未提供 "jre-alpine" 版本，这里使用完整 JDK 但仅运行 jar（可接受）
# 或者改用 eclipse-temurin:jre-alpine 以减小体积（见下方说明）
# ------------------------------------------------------------
FROM dragonwell-registry.cn-hangzhou.cr.aliyuncs.com/dragonwell/dragonwell:21-anolis AS base

WORKDIR /app

ENV LANG C.UTF-8
ENV LC_ALL C.UTF-8
VOLUME /tmp
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo 'Asia/Shanghai' >/etc/timezone

#安装字体库
RUN yum install -y fontconfig
#安装网络工具
RUN yum install -y lrzsz net-tools vim wget

COPY --from=builder /app/dist/*.jar app.jar


# 启动应用（仅在容器运行时执行，不会在构建时执行）
ENTRYPOINT ["java","-Djava.security.egd=file:/dev/./urandom","-jar","app.jar"]

