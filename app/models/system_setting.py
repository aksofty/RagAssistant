from sqlalchemy.types import String
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class SystemSetting(Base):
    __tablename__ = 'system_settings'

    id: Mapped[int] = mapped_column(primary_key=True) # Технический ID
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False) # Уникальный ключ
    value: Mapped[str] = mapped_column(String(1024), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), nullable=True)