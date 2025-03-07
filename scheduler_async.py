import asyncio
import logging.config

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.log import LOGGING_CONFIG
from app.task.service_register import register_service
from config import config

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

"""异步任务定时调度，基于asyncio，适合I/O密集型任务。"""


def start_scheduler():
    scheduler = AsyncIOScheduler()

    if config.nacos.enable_service_register:
        scheduler.add_job(
            register_service,
            IntervalTrigger(seconds=10),  # 间隔10秒执行
            max_instances=1,  # 允许同时运行的最大实例数
            misfire_grace_time=30,  # 如果错过了执行时间，最多延迟30秒执行
            coalesce=True,  # 合并错过的执行
        )

    scheduler.start()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    start_scheduler()
