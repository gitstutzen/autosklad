from fastapi import FastAPI, Depends
from pydantic import BaseModel

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser

app = FastAPI(
    title="print",
    description=(
        "Рендер этикетки в PDF/PNG — портирует PrintStickerService (раздел 9 анализа: "
        "единственный класс в desktop-версии, спроектированный без обращения к "
        "глобальным AppData/AppPosition, поэтому переносится почти без изменений)."
    ),
)


class StickerRequest(BaseModel):
    article: str
    manufacturer: str
    client_ref: str | None = None
    trade_point_short_name: str | None = None
    storage_cell: str | None = None
    comment: str | None = None
    honest_sign_code: str | None = None


@app.post("/print/sticker")
def render_sticker(body: StickerRequest, user: CurrentUser = Depends(require_user)):
    """TODO: рендер через ReportLab/Pillow (замена GDI+ из PrintStickerService.Render),
    сохранить в объектное хранилище, вернуть ссылку — печатает уже локальный
    принт-агент на складе (см. README, раздел про печать), не браузер."""
    raise NotImplementedError


@app.get("/health")
def health():
    return {"status": "ok"}
