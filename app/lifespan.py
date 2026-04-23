from contextlib import asynccontextmanager
from fastapi import FastAPI
from loguru import logger
from app import CLIENT_CACHE_DIR, CLIENT_FAISS_DIR
from app.assistants.gigachat_assistant import GigaChatAssistant
from app.config import Config
from app.cruds.source import get_sources
from app.database import AsyncSessionLocal, init_db
from app.scheduler import add_cron_task, start_scheduler
from app.schemas.source import SourceRead
from app.utils.common import get_rag_cache_path
from app.utils.document_processor import DocumentProcessor
from app.utils.http_downloader import HTTPDownloader

async def init_sources():

    rag_sources = []
    async with AsyncSessionLocal() as session:
        db_sources = await get_sources(session=session)
        for db_source in db_sources:
            source = SourceRead.model_validate(db_source).model_dump()
            file_path = get_rag_cache_path(source=source, cache_dir=CLIENT_CACHE_DIR)
            try:
                await HTTPDownloader(
                    url=source["url"], 
                    file_path=file_path, 
                    cache_hours=source["cache_time"]).run()
                
            except Exception as e:
                logger.error(f"Ошибка при загрузке {source.get('url')}: {e}")

            if source:    
                rag_sources.append(source)

    if rag_sources:
        logger.info("Источники данных подготовлены")
    else:
        logger.warning("Источники данных не найдены")
    return rag_sources


@asynccontextmanager
async def lifespan(app: FastAPI):

    await init_db() #инициализация базы данных
    rag_sources = await init_sources() #инициализация источников данных
    
    #инициализация ассистента
    assistant = GigaChatAssistant(
        client_id=Config.GIGACHAT_CLIENT_ID, 
        client_secret=Config.GIGACHAT_CLIENT_SECRET, 
        rag_sources=rag_sources,
        faiss_dir=CLIENT_FAISS_DIR,
        cache_dir=CLIENT_CACHE_DIR,
        model="GigaChat-2",
        temperature=0.1
    )
    await assistant.sync_indices() #синхронизация векторов

    #крон задача для синхронизации векторов (если обновилcя кеш источников)
    add_cron_task(assistant.sync_indices, cron_string="0 * * * *")
    await start_scheduler()

    app.state.assistant = assistant

    yield  # Здесь приложение работает
    
    # Код после yield выполняется ПРИ ВЫКЛЮЧЕНИИ
    print("Остановка приложения...")