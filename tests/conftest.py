import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.deps import get_session
from app.core.db import ASYNC_DATABASE_URL
from app.main import app
from config import config

engine = create_async_engine(
    ASYNC_DATABASE_URL,  # 请替换成用于单元测试的数据库URL
    echo=config.db.echo,
    poolclass=NullPool,  # pytest 无法使用 AsyncAdaptedQueuePool
    pool_recycle=60 * 60,
)

# 异步会话
session_factory = async_sessionmaker[AsyncSession](
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def init_db():
    pass


@pytest_asyncio.fixture()  # 默认scope="function"，不同测试用例的数据相互隔离。需共享时，scope="session"
async def db_session():
    async with session_factory() as session:
        yield session
        # await session.commit()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    def get_session_override():
        return db_session

    app.dependency_overrides[get_session] = get_session_override  # 替换成测试用的会话
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
