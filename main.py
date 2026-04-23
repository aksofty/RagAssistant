from fastapi import FastAPI
from sqladmin import Admin
import uvicorn
from app import CLIENT_LOG_FILE
from app.admin.admin_auth import AdminAuth
from app.admin.views import BotUserAdmin, BotUserMessageAdmin, PromptEditorAdmin, ChatAssistantAdmin, SourceAdmin, SystemSettingAdmin
from app.config import Config
from app.lifespan import lifespan
from app.routers import ask
from app.database import engine
from loguru import logger

logger.remove()
logger.add(lambda msg: print(msg, end=""), level="DEBUG")
logger.add(CLIENT_LOG_FILE, rotation="1 MB")

app = FastAPI(lifespan=lifespan)
app.include_router(ask.router)

# Инициализация админки
authentication_backend = AdminAuth(secret_key=Config.ADMIN_SECRET_KEY)
admin = Admin(app, engine, authentication_backend=authentication_backend)

admin.add_view(ChatAssistantAdmin)
admin.add_view(PromptEditorAdmin)
admin.add_view(BotUserAdmin)
admin.add_view(BotUserMessageAdmin)
admin.add_view(SourceAdmin)
admin.add_view(SystemSettingAdmin)

    

def main():
    logger.info("Starting application...")
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8080, 
        reload=True,
        reload_includes=["*.md"]
    )

#reload_includes=["PROMPT.md"],
'''reload_includes=["*"],
        reload_excludes=[
            f"{BASE_DIR}/_data/RAG/vector_indices/",
            f"{BASE_DIR}/_logs/"
        ],'''

if __name__ == "__main__":
    main()

