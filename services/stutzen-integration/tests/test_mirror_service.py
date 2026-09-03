"""
Тесты зеркала складских заданий.

Используется SQLite в памяти — тесты не ходят ни в боевой Stutzen,
ни в реальную базу. Каждый тест получает чистую базу.
"""
from datetime import datetime, date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Base, StockTaskMirror
from app import stock_tasks_service as svc


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def add_task(
    session: Session,
    task_id: int,
    stock_id: int = 8,
    status: int = 1,
    provider: str = "МСК-МСК-НДС-ПОСТАВЩИК (БРЕНД)",
    created: datetime | None = None,
) -> StockTaskMirror:
    task = StockTaskMirror(
        id=task_id,
        receipt_number=600000 + task_id,
        document_number=11000000 + task_id,
        created_at=created or datetime(2026, 8, 31, 13, 0, 0),
        changed_at=created or datetime(2026, 8, 31, 13, 0, 0),
        status=status,
        stock_id=stock_id,
        provider=provider,
        provider_search=provider.lower(),
        amount=1000.0,
        login="Ivanov_I",
        synced_at=datetime(2026, 8, 31, 14, 0, 0),
    )
    session.add(task)
    session.commit()
    return task


# ---- главный сценарий, ради которого делалось зеркало ----

def test_old_unfinished_task_stays_visible(session):
    """Ключевой случай: по приходу месячной давности не приняли часть позиций
    из-за задержки поставки. Кладовщик должен иметь возможность к нему вернуться.

    Через api1c такое задание было бы недоступно — оно давно ушло за пределы
    свежего среза. В зеркале оно есть."""
    add_task(session, 1, status=1, created=datetime(2026, 7, 1, 10, 0))   # месяц назад
    add_task(session, 2, status=1, created=datetime(2026, 8, 31, 13, 0))  # сегодня

    tasks = svc.list_tasks(session, stock_id=8)

    ids = [t.id for t in tasks]
    assert 1 in ids, "старое незакрытое задание должно оставаться доступным"
    assert ids == [2, 1], "свежие сверху, старые ниже"


def test_finished_old_task_is_hidden_by_default(session):
    """Закрытые задания не засоряют список, даже если они старые."""
    add_task(session, 1, status=4, created=datetime(2026, 7, 1, 10, 0))
    add_task(session, 2, status=1, created=datetime(2026, 8, 31, 13, 0))

    tasks = svc.list_tasks(session, stock_id=8)
    assert [t.id for t in tasks] == [2]


# ---- фильтры, которых нет в api1c ----

def test_filter_by_stock(session):
    add_task(session, 1, stock_id=8)
    add_task(session, 2, stock_id=3)
    assert [t.id for t in svc.list_tasks(session, stock_id=8)] == [1]


def test_status_3_is_treated_as_finished(session):
    """Статус 3 — ЗАВЕРШЁННОЕ задание, а не активное.

    Это не мелочь: в боевых данных в статусе 3 висит 8654 задания, включая
    записи 2017 года. Пока здесь стояло условие "статус != 4", все они попадали
    бы в список кладовщика как требующие работы.

    Источник: SQL-запросы десктоп-версии (FormStock.cs) — вкладка "не завершено"
    запрашивает статусы 1, 2, 5, 6, вкладка "завершено" — 3 и 4.
    """
    add_task(session, 1, status=1)   # создано — активное
    add_task(session, 2, status=2)   # в работе — активное
    add_task(session, 3, status=3)   # завершено
    add_task(session, 4, status=4)   # завершено
    add_task(session, 5, status=5)   # активное

    tasks = svc.list_tasks(session, stock_id=8)
    assert sorted(t.id for t in tasks) == [1, 2, 5]


def test_count_unfinished_excludes_status_3(session):
    add_task(session, 1, status=1)
    add_task(session, 2, status=3)
    add_task(session, 3, status=4)
    assert svc.count_unfinished(session, stock_id=8) == 1


def test_include_finished_when_asked(session):
    add_task(session, 1, status=1)
    add_task(session, 2, status=4)
    tasks = svc.list_tasks(session, stock_id=8, only_unfinished=False)
    assert len(tasks) == 2


def test_filter_by_provider_is_case_insensitive_for_cyrillic(session):
    """Поиск по поставщику должен игнорировать регистр КИРИЛЛИЦЫ.

    Это не придирка. Первая реализация использовала ILIKE, и она работала бы
    в PostgreSQL (прод), но не в SQLite (тесты): встроенное приведение регистра
    в SQLite обрабатывает только латиницу. То есть код вёл бы себя в тестах
    и в проде по-разному.

    Решение: отдельное нормализованное поле provider_search, заполняемое
    в Python при записи. Проверяем оба направления регистра.
    """
    add_task(session, 1, provider="МСК-МСК-НДС-АЛЬФА (БРЕНД1)")
    add_task(session, 2, provider="МСК-МСК-НДС-БЕТА (БРЕНД2)")

    assert [t.id for t in svc.list_tasks(session, stock_id=8, provider_contains="альфа")] == [1]
    assert [t.id for t in svc.list_tasks(session, stock_id=8, provider_contains="АЛЬФА")] == [1]
    assert [t.id for t in svc.list_tasks(session, stock_id=8, provider_contains="БеТа")] == [2]


def test_filter_by_provider(session):
    add_task(session, 1, provider="МСК-МСК-НДС-АЛЬФА (БРЕНД1)")
    add_task(session, 2, provider="МСК-МСК-НДС-БЕТА (БРЕНД2)")
    tasks = svc.list_tasks(session, stock_id=8, provider_contains="альфа")
    assert [t.id for t in tasks] == [1], "поиск должен игнорировать регистр"


def test_filter_by_date_range(session):
    add_task(session, 1, created=datetime(2026, 7, 1, 10, 0))
    add_task(session, 2, created=datetime(2026, 8, 15, 10, 0))
    add_task(session, 3, created=datetime(2026, 8, 31, 10, 0))

    tasks = svc.list_tasks(
        session, stock_id=8,
        created_from=date(2026, 8, 1), created_to=date(2026, 8, 20),
    )
    assert [t.id for t in tasks] == [2]


def test_date_to_includes_whole_day(session):
    """Граничный случай: задание, созданное в 23:50, должно попадать
    в выборку за этот день, а не отсекаться полуночью."""
    add_task(session, 1, created=datetime(2026, 8, 15, 23, 50))
    tasks = svc.list_tasks(
        session, stock_id=8,
        created_from=date(2026, 8, 15), created_to=date(2026, 8, 15),
    )
    assert [t.id for t in tasks] == [1]


def test_pagination(session):
    for i in range(1, 6):
        add_task(session, i, created=datetime(2026, 8, i, 10, 0))

    page1 = svc.list_tasks(session, stock_id=8, limit=2, offset=0)
    page2 = svc.list_tasks(session, stock_id=8, limit=2, offset=2)

    assert [t.id for t in page1] == [5, 4]
    assert [t.id for t in page2] == [3, 2]


def test_get_single_task(session):
    """В api1c получить одно задание по номеру нельзя вообще —
    работает только благодаря зеркалу."""
    add_task(session, 486234)
    task = svc.get_task(session, 486234)
    assert task is not None
    assert task.receipt_number == 1086234


def test_get_missing_task_returns_none(session):
    assert svc.get_task(session, 999999) is None


def test_count_unfinished_includes_old(session):
    add_task(session, 1, status=1, created=datetime(2026, 6, 1, 10, 0))
    add_task(session, 2, status=2, created=datetime(2026, 8, 31, 10, 0))
    add_task(session, 3, status=4, created=datetime(2026, 8, 31, 11, 0))

    assert svc.count_unfinished(session, stock_id=8) == 2
