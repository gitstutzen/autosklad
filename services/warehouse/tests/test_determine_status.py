"""
Тест на уже реализованную часть логики — determine_status() (app/service.py).
Это единственная функция в warehouse-сервисе, которая на сегодня не заглушка,
а перенесённое из FormStock.SavePosition правило (раздел 11 анализа).
Запускается без Docker, без базы данных, без сети — чистая функция.
"""
from app.service import determine_status
from libs.common.schemas import PositionStatus


def test_nothing_accepted_is_unprocessed():
    assert determine_status(expected=10, accepted_total=0, has_issues=False) == PositionStatus.UNPROCESSED


def test_partial_acceptance():
    assert determine_status(expected=10, accepted_total=4, has_issues=False) == PositionStatus.PARTIAL


def test_full_clean_acceptance():
    assert determine_status(expected=10, accepted_total=10, has_issues=False) == PositionStatus.ACCEPTED


def test_full_acceptance_with_issues_is_status_6():
    """Статус 6 ('принята, но есть брак/недостача/пересорт') — значение, которого
    не было в исходном справочнике LocalDb и которое нашлось только при разборе
    FormStock.SavePosition (раздел 11 анализа). Этот тест защищает именно его."""
    assert determine_status(expected=10, accepted_total=10, has_issues=True) == PositionStatus.ACCEPTED_WITH_ISSUES


def test_excess():
    assert determine_status(expected=10, accepted_total=12, has_issues=False) == PositionStatus.EXCESS
