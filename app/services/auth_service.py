"""Login / refresh flows built on top of UserService."""

import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import UnauthorizedError
from app.core.security import create_token, decode_token, verify_password
from app.models.user import User
from app.schemas.auth import TokenPair
from app.services.user_service import UserService


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserService(db)

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.users.get_by_email(email)
        # Same error for "unknown email" and "wrong password" - no user enumeration.
        if user is None or not verify_password(password, user.hashed_password):
            raise UnauthorizedError("Incorrect email or password")
        if not user.is_active:
            raise UnauthorizedError("Inactive user")
        return user

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self.authenticate(email, password)
        return self._issue_tokens(str(user.id))

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            payload = decode_token(refresh_token)
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Invalid refresh token") from exc

        if payload.get("type") != "refresh":
            raise UnauthorizedError("Invalid token type")
        return self._issue_tokens(str(payload["sub"]))

    @staticmethod
    def _issue_tokens(subject: str) -> TokenPair:
        return TokenPair(
            access_token=create_token(subject, "access"),
            refresh_token=create_token(subject, "refresh"),
        )
