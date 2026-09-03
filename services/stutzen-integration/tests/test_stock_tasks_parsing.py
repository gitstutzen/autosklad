"""
Тесты разбора ответа GetStockTasks.

Образцы взяты из реального ответа боевого API (пробник от 31.08.2026),
названия поставщиков и логины заменены на условные — в репозитории
не должно быть боевых данных.
"""
from datetime import datetime

from app.stock_tasks import parse_stock_tasks, StockTask


SAMPLE = [
    {
        "id": 486234,
        "receiptNumber": 660089,
        "documentNumber": 11692591,
        "dateCreation": "2026-08-31T13:53:56.39",
        "dateLastChange": "2026-08-31T13:53:56.39",
        "status": 1,
        "deletet": 1,
        "provider": "МСК-МСК-НДС-ООО ПОСТАВЩИК (БРЕНД)",
        "amount": 149848.0,
        "startTime": "0001-01-01T00:00:00",
        "endTime": "0001-01-01T00:00:00",
        "stockId": 8,
        "comment": "",
        "commentStock": None,
        "login": "Ivanov_I",
        "rcp_id": 660089,
        "stk_id": 0,
    },
    {
        "id": 486233,
        "receiptNumber": 659616,
        "documentNumber": 11684242,
        "dateCreation": "2026-08-31T13:52:52.157",
        "dateLastChange": "2026-08-31T13:52:52.157",
        "status": 1,
        "deletet": 1,
        "provider": "МСК-МСК-НДС-ИП ПОСТАВЩИК (БРЕНД2)",
        "amount": 2965.0,
        "startTime": "0001-01-01T00:00:00",
        "endTime": "0001-01-01T00:00:00",
        "stockId": 8,
        "comment": "",
        "commentStock": None,
        "login": "Petrova_A",
        "rcp_id": 659616,
        "stk_id": 0,
    },
]


def test_parses_all_valid_rows():
    tasks = parse_stock_tasks(SAMPLE)
    assert len(tasks) == 2
    assert all(isinstance(t, StockTask) for t in tasks)


def test_maps_fields_correctly():
    task = parse_stock_tasks(SAMPLE)[0]
    assert task.id == 486234
    assert task.receipt_number == 660089
    assert task.document_number == 11692591
    assert task.status == 1
    assert task.stock_id == 8
    assert task.amount == 149848.0
    assert task.login == "Ivanov_I"


def test_dotnet_empty_date_becomes_none():
    """0001-01-01 — это признак 'не заполнено' у .NET, а не реальная дата.
    Без обработки фронтенд показал бы кладовщику 1 год нашей эры."""
    task = parse_stock_tasks(SAMPLE)[0]
    assert task.started_at is None
    assert task.finished_at is None


def test_real_dates_are_parsed():
    task = parse_stock_tasks(SAMPLE)[0]
    assert task.created_at == datetime(2026, 8, 31, 13, 53, 56, 390000)


def test_filled_start_time_is_kept():
    row = dict(SAMPLE[0], startTime="2026-08-31T14:10:00")
    task = parse_stock_tasks([row])[0]
    assert task.started_at == datetime(2026, 8, 31, 14, 10, 0)


def test_task_without_stock_is_not_lost():
    """Задание без склада должно разбираться, а не выбрасываться молча.

    В боевых данных такие есть: на 02.09.2026 — 5 активных заданий
    с пустым StockId. Пока поле было обязательным, разбор их отбрасывал,
    и они пропадали из зеркала без всякого следа.
    """
    row = dict(SAMPLE[0], stockId=None)
    tasks = parse_stock_tasks([row])
    assert len(tasks) == 1
    assert tasks[0].stock_id is None


def test_task_with_zero_stock_is_kept():
    """Склад 0 тоже встречается в боевых данных — это не то же самое,
    что отсутствие склада, и терять такие записи нельзя."""
    row = dict(SAMPLE[0], stockId=0)
    tasks = parse_stock_tasks([row])
    assert len(tasks) == 1
    assert tasks[0].stock_id == 0


def test_every_field_except_id_may_be_empty():
    """Ни одно поле, кроме id, не должно быть обязательным.

    Это защита от целого класса ошибок, а не от конкретного поля. Мы дважды
    наступили на одни грабли: сначала объявили обязательным stock_id
    (потеряли 5 активных заданий), потом login (потеряли 65 700 записей,
    14,5% всей базы). Каждый раз чинили одно поле и не проверяли остальные.

    Здесь проверяются все поля сразу: если кто-то снова сделает поле
    обязательным, тест упадёт до того, как записи начнут исчезать из зеркала.
    """
    from app.stock_tasks import parse_stock_tasks_detailed

    optional_fields = [
        "receiptNumber", "documentNumber", "dateCreation", "dateLastChange",
        "status", "provider", "amount", "stockId", "login",
        "startTime", "endTime", "comment", "commentStock",
    ]

    for field_name in optional_fields:
        row = dict(SAMPLE[0], **{field_name: None})
        result = parse_stock_tasks_detailed([row])
        assert result.skipped == 0, (
            f"запись с пустым {field_name} была отброшена: {result.report()}. "
            f"Поле должно быть необязательным — иначе такие записи молча "
            f"исчезнут из зеркала."
        )


def test_only_id_is_truly_required():
    """Обратная проверка: без id запись бессмысленна, её отбрасывать правильно."""
    from app.stock_tasks import parse_stock_tasks_detailed

    result = parse_stock_tasks_detailed([dict(SAMPLE[0], id=None)])
    assert result.skipped == 1


def test_skipped_rows_are_counted():
    """Пропуски обязаны считаться, а не исчезать молча.

    Полная синхронизация 02.09.2026 потеряла ~65 000 записей из 452 000,
    и это осталось незамеченным ровно потому, что счётчика не было.
    """
    from app.stock_tasks import parse_stock_tasks_detailed

    rows = [SAMPLE[0], {"id": "не число"}, {"нет": "полей"}, SAMPLE[1]]
    result = parse_stock_tasks_detailed(rows)

    assert len(result.tasks) == 2
    assert result.skipped == 2
    assert sum(result.reasons.values()) == 2


def test_report_mentions_losses():
    """Отчёт должен явно говорить о потере, чтобы её было видно в логах."""
    from app.stock_tasks import parse_stock_tasks_detailed

    result = parse_stock_tasks_detailed([SAMPLE[0], {"мусор": 1}])
    assert "ПРОПУЩЕНО" in result.report()


def test_report_is_calm_when_nothing_lost():
    from app.stock_tasks import parse_stock_tasks_detailed

    result = parse_stock_tasks_detailed(SAMPLE)
    assert result.skipped == 0
    assert "ПРОПУЩЕНО" not in result.report()


def test_reasons_explain_what_broke():
    """В причине должно быть видно, какое поле подвело — иначе непонятно,
    чинить данные или наши допущения о них."""
    from app.stock_tasks import parse_stock_tasks_detailed

    result = parse_stock_tasks_detailed([dict(SAMPLE[0], id="не число")])
    reasons = " ".join(result.reasons.keys())
    assert "id" in reasons


def test_bad_row_is_skipped_not_crashing():
    """В выборке 450 000+ записей за годы работы почти наверняка есть аномалии.
    Одна битая строка не должна ломать весь список заданий кладовщика."""
    rows = [SAMPLE[0], {"id": "не число", "provider": None}, SAMPLE[1]]
    tasks = parse_stock_tasks(rows)
    assert len(tasks) == 2


def test_empty_response():
    assert parse_stock_tasks([]) == []


def test_unknown_fields_are_ignored():
    """API может добавить поля — это не должно ничего ломать."""
    row = dict(SAMPLE[0], someNewFieldFromStutzen="значение")
    tasks = parse_stock_tasks([row])
    assert len(tasks) == 1
