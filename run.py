import logging.config

import uvicorn
from app.core.log import LOGGING_CONFIG
from app.config import config

logging.config.dictConfig(LOGGING_CONFIG)


def main():
    try:
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=config.server.port,
            # loop="uvloop",  # 使用更高效的 uvloop 事件循环
            reload=False,
            workers=config.server.workers,  # 启动 n 个进程（reload=True 时不生效）
            limit_concurrency=config.server.limit_concurrency,  # 每个进程最多同时处理 n 个并发请求
            limit_max_requests=config.server.limit_max_requests,  # 每个进程处理 n 个请求后重启
        )
    except KeyboardInterrupt:
        pass
    finally:
        pass


if __name__ == "__main__":
    main()
