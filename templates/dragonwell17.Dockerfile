FROM registry.cn-shanghai.aliyuncs.com/51jbm/spring-boot-layer:dragonwell17 as builder
ARG JAR_FILE=*.jar
COPY ${JAR_FILE} application.jar
RUN java -Djarmode=layertools -jar application.jar extract

FROM registry.cn-shanghai.aliyuncs.com/51jbm/spring-boot-layer:dragonwell17

# 从 builder 阶段复制分层内容（注意路径！）
COPY --from=builder /root/app/dependencies/ ./
COPY --from=builder /root/app/snapshot-dependencies/ ./
COPY --from=builder /root/app/application/ ./
COPY --from=builder /root/app/spring-boot-loader/ ./
