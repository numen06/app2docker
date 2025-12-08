# ------------------------------------------------------------
# Stage 1: 构建整个项目（使用阿里云 Maven 镜像）
# ------------------------------------------------------------
FROM registry.cn-hangzhou.aliyuncs.com/acs/maven:3.8.6-openjdk-17 AS builder

WORKDIR /app
COPY . .

# 可选：配置阿里云 Maven 镜像加速（提升依赖下载速度）
RUN mkdir -p /root/.m2 && \
    echo '<settings><mirrors><mirror><id>aliyunmaven</id><mirrorOf>*</mirrorOf><name>阿里云公共仓库</name><url>https://maven.aliyun.com/repository/public</url></mirror></mirrors></settings>' > /root/.m2/settings.xml

# 执行构建，跳过测试（生产环境可移除）
RUN mvn clean package -DskipTests

# ------------------------------------------------------------
# 公共基础运行镜像（华为云 Java 运行时）
# ------------------------------------------------------------
FROM dragonwell-registry.cn-hangzhou.cr.aliyuncs.com/dragonwell/dragonwell:8-anolis AS base

WORKDIR /app
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# ------------------------------------------------------------
# 每个服务 stage 名称 = pom.xml 中的 <artifactId>
# ------------------------------------------------------------

FROM base AS jbm-cluster-platform-auth
COPY --from=builder /app/dist/jbm-cluster-platform-auth.jar app.jar
EXPOSE 9200
USER 1001
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-bigscreen
COPY --from=builder /app/dist/jbm-cluster-platform-bigscreen.jar app.jar
EXPOSE 9203
USER 1002
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-center
COPY --from=builder /app/dist/jbm-cluster-platform-center.jar app.jar
EXPOSE 9204
USER 1003
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-doc
COPY --from=builder /app/dist/jbm-cluster-platform-doc.jar app.jar
EXPOSE 9205
USER 1004
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-gateway
COPY --from=builder /app/dist/jbm-cluster-platform-gateway.jar app.jar
EXPOSE 9999
USER 1005
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-job
COPY --from=builder /app/dist/jbm-cluster-platform-job.jar app.jar
EXPOSE 9206
USER 1006
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-logs
COPY --from=builder /app/dist/jbm-cluster-platform-logs.jar app.jar
EXPOSE 9207
USER 1007
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-push
COPY --from=builder /app/dist/jbm-cluster-platform-push.jar app.jar
EXPOSE 9208
USER 1008
CMD ["java", "-jar", "app.jar"]

FROM base AS jbm-cluster-platform-weixin
COPY --from=builder /app/dist/jbm-cluster-platform-weixin.jar app.jar
EXPOSE 9209
USER 1009
CMD ["java", "-jar", "app.jar"]