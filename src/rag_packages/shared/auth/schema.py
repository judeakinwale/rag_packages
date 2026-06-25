from typing import Any
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict


class BaseSchema(BaseModel):
    model_config = SettingsConfigDict(from_attributes=True)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        kwargs.setdefault("exclude_unset", True)
        kwargs.setdefault("exclude_none", True)
        return super().model_dump(**kwargs)


class AuthContext(BaseSchema):
    user_id: int
    email: str
    roles: list[str]


class TokenPayload(BaseSchema):
    sub: str
    email: str
    roles: list[str] | None = []
    exp: int | None = None # JWT exp is stored as a Unix timestamp in seconds.


class JWTConfig(BaseSchema):
    secret: str
    algorithm: str | None = "HS256"
    token_url: str | None = "/api/v1/auth/token"
    token_expires_in: int | None = 3600 * 24  # in seconds, default is one day
