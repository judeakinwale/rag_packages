from fastapi import Request, Depends, HTTPException, status
from .schema import AuthContext


def get_auth_context(request: Request) -> AuthContext:
    claims = getattr(request.state, "auth_claims", None)
    if claims is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication context",
        )

    return AuthContext(
        user_id=int(claims["sub"]),
        email=claims["email"],
        roles=claims.get("roles", []),
    )


# example usage in a FastAPI route
def get_current_user_id(auth_context: AuthContext = Depends(get_auth_context)) -> int:
    return auth_context.user_id
