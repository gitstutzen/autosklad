"""
Диагностика потери записей при разборе.

Проблема: полная синхронизация 02.09.2026 положила в зеркало 387 585 записей,
хотя прямой запрос к базе показывает 453 147, а пробник по api1c двумя днями
раньше — 452 200. Потерялось около 65 000 записей, и произошло это молча.

Скрипт выясняет, где именно теряются данные:
  - сколько записей вообще пришло от api1c;
  - сколько из них не прошли разбор и по каким причинам;
  - как выглядят проблемные строки (с обезличиванием).

Только чтение. Ничего никуда не записывается.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python diagnose_lost_records.py

Займёт около трёх минут: полная выгрузка идёт долго.
"""
import os
import sys
import time
from collections import Counter

os.environ["STUTZEN_READ_ONLY"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("JWT_SECRET", "not-used-here")
os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "not-used-here")

if not os.environ.get("API1C_API_KEY"):
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.api1c_client import Api1cClient
from app.stock_tasks import parse_stock_tasks_detailed


SAFE_FIELDS = (
    "id", "receiptNumber", "documentNumber", "dateCreation", "dateLastChange",
    "status", "deletet", "stockId", "stk_id", "rcp_id",
)


def header(text: str) -> None:
    print("\n" + "=" * 74)
    print(text)
    print("=" * 74)


def safe_view(row: dict) -> dict:
    """Только безличные поля: без поставщика, логина, сумм и комментариев."""
    view = {k: row.get(k) for k in SAFE_FIELDS if k in row}
    for name in ("provider", "login", "comment", "commentStock", "amount"):
        if name in row:
            value = row[name]
            view[name] = f"<{type(value).__name__}>" if value is not None else None
    return view


header("ШАГ 1. Забираем полную выгрузку")
print("Это займёт пару минут...")

started = time.monotonic()
payload = Api1cClient().get_stock_tasks()
elapsed = time.monotonic() - started

if not isinstance(payload, list):
    print(f"api1c вернул не список, а {type(payload).__name__}")
    raise SystemExit(1)

print(f"Получено записей: {len(payload)}, за {elapsed:.0f} сек")

header("ШАГ 2. Разбор с подсчётом пропусков")

parsed = parse_stock_tasks_detailed(payload)
print(parsed.report())

if parsed.skipped:
    print(f"\nДоля потерь: {parsed.skipped / len(payload) * 100:.1f}%")
    print("\nПричины пропусков:")
    for reason, count in parsed.reasons.most_common():
        print(f"  {count:>7}  {reason}")

    # найдём примеры проблемных строк
    print("\nПримеры проблемных записей (только безличные поля):")
    shown = 0
    seen_reasons = set()
    for row in payload:
        if shown >= 6:
            break
        try:
            from app.stock_tasks import StockTask, _to_snake
            StockTask(**_to_snake(row))
        except Exception as exc:
            from app.stock_tasks import _describe_error
            reason = _describe_error(exc)
            if reason in seen_reasons:
                continue
            seen_reasons.add(reason)
            shown += 1
            print(f"\n  причина: {reason}")
            print(f"  запись: {safe_view(row)}")
else:
    print("\nПри разборе ничего не потерялось.")
    print("Значит, дело не в разборе — api1c отдал меньше записей, чем есть в базе.")

header("ШАГ 3. Сверка количества")

print(f"Пришло от api1c:        {len(payload)}")
print(f"Разобрано успешно:      {len(parsed.tasks)}")
print(f"Ожидалось (по базе):    453147")
print(f"Было 31.08 (пробник):   452200")

gap_api = 453147 - len(payload)
if gap_api > 0:
    print(f"\nApi1c отдал на {gap_api} записей меньше, чем есть в базе.")
    print("Это уже не про разбор — вопрос к самому API.")
    print("Возможные причины: отдаёт не все статусы, есть внутренний предел выдачи,")
    print("или ответ обрывается на большом объёме.")

# распределение по статусам среди сырых данных — сверим с базой
header("ШАГ 4. Статусы в сырых данных api1c")
print("Сверьте с тем, что показал прямой запрос к базе:")
print("  1: 188, 2: 104, 3: 8619, 4: 444212, 5: 24\n")

raw_statuses = Counter(r.get("status") for r in payload)
for status, count in sorted(raw_statuses.items(), key=lambda x: (x[0] is None, x[0])):
    print(f"  статус {status}: {count}")

# уникальность id — вдруг дубли схлопываются при записи
header("ШАГ 5. Нет ли дублей по id")
ids = [r.get("id") for r in payload]
unique_ids = len(set(ids))
print(f"Записей: {len(ids)}, уникальных id: {unique_ids}")
if unique_ids < len(ids):
    print(f"ДУБЛИ: {len(ids) - unique_ids} записей с повторяющимся id.")
    print("При записи в зеркало такие схлопываются в одну — это тоже потеря.")
else:
    print("Дублей нет.")

print("\n" + "=" * 74)
print("Присылайте вывод — здесь только числа, причины ошибок и обезличенные")
print("примеры записей. Поставщики, логины и суммы заменены на тип значения.")
