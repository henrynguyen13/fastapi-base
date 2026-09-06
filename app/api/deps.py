"""Reusable FastAPI dependencies (DI container of a NestJS app, roughly)."""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService
from app.services.user_service import UserService

bearer_scheme = HTTPBearer(auto_error=False)

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_service(db: DbSession) -> UserService:
    return UserService(db)


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(db)


UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_current_user(
    users: UserServiceDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Missing bearer token")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid token") from exc

    if payload.get("type") != "access":
        raise UnauthorizedError("Invalid token type")

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Invalid token subject") from exc

    user = await users.get_by_id(user_id)
    if not user.is_active:
        raise UnauthorizedError("Inactive user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_current_superuser(user: CurrentUser) -> User:
    if not user.is_superuser:
        raise ForbiddenError()
    return user


CurrentSuperuser = Annotated[User, Depends(get_current_superuser)]
