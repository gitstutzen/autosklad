import os
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from libs.common.auth import require_user
from libs.common.schemas import CurrentUser
from app import stock_tasks_service as svc
from app import sync as sync_module
from app.api1c_client import Api1cClient
from app.task_positions import TaskPosition, parse_positions

router = APIRouter()

_engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = sessionmaker(bind=_engine)


def get_session():
    with SessionLocal() as session:
        yield session


class StockTaskOut(BaseModel):
    """Задание в виде, отдаваемом фронтенду.

    Почти все поля могут быть пустыми — это зеркало чужой системы с данными
    с 2017 года. Строгая модель здесь приводила бы к отказу отдать запись,
    у которой не заполнен, скажем, автор. Лучше показать приход без автора,
    чем не показать приход. Подробности — в app/stock_tasks.py, класс StockTask.
    """
    id: int
    receipt_number: int | None
    document_number: int | None
    created_at: str | None
    status: int | None
    stock_id: int | None
    provider: str | None
    amount: float | None
    login: str | None
    started_at: str | None
    finished_at: str | None
    comment: str | None
    comment_stock: str | None

    @classmethod
    def from_mirror(cls, task) -> "StockTaskOut":
        return cls(
            id=task.id,
            receipt_number=task.receipt_number,
            document_number=task.document_number,
            created_at=task.created_at.isoformat() if task.created_at else None,
            status=task.status,
            stock_id=task.stock_id,
            provider=task.provider,
            amount=task.amount,
            login=task.login,
            started_at=task.started_at.isoformat() if task.started_at else None,
            finished_at=task.finished_at.isoformat() if task.finished_at else None,
            comment=task.comment,
            comment_stock=task.comment_stock,
        )


# Названия статусов позиции — дословно из справочной таблицы
# PositionsStorageStatus боевой базы (прочитано 02.09.2026).
# В api1c этот справочник не отдаётся.
POSITION_STATUS_NAMES = {
    1: "Необработана",
    2: "Принята частично",
    3: "Принята",
    4: "Излишек",
    5: "Отсутствует",
    6: "Принято с разногласием",
}


class TaskPositionOut(BaseModel):
    """Позиция в виде, удобном для экрана кладовщика.

    Отличия от сырого ответа api1c: посчитан остаток, добавлен признак
    завершённости и человекочитаемое название статуса — чтобы фронтенду
    не пришлось знать про числовые коды и повторять логику расчёта.
    """
    article: str
    article_new: str | None
    manufacturer: str
    name: str
    quantity: int
    quantity_fact: int
    remaining: int
    price: float
    price_total: float
    status_position: int
    status_name: str
    is_done: bool
    ref_stutzen: int
    ref_provider: int
    trade_point: int
    number_customer: int
    comment: str | None

    @classmethod
    def from_position(cls, p: TaskPosition) -> "TaskPositionOut":
        return cls(
            article=p.article,
            article_new=p.article_new or None,
            manufacturer=p.manufacturer,
            name=p.name,
            quantity=p.quantity,
            quantity_fact=p.quantity_fact,
            remaining=p.remaining,
            price=p.price,
            price_total=p.price_total,
            status_position=p.status_position,
            status_name=POSITION_STATUS_NAMES.get(p.status_position, "Неизвестный статус"),
            is_done=p.is_done,
            ref_stutzen=p.ref_stutzen,
            ref_provider=p.ref_provider,
            trade_point=p.trade_point,
            number_customer=p.number_customer,
            comment=p.comment,
        )



@router.get("/stock-tasks", response_model=list[StockTaskOut])
def list_stock_tasks(
    stock_id: int = Query(..., description="Номер склада"),
    only_unfinished: bool = Query(True, description="Только незакрытые задания"),
    provider: str | None = Query(None, description="Поиск по названию поставщика"),
    created_from: date | None = Query(None, description="Создано не раньше"),
    created_to: date | None = Query(None, description="Создано не позже"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Список складских заданий.

    Читается из локального зеркала, поэтому доступны фильтры и постраничность,
    которых нет в api1c, и — главное — старые незакрытые задания остаются
    видны сколько угодно долго (например, приход, по которому часть позиций
    ещё не поступила от поставщика).
    """
    if stock_id not in user.allowed_stock_ids:
        raise HTTPException(403, "Нет доступа к этому складу")

    tasks = svc.list_tasks(
        session,
        stock_id=stock_id,
        only_unfinished=only_unfinished,
        provider_contains=provider,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    return [StockTaskOut.from_mirror(t) for t in tasks]


@router.get("/stock-tasks/{task_id}", response_model=StockTaskOut)
def get_stock_task(
    task_id: int,
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
):
    task = svc.get_task(session, task_id)
    if task is None:
        raise HTTPException(404, "Задание не найдено в локальном зеркале")
    if task.stock_id not in user.allowed_stock_ids:
        raise HTTPException(403, "Нет доступа к этому складу")
    return StockTaskOut.from_mirror(task)


@router.get("/stock-tasks/{task_id}/positions", response_model=list[TaskPositionOut])
def get_task_positions(
    task_id: int,
    only_open: bool = Query(False, description="Только позиции, требующие работы"),
    user: CurrentUser = Depends(require_user),
    session: Session = Depends(get_session),
):
    """Позиции внутри задания — то, что кладовщик видит, открыв приход.

    Позиции читаются напрямую из api1c, а не из зеркала: они меняются в ходе
    приёмки постоянно, и показывать здесь устаревший срез нельзя.

    Про параметр запроса к api1c: метод ждёт `dcc_id`, и значение туда идёт
    из поля `document_number` ЗАДАНИЯ. Именно поэтому эндпоинт принимает id
    задания, сам достаёт задание из зеркала и берёт номер документа оттуда —
    клиент не должен знать про эту особенность и не может ошибиться.
    При неверном значении api1c молча вернул бы пустой список без ошибки.
    """
    task = svc.get_task(session, task_id)
    if task is None:
        raise HTTPException(404, "Задание не найдено в локальном зеркале")
    if task.stock_id not in user.allowed_stock_ids:
        raise HTTPException(403, "Нет доступа к этому складу")

    payload = Api1cClient().get_stock_task_positions(document_number=task.document_number)
    if not isinstance(payload, list):
        raise HTTPException(502, "Неожиданный ответ Stutzen при запросе позиций")

    positions = parse_positions(payload)
    if only_open:
        positions = [p for p in positions if not p.is_done]
    return [TaskPositionOut.from_position(p) for p in positions]


@router.get("/sync-status")
def sync_status(session: Session = Depends(get_session)):
    """Когда синхронизация отрабатывала в последний раз.

    Если инкрементальная давно молчит, кладовщик может не увидеть новый приход —
    лучше узнать об этом отсюда, чем по звонку со склада.
    """
    return sync_module.get_sync_status(session)


@router.get("/order-states")
def get_order_states():
    """Справочник статусов с человекочитаемыми названиями — из api1c.
    Заменяет захардкоженный в desktop-версии список из 93 значений."""
    return Api1cClient().get_order_states()


class SyncStatusRequest(BaseModel):
    position_id: int
    status_id: int
    sub_states: list[dict] | None = None


@router.post("/positions/{position_id}/sync-status")
async def sync_position_status_endpoint(
    position_id: int,
    body: SyncStatusRequest,
    user: CurrentUser = Depends(require_user),
):
    """Вызывается warehouse-сервисом после успешной приёмки.

    Синхронно ничего не делает — кладёт задачу в очередь, чтобы сбой связи
    со Stutzen не блокировал ответ кладовщику и не терялся молча, как это
    происходило в desktop-версии."""
    from arq import create_pool
    from arq.connections import RedisSettings

    redis = await create_pool(RedisSettings.from_dsn(os.environ["REDIS_URL"]))
    job = await redis.enqueue_job(
        "sync_position_status", body.position_id, body.status_id, body.sub_states
    )
    return {"queued": True, "job_id": job.job_id}
