import logging.config
import os
import time

from apscheduler.executors.pool import ProcessPoolExecutor
from apscheduler.schedulers.blocking import BlockingScheduler

from app.core.log import LOGGING_CONFIG

logging.config.dictConfig(LOGGING_CONFIG)

logger = logging.getLogger(__name__)

"""同步任务定时调度，默认多进程并发以利用多核cpu能力，适合计算密集型任务。"""


def scheduler_test():
    logger.warning("test start")
    time.sleep(2)
    logger.warning("test end")


def scheduler_test2():
    logger.warning("test2 start")
    time.sleep(2)
    logger.warning("test2 end")


def start_scheduler():
    scheduler = BlockingScheduler(executors={"default": ProcessPoolExecutor(os.cpu_count())})

    # scheduler.add_job(scheduler_test, "interval", seconds=10)
    # scheduler.add_job(scheduler_test2, "interval", seconds=10)
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass


if __name__ == "__main__":
    start_scheduler()
