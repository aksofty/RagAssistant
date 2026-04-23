from sqlalchemy import Text
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class BotCommand(Base):
    __tablename__ = 'bot_commands'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    command: Mapped[str] = mapped_column()
    text: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=True)