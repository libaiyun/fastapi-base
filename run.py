import asyncio
import logging.config

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from skywalking import agent, config as sw_config

from app.constants import SW_AGENT_DISABLE_PLUGINS
from app.core.log import LOGGING_CONFIG
from app.core.nacos.config import config_syncer
from app.config import config
from app.core.nacos.registry import service_registry

logging.config.dictConfig(LOGGING_CONFIG)


async def main():
    scheduler = AsyncIOScheduler()
    scheduler.start()

    try:
        await service_registry.start()
        await config_syncer.start()
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
        await server.serve()  # 单进程模式，workers 参数被忽略
    except KeyboardInterrupt:
        pass
    finally:
        scheduler.shutdown()
        await service_registry.stop()
        await config_syncer.stop()


if __name__ == "__main__":
    if config.sw.enabled:
        sw_config.init(
            agent_collector_backend_services=config.sw.agent_collector_backend_services,
            agent_name=config.service_name,
            # TODO: 自定义agent_instance_name避免应用重启后实例名不同
            agent_log_reporter_active=config.sw.agent_log_reporter_active,
            agent_log_reporter_level=config.sw.agent_log_reporter_level,
            agent_meter_reporter_active=config.sw.agent_meter_reporter_active,
            agent_disable_plugins=SW_AGENT_DISABLE_PLUGINS,
        )
        agent.start()
    asyncio.run(main())
