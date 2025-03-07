import asyncio

import uvicorn

from config import config


async def main():
    server = uvicorn.Server(
        uvicorn.Config(
            "app.main:app",
            host="0.0.0.0",
            port=config.server.port,
            # loop="uvloop",  # 使用更高效的 uvloop 事件循环
            reload=False,
            workers=config.server.workers,  # 启动 n 个进程（reload=True 时不生效）
            limit_concurrency=config.server.limit_concurrency,  # 每个进程最多同时处理 n 个并发请求
            limit_max_requests=config.server.limit_max_requests,  # 每个进程处理 n 个请求后重启
        )
    )
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
