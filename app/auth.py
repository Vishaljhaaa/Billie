from __future__ import annotations

from fastapi import Header, HTTPException, status

from app.config import AuthConfig


class AuthManager:
    def __init__(self, config: AuthConfig) -> None:
        self.config = config

    def require_api_key(self, x_api_key: str | None = Header(default=None)) -> None:
        if not self.config.api_key:
            return
        if x_api_key != self.config.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing API key.",
            )

    def require_admin_key(self, x_admin_key: str | None = Header(default=None)) -> None:
        if not self.config.admin_key:
            return
        if x_admin_key != self.config.admin_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing admin key.",
            )
