FROM python:3.10-slim

ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Debian 12 DEB822格式
RUN sed -i \
    's/deb.debian.org/mirrors.ustc.edu.cn/g' \
    /etc/apt/sources.list.d/debian.sources

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    curl \
    vim \
    tzdata && \
    # 配置时区
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    # 清理缓存（减小镜像体积）
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 优先安装依赖以利用缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn

# 复制应用代码
COPY . .

HEALTHCHECK --interval=30s --timeout=10s \
  CMD supervisorctl -c /app/supervisord.conf status | \
    awk '!/RUNNING/ && !/^$/{exit 1}'

CMD ["supervisord", "-n", "-c", "supervisord.conf"]
