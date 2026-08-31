from fastapi import FastAPI
from app.routers import login, users

app = FastAPI(
    title="auth",
    description=(
        "Логин и права доступа. Заменяет строки-whitelist (SetLoginsLeft/SetProviders/"
        "SetStocksRight из таблицы _users, раздел 9 анализа) нормализованной моделью "
        "пользователь-склад/пользователь-поставщик, и захардкоженные PIN-коды "
        "ступенчатой авторизации (раздел 9) — обычными ролями."
    ),
)

app.include_router(login.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/auth/users", tags=["users"])


@app.get("/health")
def health():
    return {"status": "ok"}
