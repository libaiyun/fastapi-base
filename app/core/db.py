import logging
import time
from urllib import parse

from sqlalchemy import create_engine, AsyncAdaptedQueuePool, event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncConnection
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from config import config

logger = logging.getLogger(__name__)

DATABASE_URL = "mysql+pymysql://{}:{}@{}:{}/{}".format(
    parse.quote(config.mysql.user),
    parse.quote(config.mysql.password),
    config.mysql.host,
    config.mysql.port,
    config.mysql.database,
)
sync_engine = create_engine(
    DATABASE_URL,  # 数据库连接 URL，可以是字符串或 URL 对象。
    echo=True,  # 控制是否启用 SQL 日志记录，True 会在标准输出中打印执行的 SQL 语句。
    echo_pool=True,  # 控制是否为连接池启用日志记录，打印池的相关操作日志。
    logging_name="db",  # 日志记录的名称，为此引擎实例指定日志标签。
    pool_logging_name="db_pool",  # 连接池的日志标签。
    hide_parameters=False,  # 控制是否隐藏 SQL 参数，避免日志中暴露敏感数据。
    pool_size=5,  # 池中最大连接数。
    pool_timeout=30,  # (池满)等待获取连接的超时时间。
    pool_recycle=-1,  # 每个连接的存活时间，超过该时间则重置连接，防止数据库因空闲超时断开连接。(例如MySQL的默认空闲超时通常是8小时)
    pool_pre_ping=False,  # 启用健康检查，每次借出连接时验证连接是否活跃，避免长时间未用的连接失效。
    pool_use_lifo=False,  # 是否使用后进先出（LIFO）策略，而非默认的先进先出（FIFO）。
    max_overflow=10,  # 连接池的溢出连接数，超过池大小时的最大额外连接数。
)
# sync_engine.pool.status()
sync_session_factory = sessionmaker[Session](
    sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

ASYNC_DATABASE_URL = "mysql+aiomysql://{}:{}@{}:{}/{}".format(
    parse.quote(config.mysql.user),
    parse.quote(config.mysql.password),
    config.mysql.host,
    config.mysql.port,
    config.mysql.database,
)
# 异步数据库引擎
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=config.db.echo,  # 是否输出 SQL
    poolclass=AsyncAdaptedQueuePool,
    pool_size=config.db.pool_size,  # 连接池大小
    # https://docs.pingcap.com/zh/tidb/stable/dev-guide-timeouts-in-tidb#jdbc-%E6%9F%A5%E8%AF%A2%E8%B6%85%E6%97%B6
    pool_recycle=60 * 60,
    max_overflow=config.db.max_overflow,  # 连接池的溢出连接数
)


@event.listens_for(engine.sync_engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    conn.info["start_time"] = time.perf_counter()


@event.listens_for(engine.sync_engine, "after_cursor_execute")
def log_slow_queries(conn, cursor, statement, parameters, context, executemany):
    start_time = conn.info.pop("start_time", None)
    if start_time is None:
        return
    elapsed_time = time.perf_counter() - start_time
    if elapsed_time > config.db.slow_query_threshold:
        logger.info(f"Slow query ({elapsed_time:.2f} seconds): {statement} | Parameters: {parameters}")


async def create_tables():
    async with engine.begin() as conn:
        conn: AsyncConnection
        # await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    await engine.dispose()


# 异步会话工厂
session_factory = async_sessionmaker[AsyncSession](
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
