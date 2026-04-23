from contextlib import asynccontextmanager
from fastapi import FastAPI
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



@asynccontextmanager
async def lifespan(app: FastAPI):
    
    await init_db()


    RAG_SOURCES = [
        {
            "url": "https://miniliner.ru/yml/", 
            "meta_type": "catalog",
            "meta_sub_type": "civil_aircraft",
            "item_tag": "offer"
        },
        {
            "url": "https://miniliner.ru/feedback/", 
            "meta_type": "general_info",
            "meta_sub_type": "contacts",
            "selector": {"class_": "body"}
        },
        {
            "url": "https://miniliner.ru/payment/", 
            "meta_type": "general_info",
            "meta_sub_type": "payments",
            "selector": {"class_": "body"}
        },
        {
            "url": "https://miniliner.ru/delivery/", 
            "meta_type": "general_info",
            "meta_sub_type": "delivery",
            "selector": {"class_": "body"}
        }
    ]

    
    RAG_SOURCES = [
        {
            "url": "https://miniliner.ru/yml/", 
            "meta_type": "Каталог",
            "meta_sub_type": "Гражданские модели",
            "item_tag": "offer"
        },
        {
            "url": "https://aviadivision.ru/yml/", 
            "meta_type": "Каталог",
            "meta_sub_type": "Военные модели",
            "item_tag": "offer"
        },
        {
            "url": "https://miniliner.ru/bot/contacts.txt", 
            "meta_type": "Общая информация",
            "meta_sub_type": "Контакты"
        },
        {
            "url": "https://miniliner.ru/bot/payments.txt", 
            "meta_type": "Общая информация",
            "meta_sub_type": "Оплата"
        },
        {
            "url": "https://miniliner.ru/bot/delivery.txt", 
            "meta_type": "Общая информация",
            "meta_sub_type": "Доставка"
        },
        {
            "url": "https://miniliner.ru/bot/discount.txt", 
            "meta_type": "Общая информация",
            "meta_sub_type": "бонусная программа"
        }
    ]

    rag_sources = []
    async with AsyncSessionLocal() as session:
        db_sources = await get_sources(session=session)
        for db_source in db_sources:
            db_sources = SourceRead.model_validate(db_source)
            source = db_sources.model_dump()
            rag_sources.append(source)
            #tag = source['settings'].get('item_tag', 'no')
            #selector = source['settings'].get('selector', 'no')
            file_path = get_rag_cache_path(source=source, cache_dir=CLIENT_CACHE_DIR)
            try:
                await HTTPDownloader(url=source["url"], file_path=file_path).run() 
            except Exception as e:
                print(f"Ошибка при загрузке {source.get('url')}: {e}")



    
    assistant = GigaChatAssistant(
        client_id=Config.GIGACHAT_CLIENT_ID, 
        client_secret=Config.GIGACHAT_CLIENT_SECRET, 
        rag_sources=rag_sources,
        faiss_dir=CLIENT_FAISS_DIR,
        cache_dir=CLIENT_CACHE_DIR,
        model="GigaChat-2",
        temperature=0.1
    )
    await assistant.sync_indices()

    #крон задача для синхронизации векторов (если обновились файлы данных)
    add_cron_task(assistant.sync_indices, cron_string="0 * * * *")
    await start_scheduler()

    app.state.assistant = assistant

    yield  # Здесь приложение работает
    
    # Код после yield выполняется ПРИ ВЫКЛЮЧЕНИИ
    print("Остановка приложения...")