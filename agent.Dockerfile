# Agent Dockerfile - 与主 Dockerfile backend-base 策略一致

FROM registry.cn-shanghai.aliyuncs.com/51jbm/docker:27.2.0-cli

RUN sed -i 's/dl-cdn.alpinelinux.org/mirrors.aliyun.com/g' /etc/apk/repositories

RUN apk update && apk upgrade -U && \
    apk add --no-cache \
    python3 \
    py3-pip \
    py3-setuptools \
    expat \
    curl \
    jq \
    git \
    make \
    gcc \
    musl-dev \
    linux-headers \
    docker-compose \
    tzdata && \
    (apk fix python3 expat 2>/dev/null || true) && \
    (python -c "import pyexpat" 2>/dev/null || ( \
      apk del python3 py3-pip py3-setuptools && \
      apk add --no-cache python3 py3-pip py3-setuptools expat && \
      python -c "import pyexpat" \
    ))

RUN ln -sf python3 /usr/bin/python && \
    ln -sf pip3 /usr/bin/pip

RUN python -m pip install --upgrade --break-system-packages \
    --index-url https://mirrors.aliyun.com/pypi/simple/ \
    --timeout 300 \
    --retries 5 \
    pip

ENV TZ=Asia/Shanghai
RUN ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo "$TZ" > /etc/timezone

RUN echo "✅ Python version:" && python --version && \
    echo "✅ pip version:" && pip --version && \
    echo "✅ docker version:" && docker --version && \
    echo "✅ docker-compose version:" && docker-compose --version

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
