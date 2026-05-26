from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from jwt import PyJWTError

from app.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> None:
    settings = get_settings()
    if not settings.enable_auth:
        return

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization token is required")

    try:
        jwt.decode(credentials.credentials, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid authorization token") from exc
