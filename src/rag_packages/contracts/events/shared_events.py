from pydantic import BaseModel
from typing import Any
from pydantic_settings import SettingsConfigDict


class BaseEvent(BaseModel):
    model_config = SettingsConfigDict(from_attributes=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)

    def model_dump_json(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump_json(**kwargs)


class DLQEvent(BaseEvent):
    original_topic: str
    partition: int
    offset: int
    timestamp: int
    key: Any | None = None
    payload: Any | BaseEvent
    error: str | None = None
