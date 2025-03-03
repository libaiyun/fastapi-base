from app.core.db import session_factory


async def get_session():
    async with session_factory() as session:
        yield session
        await session.commit()
