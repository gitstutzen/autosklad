from fastapi import FastAPI
from app.routers import statuses

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


@app.get("/health")
def health():
    return {"status": "ok"}
