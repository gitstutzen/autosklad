"""
Разбор ответа api1c/RoboStorage/GetStockTasks.

Структура описана по РЕАЛЬНОМУ ответу боевого API (пробник от 31.08.2026),
а не по документации — документация полей не описывала.

Реальный формат: голый JSON-массив объектов (не обёртка вида {result: [...]}),
каждый объект — одно складское задание (приход от поставщика).
"""
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum

from pydantic import BaseModel, ValidationError, field_validator

# api1c возвращает эту дату вместо пустого значения — так .NET сериализует
# неинициализированный DateTime. Означает "время не проставлено".
DOTNET_EMPTY_DATE = "0001-01-01T00:00:00"


class StockTaskStatus(IntEnum):
    """Статусы складского задания.

    Названия взяты из справочной таблицы StockTasksStatus боевой базы
    (прочитано напрямую 02.09.2026). Через api1c этот справочник не отдаётся.

    Разделение на активные и завершённые — из SQL-запросов десктоп-версии
    (FormStock.cs): вкладка "не завершено" запрашивает статусы 1, 2, 5, 6,
    вкладка "завершено" — статусы 3 и 4.
    """
    QUEUED = 1               # В очереди
    IN_PROGRESS = 2          # В работе
    ACCEPTED = 3             # Принят (завершён)
    COMPLETED = 4            # Выполнен (завершён)
    SUSPENDED = 5            # Приостановлен — приход с задержкой поставки,
                             # ждёт товар. Может висеть месяцами.
    UNDEFINED = 6            # Неопределен
    COMPLETED_PARTIALLY = 7  # Выполнен несовсем


STOCK_TASK_STATUS_NAMES = {
    1: "В очереди",
    2: "В работе",
    3: "Принят",
    4: "Выполнен",
    5: "Приостановлен",
    6: "Неопределен",
    7: "Выполнен несовсем",
}


# Статусы, при которых задание требует работы кладовщика.
#
# ВНИМАНИЕ на статус 7 ("Выполнен несовсем"): он есть в справочнике, но
# десктоп-версия не показывает его НИ на одной вкладке — ни в "не завершено"
# (1, 2, 5, 6), ни в "завершено" (3, 4). Задание с таким статусом было бы
# невидимым в программе. В боевых данных таких записей нет ни одной,
# поэтому пока повторяем поведение десктопа. Появятся — решать отдельно.
ACTIVE_STATUSES = frozenset({
    StockTaskStatus.QUEUED,
    StockTaskStatus.IN_PROGRESS,
    StockTaskStatus.SUSPENDED,
    StockTaskStatus.UNDEFINED,
})


class StockTask(BaseModel):
    """Складское задание — приход товара от поставщика.

    ПОЧЕМУ ПОЧТИ ВСЕ ПОЛЯ НЕОБЯЗАТЕЛЬНЫЕ.

    Это зеркало чужой системы, накопившей данные с 2017 года. Мы не управляем
    качеством того, что в ней лежит, и не можем требовать от старых записей
    полноты. Строгая модель здесь означает не защиту, а потерю данных: строка
    просто не разбирается и молча исчезает из зеркала.

    Так уже дважды и вышло:
      - stock_id объявили обязательным — потеряли 5 активных заданий;
      - login объявили обязательным — потеряли 65 700 записей (14,5% всей базы,
        02.09.2026). Проверка показала: у них поле login пустое.

    Поэтому обязательным остаётся только id — без него запись невозможно
    ни сохранить, ни обновить. Всё остальное принимается таким, какое пришло.
    Проверять полноту данных — задача экрана, а не разбора: лучше показать
    приход без указания автора, чем не показать приход вовсе.
    """
    id: int                              # id — единственное действительно
                                         # обязательное поле: ключ записи

    receipt_number: int | None = None    # receiptNumber — номер прихода
    document_number: int | None = None   # documentNumber — по нему запрашиваются
                                         # позиции задания (параметр dcc_id)
    created_at: datetime | None = None   # dateCreation
    changed_at: datetime | None = None   # dateLastChange
    status: int | None = None            # status: см. StockTaskStatus
    provider: str | None = None          # provider — "МСК-МСК-НДС-Название (Бренд)"
    amount: float | None = None          # amount — сумма прихода
    stock_id: int | None = None          # stockId — склад. Бывает пустым.
    login: str | None = None             # login — кто создал приход.
                                         # Пустой у 65 700 записей.
    started_at: datetime | None = None   # startTime, пусто = не начато
    finished_at: datetime | None = None  # endTime, пусто = не завершено
    comment: str | None = None           # comment
    comment_stock: str | None = None     # commentStock

    @property
    def is_active(self) -> bool:
        """Требует ли задание работы кладовщика."""
        return self.status in ACTIVE_STATUSES

    @field_validator("started_at", "finished_at", mode="before")
    @classmethod
    def empty_dotnet_date_to_none(cls, value):
        """0001-01-01T00:00:00 — это "не заполнено", а не реальная дата.
        Без этого преобразования фронтенд показывал бы 1 год нашей эры."""
        if value in (None, "", DOTNET_EMPTY_DATE):
            return None
        return value


@dataclass
class ParseResult:
    """Результат разбора: что получилось и что потерялось.

    Счётчик пропусков существует не для красоты. Полная синхронизация 02.09.2026
    незаметно потеряла 65 000 записей из 452 000 — просто потому, что пропуски
    нигде не считались. Молчаливое "continue" скрывает не только мусор в данных,
    но и наши собственные неверные допущения о них.
    """
    tasks: list["StockTask"]
    skipped: int = 0
    reasons: Counter = field(default_factory=Counter)

    def report(self) -> str:
        if not self.skipped:
            return f"разобрано {len(self.tasks)}, пропусков нет"
        top = ", ".join(f"{reason} ({count})" for reason, count in self.reasons.most_common(5))
        return f"разобрано {len(self.tasks)}, ПРОПУЩЕНО {self.skipped}. Причины: {top}"


def parse_stock_tasks_detailed(payload: list[dict]) -> ParseResult:
    """Разбор с подсчётом пропусков и причин.

    Записи, которые не удалось разобрать, пропускаются, а не роняют весь список:
    в выборке 450 000+ записей за много лет найдутся аномалии, и из-за одной
    такой строки экран кладовщика не должен переставать работать.
    Но пропуски ОБЯЗАТЕЛЬНО подсчитываются — иначе потеря данных незаметна.
    """
    result = ParseResult(tasks=[])
    for row in payload:
        try:
            result.tasks.append(StockTask(**_to_snake(row)))
        except Exception as exc:
            result.skipped += 1
            result.reasons[_describe_error(exc)] += 1
    return result


def _describe_error(exc: Exception) -> str:
    """Короткое описание причины — чтобы в отчёте было видно, что именно ломается,
    без простыни из полного текста ошибки на каждую строку."""
    if isinstance(exc, ValidationError):
        problems = sorted({
            f"{'.'.join(str(p) for p in err['loc'])}: {err['type']}"
            for err in exc.errors()
        })
        return "; ".join(problems[:3])
    return type(exc).__name__


def parse_stock_tasks(payload: list[dict]) -> list[StockTask]:
    """Разбор без подробностей — для мест, где счётчик пропусков не нужен.

    Если разбираете полную выгрузку, берите parse_stock_tasks_detailed:
    там видно, сколько записей потерялось.
    """
    return parse_stock_tasks_detailed(payload).tasks


FIELD_MAP = {
    "id": "id",
    "receiptNumber": "receipt_number",
    "documentNumber": "document_number",
    "dateCreation": "created_at",
    "dateLastChange": "changed_at",
    "status": "status",
    "provider": "provider",
    "amount": "amount",
    "stockId": "stock_id",
    "login": "login",
    "startTime": "started_at",
    "endTime": "finished_at",
    "comment": "comment",
    "commentStock": "comment_stock",
    # Намеренно не переносим:
    #   deletet — 1 означает АКТИВНАЯ запись, а не удалённая (логика обратна названию).
    #             Все SQL-запросы десктоп-версии содержат условие Deletet=1, и в боевой
    #             выгрузке все 452 200 записей имеют значение 1 — то есть api1c
    #             удалённые просто не отдаёт. Поле бесполезно для наших задач.
    #   rcp_id  — дублирует receiptNumber в наблюдаемых данных.
    #   stk_id  — во всех записях 0, назначение неясно. Не путать с id.
}


def _to_snake(row: dict) -> dict:
    return {FIELD_MAP[k]: v for k, v in row.items() if k in FIELD_MAP}
