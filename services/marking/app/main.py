from fastapi import FastAPI, Depends
from pydantic import BaseModel
import httpx
import os

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser

app = FastAPI(
    title="marking",
    description=(
        "Проверка кодов маркировки 'Честный Знак' через государственный реестр. "
        "Единственный сервис, у которого есть CRPT_API_KEY — портирует "
        "FormManager.GetMark (раздел 11 анализа: прямой вызов "
        "https://cdn01.crpt.ru/api/v4/true-api/codes/check)."
    ),
)

CRPT_API_KEY = os.environ["CRPT_API_KEY"]
CRPT_BASE_URL = "https://cdn01.crpt.ru/api/v4/true-api"


class CheckMarkRequest(BaseModel):
    code: str


class CheckMarkResponse(BaseModel):
    valid: bool
    raw: dict


@app.post("/marking/check", response_model=CheckMarkResponse)
def check_mark(body: CheckMarkRequest, user: CurrentUser = Depends(require_user)):
    """Реальная проверка в государственном реестре (не путать с warehouse-сервисом,
    где сверяются уже ЗНАЕМЫЕ для позиции коды — здесь идёт внешний запрос)."""
    resp = httpx.post(
        f"{CRPT_BASE_URL}/codes/check",
        headers={"X-API-KEY": CRPT_API_KEY},
        json={"codes": [body.code]},
        timeout=10.0,
    )
    resp.raise_for_status()
    data = resp.json()
    return CheckMarkResponse(valid=bool(data.get("codes")), raw=data)


@app.get("/health")
def health():
    return {"status": "ok"}
