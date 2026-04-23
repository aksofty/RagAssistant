import json
import re
from typing import Any, Dict
from sqlalchemy.types import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.models.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    active: Mapped[bool] = mapped_column(default=True)
    url: Mapped[str] = mapped_column(String(255))
    meta_type: Mapped[str] = mapped_column(String(255))
    meta_sub_type: Mapped[str] = mapped_column(String(255))
    cache_time: Mapped[int] = mapped_column()
    settings: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    @validates('url')
    def validate_url(self, key, address):
        regex = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+'
        if not re.match(regex, address):
            raise ValueError("Некорректный формат URL")
        return address
    
    @validates("settings")
    def validate_settings(self, key, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except ValueError:
                raise ValueError("Поле settings должно содержать валидный JSON-строку или словарь")
        return value