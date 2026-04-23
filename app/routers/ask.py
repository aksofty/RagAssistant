from fastapi import APIRouter, Depends, Header, HTTPException, status, Request
from app.assistants.gigachat_assistant import GigaChatAssistant
from app.config import Config
from app.cruds.bot_user import get_add_bot_user
from app.database import AsyncSessionLocal
from typing import Annotated
from app.schemas.ask import AIQuestion, AIResponse
from app.utils.common import clean_response_for_chat

def get_ai_assistant(request: Request):
    return request.app.state.assistant

router = APIRouter(tags=["AI Assistant"])

@router.post("/ask", response_model=AIResponse)   
async def ask_node(
    request: AIQuestion,
    assistant: GigaChatAssistant = Depends(get_ai_assistant),
    fast_api_key: Annotated[str | None, Header()] = None
):
    
    # Проверка ключа авторизации
    if fast_api_key not in Config.FAST_API_SECRET_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    
    try:
        async with AsyncSessionLocal() as session:
            await get_add_bot_user(session, chat_id='123456789', name="Andrei")
            response = await assistant.ask(query=request.question, chat_id='123456789', max_asimilarity=5, min_score=310)

        
        return AIResponse(
                user_id=request.user_id,
                question=request.question,
                answer=clean_response_for_chat(response) if response else "Извините, какие то проблемы."
            )

    except Exception as e:
        print(f"Ошибка при обработке сообщения---: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{str(e)}"
        )