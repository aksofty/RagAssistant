
from loguru import logger
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app import CLIENT_DB_FILE
from app.models.base import Base
from app.models.bot_user import BotUser
from app.models.bot_user_message import BotUserMessage
from app.models.source import Source
from app.models.system_setting import SystemSetting


engine = create_async_engine(f"sqlite+aiosqlite:///{CLIENT_DB_FILE}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise