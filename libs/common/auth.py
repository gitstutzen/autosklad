"""
JWT-проверка, общая для всех сервисов кроме auth (который токены выпускает).
Каждый сервис подключает require_user как FastAPI-зависимость:

    from libs.common.auth import require_user
    @router.post("/positions/{id}/accept")
    def accept(id: int, user: CurrentUser = Depends(require_user)):
        ...

Права (allowed_stock_ids) проверяются в каждом сервисе на своих данных —
auth-сервис только удостоверяет личность и отдаёт список разрешённых складов/поставщиков,
он не решает, может ли конкретный пользователь принять конкретную позицию.
"""
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from .schemas import CurrentUser

JWT_SECRET = os.environ["JWT_SECRET"]  # общий на все сервисы, задаётся в .env
JWT_ALGORITHM = "HS256"

bearer_scheme = HTTPBearer()


def require_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Невалидный или истёкший токен")
    return CurrentUser(**payload)


def require_stock_access(stock_id: int):
    """Зависимость-фабрика: проверяет, что у пользователя есть доступ к конкретному складу.
    Заменяет строки-whitelist SetStocksRight из desktop-версии (раздел 9 анализа)
    нормальной проверкой списка ID."""
    def _check(user: CurrentUser = Depends(require_user)) -> CurrentUser:
        if stock_id not in user.allowed_stock_ids:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Нет доступа к этому складу")
        return user
    return _check
