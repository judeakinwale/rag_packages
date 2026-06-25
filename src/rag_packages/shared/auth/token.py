import time
from fastapi import Request
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from .schema import TokenPayload, JWTConfig
from rag_packages.shared.exception.exception import UnauthorizedException


class JWTToken:
    def __init__(self, jwt_config: JWTConfig) -> None:
        self.jwt_config = jwt_config
        self.oauth2_scheme = OAuth2PasswordBearer(tokenUrl=jwt_config.token_url)
        # self.security = HTTPBearer()

    def issue_token(self, payload: TokenPayload) -> str:
        if payload.sub is None or payload.email is None:
            raise ValueError("Missing required fields in payload")

        if self.jwt_config.secret is None:
            raise ValueError("Missing required fields in self.jwt_config")

        if payload.exp is None:
            now = int(time.time())
            # one_day = 3600 * 24
            # jwt_expire = self.jwt_config.token_expires_in  or one_day
            jwt_expire = self.jwt_config.token_expires_in
            payload.exp = now + jwt_expire

        token = jwt.encode(
            payload.model_dump(),
            self.jwt_config.secret,
            algorithm=self.jwt_config.algorithm,
        )
        return token

    def decode_token(self, token: str) -> TokenPayload:
        try:
            payload = jwt.decode(
                token, self.jwt_config.secret, algorithms=[self.jwt_config.algorithm]
            )
            return TokenPayload(**payload)
        except JWTError as e:
            raise UnauthorizedException(message="Invalid token") from e

    # ? consider not raising exceptions if claims are injected by a triggered event and user validity is checked in route handler
    async def inject_auth_claims(self, request: Request) -> None:
        try:
            token = await self.oauth2_scheme(request)
            payload = self.decode_token(token)
            request.state.auth_claims = payload.model_dump()
        except Exception:
            raise
