from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.bot_user_message import BotUserMessage, MessageType

async def get_message_history(
        session: AsyncSession, chat_id: str, limit: int = 4, ttl_hours: int = 1) -> list[BotUserMessage]:
    
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    query = (
        select(BotUserMessage)
        .where(BotUserMessage.chat_id == chat_id, BotUserMessage.created_at >= time_threshold)
        .order_by(BotUserMessage.id.desc())
        .limit(limit)
    )
    result = await session.execute(query)
    messages = result.scalars().all()
    return messages[::-1]  # Возвращаем в порядке от старых к новым


async def add_bot_user_message(
        session: AsyncSession, chat_id: str, message_type: MessageType, text: str) -> Optional[BotUserMessage]:
    
    new_message = BotUserMessage(chat_id=chat_id, type=message_type, text=text)
    session.add(new_message)
    try:
        await session.commit()
        await session.refresh(new_message)
        return new_message
    except IntegrityError as e:
        print(f"Ошибка при добавлении сообщения: {e}")
        await session.rollback()
        return None