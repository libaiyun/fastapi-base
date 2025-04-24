import asyncio
import logging.config
import signal
import sys

from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.triggers.interval import IntervalTrigger

from app.core.log import LOGGING_CONFIG
from app.config import config


from app.core.nacos.registry import ServiceRegistry

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

"""异步任务定时调度，基于asyncio，适合I/O密集型任务。"""


def scheduler_task(scheduler: AsyncIOScheduler):
    """添加调度任务"""
    # scheduler.add_job(
    #     you_task,
    #     IntervalTrigger(seconds=10),  # 间隔10秒执行
    #     max_instances=1,  # 允许同时运行的最大实例数
    #     misfire_grace_time=30,  # 如果错过了执行时间，最多延迟30秒执行
    #     coalesce=True,  # 合并错过的执行
    # )


async def main():
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    if sys.platform == "win32":
        # Windows 仅支持 SIGINT (Ctrl+C)
        signal.signal(signal.SIGINT, lambda sig, frame: loop.call_soon_threadsafe(stop_event.set))
    else:
        # Unix-like 系统支持 SIGTERM 和 SIGINT
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, stop_event.set)

    async with ServiceRegistry(config) as registry:
        await registry.start()

        scheduler = AsyncIOScheduler()
        try:
            scheduler_task(scheduler)
            scheduler.start()

            await stop_event.wait()
        finally:
            scheduler.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
