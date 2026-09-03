"""
Тесты преобразования позиции в ответ API и защиты от главной ловушки:
в api1c должен уходить documentNumber задания, а не его id.
"""
import pytest

from app.routers.statuses import TaskPositionOut, POSITION_STATUS_NAMES
from app.task_positions import parse_positions


def make_row(**overrides) -> dict:
    row = {
        "article": "ABC1117",
        "articleNew": "",
        "manufacturer": "ПРОИЗВОДИТЕЛЬ",
        "name": "Трос стояночного тормоза",
        "quantity": 10,
        "quantityFact": 4,
        "quantityScanned": 0,
        "quantityTotalScanned": 0,
        "price": 515.48,
        "priceTotal": 5154.80,
        "refStutzen": 14664960,
        "refProvider": 14667317,
        "tradePoint": 12,
        "numberCustomer": 262607,
        "comment": None,
        "processingStartTime": "0001-01-01T00:00:00",
        "processingCompletionTime": "0001-01-01T00:00:00",
        "timeOfLastChange": "2026-09-02T02:47:34.587",
        "statusPosition": 2,
    }
    row.update(overrides)
    return row


def to_out(**overrides) -> TaskPositionOut:
    position = parse_positions([make_row(**overrides)])[0]
    return TaskPositionOut.from_position(position)


def test_remaining_is_calculated_for_frontend():
    """Остаток считается на сервере, чтобы фронтенд не повторял эту логику."""
    out = to_out(quantity=10, quantityFact=4)
    assert out.remaining == 6


def test_status_name_is_human_readable():
    """Фронтенду не нужно знать про числовые коды статусов.

    Названия — дословно из справочной таблицы PositionsStorageStatus боевой базы
    (прочитано 02.09.2026). Если правите их, правьте и здесь: расхождение
    с десктоп-версией будет сбивать кладовщиков с толку.
    """
    assert to_out(statusPosition=1).status_name == "Необработана"
    assert to_out(statusPosition=2).status_name == "Принята частично"
    assert to_out(statusPosition=3).status_name == "Принята"
    assert to_out(statusPosition=4).status_name == "Излишек"
    assert to_out(statusPosition=5).status_name == "Отсутствует"
    assert to_out(statusPosition=6).status_name == "Принято с разногласием"


def test_unknown_status_does_not_crash():
    """Если в Stutzen появится новый статус, экран должен продолжить работать."""
    out = to_out(statusPosition=99)
    assert out.status_name == "Неизвестный статус"
    assert out.status_position == 99


def test_all_known_statuses_have_names():
    for code in (1, 2, 3, 4, 5, 6):
        assert code in POSITION_STATUS_NAMES


def test_empty_article_new_becomes_none():
    """Пустая строка в articleNew означает 'замены не было'."""
    assert to_out(articleNew="").article_new is None
    assert to_out(articleNew="XYZ999").article_new == "XYZ999"


def test_label_fields_are_present():
    """Точка назначения и клиент печатаются на этикетке — они должны доехать
    до фронтенда, иначе кладовщик не поймёт, куда едет деталь."""
    out = to_out()
    assert out.trade_point == 12
    assert out.number_customer == 262607


# ---- защита от главной ловушки ----

class FakeApi1c:
    """Запоминает, с каким аргументом его вызвали."""
    last_document_number = None

    def get_stock_task_positions(self, document_number: int):
        FakeApi1c.last_document_number = document_number
        return []


def test_client_method_signature_requires_document_number():
    """Метод клиента принимает именно document_number.

    Это защита от ошибки, которая не даёт о себе знать: если передать в api1c
    id задания вместо documentNumber, API ответит 200 OK и пустым списком —
    без ошибки. Экран окажется пустым, и причина будет неочевидна.

    Поэтому параметр назван document_number, а не абстрактным task_id:
    вызывающий код не может передать не то, не заметив этого.
    """
    import inspect
    from app.api1c_client import Api1cClient

    signature = inspect.signature(Api1cClient.get_stock_task_positions)
    assert "document_number" in signature.parameters, (
        "параметр должен называться document_number — см. записную книжку, "
        "раздел «Про связь задания и его позиций»"
    )
    assert "task_id" not in signature.parameters
    assert "stk_id" not in signature.parameters
