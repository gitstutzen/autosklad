from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
import os
import time

router = APIRouter()

JWT_SECRET = os.environ["JWT_SECRET"]


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    expires_in: int = 3600 * 8  # рабочая смена, не бессрочно как было в desktop


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    """Заменяет FormLogin.button1_Click. Ключевые отличия от desktop-версии
    (раздел 9 анализа):
      - bcrypt со случайной солью на пользователя, не SHA-256 с одной фиксированной
        солью, единой для всех пользователей;
      - при первом успешном логине после миграции — проверка по старой схеме
        и "ленивое" перехеширование в bcrypt (см. service.verify_and_maybe_rehash,
        TODO), чтобы не заставлять всех сбрасывать пароли одномоментно;
      - права (allowed_stock_ids/allowed_provider_ids) читаются из нормализованных
        таблиц user_stocks/user_providers, а не парсятся из строки-whitelist.
    """
    # TODO: заменить на реальный поход в БД (service.authenticate)
    raise HTTPException(501, "TODO: authenticate() — см. комментарий выше")


def _issue_token(user_id: int, login: str, allowed_stock_ids: list[int], allowed_provider_ids: list[int]) -> str:
    payload = {
        "user_id": user_id,
        "login": login,
        "allowed_stock_ids": allowed_stock_ids,
        "allowed_provider_ids": allowed_provider_ids,
        "exp": int(time.time()) + 3600 * 8,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
