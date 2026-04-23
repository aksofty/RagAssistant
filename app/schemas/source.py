import json

from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Any, Dict

class SourceBase(BaseModel):
    active: bool = True
    url: str = Field(..., max_length=255)
    meta_type: str = Field(..., max_length=255)
    meta_sub_type: str = Field(..., max_length=255)
    cache_time: int
    settings: Dict[str, Any] = Field(default_factory=dict)

class SourceRead(SourceBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

    @field_validator('settings', mode='before')
    @classmethod
    def transform_settings_to_dict(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {}
        return v or {}