from fastapi import APIRouter, Depends
from libs.common.auth import require_user
from libs.common.schemas import CurrentUser

router = APIRouter()


@router.get("/me")
def me(user: CurrentUser = Depends(require_user)):
    """Текущий пользователь и его права — заменяет то, что в desktop-версии
    расползалось по глобальным AppData.SetStocksRight/SetProviders (раздел 9)."""
    return user


# TODO: CRUD для управления пользователями (замена FormUsers.cs/EditUser.cs) —
# создание пользователя, назначение прав на склады/поставщиков, смена настроек
# (звук сканера, автостатус) — см. docs/RoboStorages_анализ_и_миграция_в_web.md.
# Ступенчатая авторизация (LoginPass.cs, числовые PIN-коды, раздел 9) НЕ переносится —
# заменяется обычными ролями (например, роль "accountant"/"analyst") на этом же токене.
