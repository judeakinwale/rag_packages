# Auth Flow

This package provides the shared pieces for password verification, JWT issuing,
JWT decoding, and accessing the authenticated user inside FastAPI routes.

## 1. User signs in

The auth service receives the user's email and plain-text password from the
login endpoint.

```python
email = form_data.username
password = form_data.password
```

The auth service does not need to own the full user record. It only needs enough
data from the user service to verify credentials and build token claims.

```python
# user service -> auth service
user = {
    "id": 123,
    "email": "user@example.com",
    "password": "$argon2id$v=19$m=65536,t=3,p=4$...",  # hashed password
    "is_active": True,
    "roles": ["user"],
}
```

## 2. Auth service verifies credentials

The auth service fetches the credential record by email. If no user is found,
the account is inactive, or the Argon2 password check fails, the login request
is denied.

```python
from rag_packages.shared.auth.security import verify_password


user = await user_client.get_user_credentials_by_email(email)

if user is None:
    deny()

if not user["is_active"]:
    deny()

if not verify_password(password, user["password"]):
    deny()
```

`verify_password()` expects the plain password first and the stored hash second:

```python
verify_password(password, user["password"])
```

## 3. Auth service issues an access token

After credential verification succeeds, the auth service creates a JWT payload
and signs it with `JWTToken.issue_token()`.

```python
from rag_packages.shared.auth.schema import JWTConfig, TokenPayload
from rag_packages.shared.auth.token import JWTToken


jwt_token = JWTToken(
    JWTConfig(
        secret=settings.jwt_secret,
        token_url="/api/v1/auth/token",
        algorithm="HS256",
    )
)

access_token = jwt_token.issue_token(
    TokenPayload(
        sub=str(user["id"]),
        email=user["email"],
        roles=user.get("roles", ["user"]),
    )
)
```

If `exp` is not set on `TokenPayload`, `issue_token()` adds a default expiry of
one day from the issue time.

The login endpoint returns the token to the client.

```python
return {
    "access_token": access_token,
    "token_type": "bearer",
}
```

## 4. Client sends the bearer token

For authenticated requests, the client sends the JWT in the `Authorization`
header.

```http
Authorization: Bearer <access_token>
```

## 5. Application decodes the token and stores claims on the request

Before a protected route reads the authenticated user, the application must call
`JWTToken.inject_auth_claims(request)`. This uses FastAPI's
`OAuth2PasswordBearer` helper to read the bearer token, decodes it, and stores
the claims on `request.state.auth_claims`.

```python
from fastapi import Request


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    await jwt_token.inject_auth_claims(request)
    return await call_next(request)
```

After injection, the request state contains the token claims as a dictionary.

```python
request.state.auth_claims == {
    "sub": "123",
    "email": "user@example.com",
    "roles": ["user"],
    "exp": 1782400000,
}
```

`JWTToken.decode_token()` raises `UnauthorizedException("Invalid token")` when
the JWT is expired, malformed, signed with the wrong secret, or otherwise
invalid.

## 6. Route dependencies expose the authenticated user

Routes should use `get_auth_context()` when they need the authenticated user's
id, email, or roles.

```python
from fastapi import APIRouter, Depends
from rag_packages.shared.auth.dependencies import get_auth_context
from rag_packages.shared.auth.schema import AuthContext


router = APIRouter()


@router.get("/documents")
async def list_documents(
    auth_context: AuthContext = Depends(get_auth_context),
):
    return await document_service.list_for_user(auth_context.user_id)
```

`get_auth_context()` reads `request.state.auth_claims` and converts it into an
`AuthContext`.

```python
AuthContext(
    user_id=123,
    email="user@example.com",
    roles=["user"],
)
```

If `request.state.auth_claims` is missing, `get_auth_context()` raises a `401`
with `Missing authentication context`.

For routes that only need the user id, use `get_current_user_id()`.

```python
from fastapi import Depends
from rag_packages.shared.auth.dependencies import get_current_user_id


@router.get("/documents")
async def list_documents(
    user_id: int = Depends(get_current_user_id),
):
    return await document_service.list_for_user(user_id)
```

## End-to-end sequence

```text
1. Client posts email and password to the auth service.
2. Auth service asks the user service for credentials by email.
3. User service returns id, email, hashed password, active status, and roles.
4. Auth service verifies the plain password against the Argon2 hash.
5. Auth service issues a signed JWT with sub, email, roles, and exp.
6. Client stores the token and sends it as Authorization: Bearer <token>.
7. App calls JWTToken.inject_auth_claims(request) before protected route logic.
8. inject_auth_claims decodes the token and writes request.state.auth_claims.
9. Route dependency get_auth_context reads the claims.
10. Route receives AuthContext or user_id and uses it for scoped data access.
```
