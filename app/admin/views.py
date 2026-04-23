from aiofiles import os
from sqladmin import ModelView, BaseView, expose

from app import BASE_DIR
from app.cruds.bot_user_message import get_message_history
from app.database import AsyncSessionLocal
from app.models.bot_user_message import BotUserMessage
from app.models.bot_command import BotCommand
from app.models.bot_user import BotUser
from markupsafe import Markup
from starlette.responses import RedirectResponse

from app.models.source import Source
from app.utils.common import clean_response_for_chat

class SourceAdmin(ModelView, model=Source):
    name_plural = name = "Источники знаний"
    icon = "fa-solid fa-brain"
    column_list = [Source.active, Source.id, Source.url, Source.meta_type, Source.meta_sub_type, Source.cache_time, Source.settings]
    column_labels = {
        Source.active: "Активность",
        Source.id: "id",
        Source.url: "Ссылка",
        Source.meta_type: "Тип",
        Source.meta_sub_type: "Подтип",
        Source.cache_time: "Время актуальности",
        Source.settings: "Настройки"
    }
    #form_columns = [BotCommand.is_active, BotCommand.command, BotCommand.text]
    form_args = {
        "settings": {  
            "render_kw": {
                "class": "form-control", 
                "rows": 15,              
                "style": "font-family: 'Courier New', monospace; background-color: #f8f9fa;",
                "placeholder": '{"theme": "dark", "notifications": true}'
            }
        }
    }


class BotUserAdmin(ModelView, model=BotUser):
    name_plural = name = "Сессии пользователей"
    icon = "fa-solid fa-users"
    can_create = False
    can_export = False

    column_list = [BotUser.chat_id, BotUser.name]
    form_columns = [BotUser.chat_id, BotUser.name]


class BotUserMessageAdmin(ModelView, model=BotUserMessage):
    name_plural = name = "История сообщений"
    icon = "fa-solid fa-comments"
    can_create = False
    can_export = False

    column_labels = {
        BotUserMessage.chat_id: "id чата",
        BotUserMessage.type: "тип сообщения",
        BotUserMessage.text: "текст сообщения",
        BotUserMessage.created_at: "время создания"
    }
    column_list = [BotUserMessage.id, BotUserMessage.created_at, BotUserMessage.chat_id, BotUserMessage.type, BotUserMessage.text]
    form_columns = [BotUserMessage.chat_id, BotUserMessage.type, BotUserMessage.text]
    column_searchable_list = [BotUserMessage.type, BotUserMessage.chat_id]
    
    column_sortable_list = [BotUserMessage.id]
    column_default_sort = ("id", True)

    column_formatters = {
        "text": lambda m, a: Markup(m.text.replace("\n\n", "<br>").replace("\n", "<br>")) if m.text else ""
    }




class PromptEditorAdmin(BaseView):
    name = "Редактор промпта"
    icon = "fa-solid fa-file-code"

    @expose("/edit-prompt", methods=["GET", "POST"])
    async def edit_prompt(self, request):
        PROMPT_FILE_PATH = f"{BASE_DIR}/PROMPT.md"
        if request.method == "POST":
            form = await request.form()
            new_content = form.get("content")
            
            # Сохраняем изменения в файл
            with open(PROMPT_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            # Можно добавить редирект или сообщение об успехе
            return RedirectResponse(request.url_for("admin:edit_prompt"), status_code=303)

        # Читаем текущее содержимое файла
        content = ""
        if await os.path.exists(PROMPT_FILE_PATH):
            with open(PROMPT_FILE_PATH, "r", encoding="utf-8") as f:
                content = f.read()

        return await self.templates.TemplateResponse(
            request,
            "admin/prompt_editor.html",
            context={"content": content}
        )
    
class ChatAssistantAdmin(BaseView):
    name = "Ассистент в чате"
    icon = "fa-solid fa-comment"

    @expose("/chat", methods=["GET"])
    async def chat_page(self, request):
        content = ""

        async with AsyncSessionLocal() as session:
            history = await get_message_history(session, chat_id=123456789, limit=10)
        if history:
            for message in history:
                text = message.text.split("Вопрос:")
                text_clean = text[1] if len(text) > 1 else message.text
                text_clean = clean_response_for_chat(text_clean)

                content += f"""<div class="message {"user" if message.type.name == "HUMAN" else "bot"}">{text_clean}</div>"""
        else:
            content = "<div class=\"message bot\">Привет! Чем я могу помочь?</div>"

        return await self.templates.TemplateResponse(
            request, 
            "admin/chat_assistant.html",
            context={"content": Markup(content)}
        )