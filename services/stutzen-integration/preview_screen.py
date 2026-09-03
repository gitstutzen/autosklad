"""
Экран приёмки — предварительный просмотр.

Зачем: показать кладовщикам и спросить «похоже на то, чем вы пользуетесь?».
Обратная связь от людей сейчас важнее следующей технической детали.

ЧЕМ ЭТО НЕ ЯВЛЯЕТСЯ. Это не рабочий экран, а витрина поверх настоящих данных:
  - без входа по паролю (боевой экран будет требовать логин);
  - слушает только localhost, снаружи недоступен;
  - задания берёт из локального зеркала full_sync.db, а не из Postgres;
  - только чтение, ничего изменить нельзя.

Зато логика вся настоящая: те же функции, что и в сервисе, те же статусы,
тот же способ запрашивать позиции. Показанное на экране — то, что реально
отдаст система.

Запуск (из папки services/stutzen-integration, окружение активировано):

    pip install fastapi uvicorn
    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python preview_screen.py

Затем откройте http://127.0.0.1:8080

Нужен файл full_sync.db — создаётся скриптом check_full_sync.py.
Без ключа API список заданий работает, позиции внутри задания — нет.
"""
import os
import sys

os.environ["STUTZEN_READ_ONLY"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///full_sync.db")
os.environ.setdefault("JWT_SECRET", "not-used-here")
os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "not-used-here")
os.environ.setdefault("API1C_BASE_URL", "https://example.invalid/api1c")
os.environ.setdefault("API1C_API_KEY", "not-set")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import StockTaskMirror
from app import stock_tasks_service as svc
from app.stock_tasks import ACTIVE_STATUSES, STOCK_TASK_STATUS_NAMES
from app.api1c_client import Api1cClient
from app.task_positions import parse_positions

DB_FILE = "full_sync.db"
if not Path(DB_FILE).exists():
    print(f"Не найден {DB_FILE}. Сначала запустите: python check_full_sync.py")
    raise SystemExit(1)

engine = create_engine(f"sqlite:///{DB_FILE}")
SessionLocal = sessionmaker(bind=engine)
ACTIVE_VALUES = [int(s) for s in ACTIVE_STATUSES]

app = FastAPI(title="Приёмка — предварительный просмотр")


@app.get("/api/stocks")
def stocks():
    """Склады, на которых есть активные приходы."""
    with SessionLocal() as session:
        rows = session.execute(
            select(StockTaskMirror.stock_id, func.count())
            .where(StockTaskMirror.status.in_(ACTIVE_VALUES))
            .group_by(StockTaskMirror.stock_id)
            .order_by(func.count().desc())
        ).all()
    return [{"stock_id": stock_id, "count": count} for stock_id, count in rows]


@app.get("/api/tasks")
def tasks(stock_id: int, limit: int = 200):
    with SessionLocal() as session:
        rows = svc.list_tasks(session, stock_id=stock_id, limit=limit)
        return [
            {
                "id": t.id,
                "receipt_number": t.receipt_number,
                "document_number": t.document_number,
                "provider": t.provider,
                "amount": t.amount,
                "status": t.status,
                "status_name": STOCK_TASK_STATUS_NAMES.get(t.status, "неизвестен"),
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "login": t.login,
            }
            for t in rows
        ]


@app.get("/api/tasks/{task_id}/positions")
def positions(task_id: int):
    with SessionLocal() as session:
        task = svc.get_task(session, task_id)
    if task is None:
        raise HTTPException(404, "Приход не найден")
    if task.document_number is None:
        raise HTTPException(422, "У прихода нет номера документа — позиции не запросить")

    if os.environ.get("API1C_API_KEY") in (None, "", "not-set"):
        raise HTTPException(503, "Не задан ключ API — позиции недоступны")

    payload = Api1cClient().get_stock_task_positions(document_number=task.document_number)
    if not isinstance(payload, list):
        raise HTTPException(502, "Stutzen вернул неожиданный ответ")

    return [
        {
            "article": p.article,
            "manufacturer": p.manufacturer,
            "name": p.name,
            "quantity": p.quantity,
            "quantity_fact": p.quantity_fact,
            "remaining": p.remaining,
            "status": p.status_position,
            "is_done": p.is_done,
            "trade_point": p.trade_point,
            "number_customer": p.number_customer,
        }
        for p in parse_positions(payload)
    ]


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "preview_screen.html").read_text(encoding="utf-8")


if __name__ == "__main__":
    import uvicorn

    print("Экран открывается на http://127.0.0.1:8080")
    print("Только чтение. Снаружи недоступен.\n")
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="warning")
