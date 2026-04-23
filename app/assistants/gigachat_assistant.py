import base64
import os
from typing import List, Dict
import uuid
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_gigachat import GigaChat, GigaChatEmbeddings
from langchain_community.vectorstores import FAISS
from loguru import logger
from app.cruds.bot_user import AsyncSessionLocal
from app.cruds.bot_user_message import add_bot_user_message, get_message_history
from app.models.bot_user_message import MessageType
from app.tools.tools import ALL_TOOLS, TOOLS_MAP
from app.utils.common import get_file_type, get_rag_cache_path
from app.utils.document_processor import DocumentProcessor
from app import BASE_DIR
from langchain_core.messages.base import BaseMessage



class GigaChatAssistant:
    def __init__(
            self, 
            client_id: str, client_secret: str, scope: str = "GIGACHAT_API_PERS", model="GigaChat", temperature=0.1,
            system_prompt_path: str = None,
            rag_sources: List[Dict[str, str]] = None,
            cache_dir: str = None,
            faiss_dir: str = None
        ):
        
        self.cache_dir = cache_dir
        self.faiss_dir = faiss_dir
        self.rag_sources = rag_sources
        self.system_prompt_path = system_prompt_path

        base64_auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        self.rquid = str(uuid.uuid4())


        self.chat = GigaChat(
            credentials=base64_auth, 
            model=model,
            temperature=temperature,  # Минимальное значение для строгости ответов
            verify_ssl_certs=False,
            scope=scope
        )

        self.model_with_tools = self.chat.bind_tools(ALL_TOOLS)

        self.embeddings = GigaChatEmbeddings(
            credentials=base64_auth, 
            verify_ssl_certs=False,
            scope=scope 
        )
        self.vector_store = None

    def _needs_update(self, file_path: str, index_folder: str) -> bool:
        """Проверяет, нужно ли пересобирать индекс для конкретного файла."""

        # Если индекс не существует, то нужно создать
        faiss_file = os.path.join(index_folder, "index.faiss")
        if not os.path.exists(faiss_file):
            return True
            
        index_mtime = os.path.getmtime(faiss_file)
        file_mtime = os.path.getmtime(file_path)
        # Если файл на диске новее, чем индекс
        if file_mtime > index_mtime:
            return True
            
        return False
    

    async def sync_indices(self):
        """Проверяет каждый файл и собирает общую базу в памяти."""
        logger.info(f"Синхронизируем векторную базу")

        all_stores = []

        for source in self.rag_sources:
            path = get_rag_cache_path(source=source, cache_dir=self.cache_dir)    
            #doc_type = get_file_type(path)

            # Уникальное имя папки для индекса этого файла
            file_hash = base64.b64encode(os.path.basename(path).encode()).decode()[:50]
            index_folder = os.path.join(self.faiss_dir, f"idx_{file_hash}")

            if self._needs_update(path, index_folder):
                logger.info(f"Файл {path} требует переиндексации...")
                processor = DocumentProcessor(source=source)
                docs = await processor.process_document()
                if docs:
                    store = await FAISS.afrom_documents(docs, self.embeddings)
                    store.save_local(index_folder)
                    all_stores.append(store)
                    logger.info(f"Файл {path} обновлен.")
            else:
                logger.info(f"Используем кеш для {path}")
                store = FAISS.load_local(index_folder, self.embeddings, allow_dangerous_deserialization=True)
                all_stores.append(store)

        # Объединяем все части в одну общую базу для поиска
        if all_stores:
            self.vector_store = all_stores[0]
            for next_store in all_stores[1:]:
                self.vector_store.merge_from(next_store)
            logger.info("Векторная база собрана")
        else:
            logger.warning("Нет данных для векторной базы")


    #async def ask(self, query: str, history: List[BaseMessage] = [], max_asimilarity: int = 5, min_score: float = 200) -> str:
    async def ask(self, query: str, chat_id: int, max_asimilarity: int = 5, min_score: float = 300) -> str:
        """Поиск контекста и генерация ответа."""

        history = await self._get_user_message_history(chat_id=chat_id)
        
        context = await self._get_context(
            query=query, max_asimilarity=max_asimilarity, min_score=min_score)

        system_prompt = await self._load_prompt(file_path=self.system_prompt_path)
        system_prompt = system_prompt.replace("{context}", context)
        
        system_message = SystemMessage(content=f"""{system_prompt}""")
        messages = [system_message] + history + [HumanMessage(content=query)]
        
        # Запускаем модель с инструментами
        response_with_tools, tool_messages = await self._run_model_with_tools(messages=messages)
        if response_with_tools:
            async with AsyncSessionLocal() as session:
                #await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.HUMAN, text=context_query)
                await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.HUMAN, text=query)
                await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.AI, text=response_with_tools)
            return response_with_tools
        
        # Если конечный ответ не получен, то генерируем ответ без инструментов
        final_step = await self.chat.ainvoke(
            tool_messages + [HumanMessage(content="""У тебя больше нет попыток вызова функций. Ответь пользователю прямо сейчас на основе полученной информации.""")])
        
        async with AsyncSessionLocal() as session:
            await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.HUMAN, text=query)
            await add_bot_user_message(session, chat_id=chat_id, message_type=MessageType.AI, text=final_step.content)
        
        return final_step.content


    async def _get_context(self, query: str, max_asimilarity: int, min_score: float):
        docs_with_scores = await self.vector_store.asimilarity_search_with_score(query, k=max_asimilarity)
        # Если score слишком большой (плохое совпадение), не даем этот кусок модели
        context = ""

        first_doc_skip = True

        for doc, score in docs_with_scores:
            logger.info(f"Найдено совпадение векторов в документе {doc.metadata['source']}. Вес: {score}")
            
            if doc.metadata['type'] == 'Каталог':
                first_doc_skip = False    
            
            if score > min_score and not first_doc_skip: 
                break

            first_doc_skip = False

            metadata_extra = []
            if 'id' in doc.metadata:
                metadata_extra.append(f"id товара в магазине: {doc.metadata['id']}")

            if 'link' in doc.metadata:
                metadata_extra.append(f"Ссылка: {doc.metadata['link']}")
    
            if 'image' in doc.metadata:
                metadata_extra.append(f"Фото: {doc.metadata['image']}")       

            '''if 'links' in doc.metadata:
                metadata_extra.append(f"Дополнительные ссылки: {', '.join(doc.metadata['links'])}")'''

            doc_type_sting = f"Тип: {doc.metadata['type']}"
            doc_type_sting += f". Раздел: {doc.metadata['sub_type']}" if doc.metadata.get('sub_type', None) else ""

            doc_string = f"--- ИСТОЧНИК: {doc.metadata['source']} ({doc_type_sting}) ---\n"
            doc_string += f"СОДЕРЖАНИЕ: {doc.page_content}. \n{'. '.join(metadata_extra)}\n\n"

            context += doc_string

        return context  
        
    async def _run_model_with_tools(self, messages: List[BaseMessage], iter_nums: int = 2):

        tool_messages = messages


        # Ограничиваем 2 итерациями, чтобы не зациклиться
        for i in range(iter_nums):
            # Запрос к модели c tools
            response = await self.model_with_tools.ainvoke(tool_messages)
            
            # Если инструментов вызывать не нужно — это финальный ответ
            if not response.tool_calls:
                return response.content, []

            # Если модель хочет вызвать инструменты, добавляем её запрос в историю
            tool_messages.append(response)

            # Обрабатываем каждый вызов инструмента
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                tool_to_call = TOOLS_MAP.get(tool_name)
                
                if tool_to_call:
                    # Извлекаем аргументы, которые подготовила модель
                    args = tool_call["args"]
                    
                    # Специальная обработка: добавляем chat_id вручную, 
                    # если функция его ожидает (для отправки в ТГ)
                    #if "chat_id" in args or tool_name == "send_product_photo":
                        #args["chat_id"] = chat_id

                    logger.info(f"Вызов {tool_name} с аргументами {args}")
                    
                    # Выполняем инструмент
                    result = await tool_to_call.ainvoke(args)
                    
                    # Передаем результат выполнения обратно модели
                    tool_messages.append(ToolMessage(
                        content=str(result), 
                        tool_call_id=tool_call["id"]
                    ))
                else:
                    tool_messages.append(ToolMessage(
                        content="Ошибка: Инструмент не найден.", 
                        tool_call_id=tool_call["id"]
                    ))

        return None, tool_messages
    
    async def _get_user_message_history(self, chat_id: int, limit: int = 5) -> List[BaseMessage]:
        """Получение истории сообщений для конкретного пользователя из базы данных."""
        async with AsyncSessionLocal() as session:
            message_history = await get_message_history(session, chat_id=chat_id, limit=limit)
            history = []
            for message in message_history:
                #print(message.text)
                if message.type == MessageType.HUMAN:
                    history.append(HumanMessage(content=message.text))
                elif message.type == MessageType.AI:
                    history.append(AIMessage(content=message.text))
                elif message.type == MessageType.TOOL:
                    history.append(ToolMessage(content=message.text))
                else:
                    history.append(SystemMessage(content=message.text))
            return history
    
    async def _load_prompt(self, file_path: str = None) -> str:
        if file_path is None:
            file_path = os.path.join(f"{BASE_DIR}", 'PROMPT.md')



        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
