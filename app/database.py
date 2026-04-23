
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app import CLIENT_DB_FILE
from app.models.base import Base
from app.models.bot_user import BotUser
from app.models.bot_user_message import BotUserMessage
#from app.models.rag_source import RAGSourceHtml, RAGSourceXml, RAGSourceDoc
from app.models.source import Source


engine = create_async_engine(f"sqlite+aiosqlite:///{CLIENT_DB_FILE}", echo=False)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)