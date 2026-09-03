import logging

from fastapi import FastAPI
from app.routers import statuses
from libs.common.read_only import is_read_only

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

app = FastAPI(
    title="stutzen-integration",
    description=(
        "ЕДИНСТВЕННЫЙ сервис, которому разрешено вызывать api1c (catalog.stutzen.ru) "
        "и TradeSoft REST API v1 (www.stutzen.ru/api/v1). Ни один другой сервис "
        "не должен знать URL или токены Stutzen напрямую — только через HTTP-контракт "
        "этого сервиса. Это даёт возможность заменить механизм синхронизации "
        "(api1c <-> официальный api/v1/order-positions), не трогая warehouse."
    ),
)

app.include_router(statuses.router, prefix="/stutzen", tags=["stutzen"])


@app.on_event("startup")
def announce_mode() -> None:
    """Режим работы печатается при старте, чтобы он был виден в логах контейнера,
    а не выяснялся опытным путём. У проекта нет тестового контура Stutzen —
    важно всегда знать, может ли этот процесс менять боевые данные."""
    if is_read_only():
        logging.getLogger("startup").info(
            "Режим ТОЛЬКО ЧТЕНИЕ: запись в Stutzen заблокирована (STUTZEN_READ_ONLY)"
        )
    else:
        logging.getLogger("startup").warning(
            "ВНИМАНИЕ: запись в Stutzen РАЗРЕШЕНА. Этот процесс может менять "
            "статусы реальных заказов."
        )


@app.get("/health")
def health():
    return {"status": "ok", "read_only": is_read_only()}
