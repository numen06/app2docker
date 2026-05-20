# Agent Dockerfile - 独立的 Agent 镜像构建文件
# 与主 Dockerfile backend-base 策略一致

FROM registry.cn-shanghai.aliyuncs.com/51jbm/docker:27.2.0-cli AS docker-tools

FROM alibaba-cloud-linux-3-registry.cn-hangzhou.cr.aliyuncs.com/alinux3/python:3.12.0

COPY --from=docker-tools /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-tools /usr/local/libexec/docker/cli-plugins/ /usr/local/libexec/docker/cli-plugins/

ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo "$TZ" > /etc/timezone

RUN yum install -y curl jq git make gcc gcc-c++ python3-devel && \
    yum clean all && \
    rm -rf /var/cache/yum

RUN python -m pip install --upgrade \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --timeout 300 \
    --retries 5 \
    pip

RUN echo "✅ Python version:" && python --version && \
    echo "✅ pip version:" && pip --version && \
    echo "✅ docker version:" && docker --version && \
    echo "✅ compose version:" && (docker compose version || docker-compose --version || echo "⚠️ compose not found")

WORKDIR /app

COPY requirements.txt .

RUN python -m venv .venv && \
    .venv/bin/pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    .venv/bin/pip config set global.timeout 300 && \
    .venv/bin/pip config set global.retries 5 && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install --no-cache-dir -r requirements.txt && \
    .venv/bin/pip install --no-cache-dir psutil websockets

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

COPY backend/ ./backend/

COPY backend/agent/start.sh /app/backend/agent/start.sh
RUN chmod +x /app/backend/agent/start.sh

CMD ["/app/backend/agent/start.sh"]
