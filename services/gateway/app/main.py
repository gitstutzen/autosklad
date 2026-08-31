"""
BFF — единственный сервис, на который ходит фронтенд. Проксирует/агрегирует вызовы
к остальным сервисам, ничего не решает сам (толстая логика — только в warehouse/
marking/print/stutzen-integration/auth, gateway — тонкий слой маршрутизации).

Пример: экран приёмки после сохранения позиции может захотеть одним ответом
получить и новый статус, и ссылку на этикетку — gateway агрегирует эти два вызова
(warehouse.accept + print.render_sticker), фронтенду не нужно знать про пять сервисов.
"""
import os
import httpx
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser

app = FastAPI(title="gateway")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("FRONTEND_ORIGIN", "http://localhost:5173")],
    allow_methods=["*"],
    allow_headers=["*"],
)

WAREHOUSE_URL = os.environ["WAREHOUSE_URL"]
MARKING_URL = os.environ["MARKING_URL"]
PRINT_URL = os.environ["PRINT_URL"]
AUTH_URL = os.environ["AUTH_URL"]


@app.get("/health")
def health():
    return {"status": "ok"}


# TODO: маршруты-прокси к каждому сервису + пара агрегирующих эндпоинтов
# (например, POST /positions/{id}/accept-and-print, объединяющий warehouse.accept
# и print.render_sticker одним сетевым запросом с фронтенда — важно для требования
# "быстро работать" на слабом Wi-Fi склада, раздел README про причины архитектуры).
