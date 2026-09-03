"""
Тест-сторож: все переменные окружения, которые модули читают жёстко
(через os.environ["..."]), должны быть заданы в conftest.py.

Зачем: такие переменные читаются при ИМПОРТЕ модуля. Если какой-то из них нет,
падает не отдельный тест, а сбор всех тестов сразу — с сообщением вида
KeyError: 'JWT_SECRET', по которому не сразу понятно, что чинить.

Это уже случалось дважды: сначала не хватало DATABASE_URL, потом JWT_SECRET.
Тест находит пропуск сам, вместо того чтобы ждать очередного падения.
"""
import os
import re
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = SERVICE_ROOT.parent.parent

# Жёсткое чтение переменной: os.environ["ИМЯ"]. Мягкое (.get / .setdefault)
# не ломает импорт, поэтому здесь не учитывается.
HARD_READ = re.compile(r'os\.environ\[\s*["\']([A-Z_0-9]+)["\']\s*\]')


def collect_required_vars() -> set[str]:
    required: set[str] = set()
    search_dirs = [SERVICE_ROOT / "app", REPO_ROOT / "libs"]
    for directory in search_dirs:
        if not directory.exists():
            continue
        for path in directory.rglob("*.py"):
            text = path.read_text(encoding="utf-8", errors="replace")
            required.update(HARD_READ.findall(text))
    return required


def test_conftest_defines_all_required_env_vars():
    required = collect_required_vars()
    assert required, "не нашлось ни одной переменной — проверьте пути поиска"

    missing = sorted(name for name in required if name not in os.environ)
    assert not missing, (
        f"Эти переменные читаются при импорте, но не заданы в conftest.py: {missing}. "
        f"Без них упадёт сбор всех тестов, а не один. Добавьте их в conftest.py "
        f"с заведомо фиктивными значениями."
    )


def test_test_env_does_not_point_at_production():
    """Страховка: тестовое окружение не должно вести в боевые системы.

    У проекта нет тестового контура — один боевой API Stutzen с одним ключом.
    Если тест по недосмотру уйдёт в сеть, он должен упасть на подключении,
    а не выполнить настоящий запрос.

    Проверка не теоретическая: 02.09.2026 этот тест поймал реальную ситуацию.
    В окне терминала остались переменные от запуска пробников, а conftest.py
    задавал значения через setdefault — то есть уступал им. Тесты оказались
    настроены на боевой Stutzen с настоящим ключом. После этого conftest.py
    перезаписывает такие переменные безусловно.
    """
    for name in ("API1C_BASE_URL", "TRADESOFT_API_BASE_URL"):
        value = os.environ.get(name, "")
        assert "stutzen.ru" not in value, (
            f"{name} указывает на боевой Stutzen ({value}). "
            f"В тестах должен быть заведомо нерабочий адрес."
        )

    # База: тесты создают и удаляют таблицы, попасть в боевую нельзя.
    database_url = os.environ.get("DATABASE_URL", "")
    assert database_url.startswith("sqlite"), (
        f"DATABASE_URL должен указывать на SQLite в тестах, а не на {database_url}. "
        f"Тесты создают и удаляют таблицы."
    )

    # Очередь задач: настоящий Redis тоже не нужен.
    redis_url = os.environ.get("REDIS_URL", "")
    assert "6379" not in redis_url, (
        f"REDIS_URL ведёт на стандартный порт Redis ({redis_url}) — "
        f"в тестах должен быть заведомо нерабочий."
    )
