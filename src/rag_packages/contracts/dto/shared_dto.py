from pydantic import BaseModel
from typing import Any
from pydantic_settings import SettingsConfigDict


class BaseDTO(BaseModel):
    model_config = SettingsConfigDict(from_attributes=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)


class APIResponse(BaseDTO):
    success: bool
    data: dict | None = None
    message: str | None = None


class APIListResponse(APIResponse):
    prev: str | None = None
    next: str | None = None
    count: int | None = None
    data: list | None = None


class ErrorDetails(BaseDTO):
    message: str
    code: str | None = None
    reason: str | None = None
    details: dict | list[dict] | None = None


class APIErrorResponse(APIResponse):
    error: ErrorDetails | None = None
