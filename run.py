import uvicorn

from config import config

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=config.port,
        reload=False,
        # loop="uvloop",  # 使用更高效的 uvloop 事件循环
        workers=4,  # 启动 n 个进程（reload=True 时不生效）
        limit_concurrency=500,  # 每个进程最多处理 n 个并发请求
        limit_max_requests=10000,  # 每个进程处理 n 个请求后重启
    )
