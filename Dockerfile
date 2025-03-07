FROM python:3.10-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    tzdata \
    vim \
    curl && \
    # 配置时区
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    # 清理缓存（减小镜像体积）
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvloop==0.21.0

HEALTHCHECK --interval=30s --timeout=10s \
  CMD supervisorctl -c /app/supervisord.conf status | \
    awk '!/RUNNING/ && !/^$/{exit 1}'

CMD ["supervisord", "-n", "-c", "supervisord.conf"]
