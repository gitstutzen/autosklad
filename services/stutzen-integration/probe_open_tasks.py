"""
Пробник №4: сколько на самом деле незавершённых заданий и какой они давности.

Зачем: экран кладовщика должен показывать в том числе старые задания, по которым
не всё принято (задержка поставки — позиции ждут неделями). Подход "последние N
записей" такие задания теряет.

Прежде чем проектировать обходной путь, нужно понять масштаб:
  - сколько всего незавершённых заданий;
  - какой самый старый из них;
  - как они распределены по складам;
  - какие вообще бывают значения статуса.

Делает ОДИН полный запрос (~44 секунды, ~100 МБ) и считает статистику локально.
Только чтение. Сами данные никуда не сохраняются — только агрегаты.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python probe_open_tasks.py
"""
import os
import time
from collections import Counter
from datetime import datetime

os.environ["STUTZEN_READ_ONLY"] = "true"

import httpx

BASE_URL = os.environ.get("API1C_BASE_URL", "https://www.catalog.stutzen.ru/api1c")
API_KEY = os.environ.get("API1C_API_KEY")

if not API_KEY:
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

EMPTY_DATE = "0001-01-01T00:00:00"


def parse_date(value):
    if not value or value == EMPTY_DATE:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


print("Загружаем полный список заданий. Это займёт около минуты...")
client = httpx.Client(base_url=BASE_URL, timeout=600.0, headers={"ApiKey": API_KEY})

started = time.monotonic()
resp = client.get("/RoboStorage/GetStockTasks")
elapsed = time.monotonic() - started

if resp.status_code != 200:
    print(f"HTTP {resp.status_code}: {resp.text[:500]}")
    raise SystemExit(1)

size_mb = len(resp.content) / 1024 / 1024
rows = resp.json()
print(f"Получено {len(rows)} записей, {size_mb:.1f} МБ, за {elapsed:.0f} сек\n")

# ---- статусы ----
statuses = Counter(r.get("status") for r in rows)
print("=" * 70)
print("РАСПРЕДЕЛЕНИЕ ПО СТАТУСАМ")
print("=" * 70)
for status, cnt in sorted(statuses.items(), key=lambda x: -x[1]):
    share = cnt / len(rows) * 100
    print(f"  статус {status}: {cnt:>8}  ({share:5.1f}%)")

# ---- незавершённые ----
# По разбору десктоп-версии: 1 создано, 2 в работе, 4 завершено.
# Считаем незавершённым всё, что не 4.
unfinished = [r for r in rows if r.get("status") != 4]
print("\n" + "=" * 70)
print("НЕЗАВЕРШЁННЫЕ ЗАДАНИЯ (статус != 4)")
print("=" * 70)
print(f"  всего: {len(unfinished)} из {len(rows)}")
if rows:
    print(f"  доля:  {len(unfinished) / len(rows) * 100:.1f}%")

# ---- давность незавершённых ----
dated = [(parse_date(r.get("dateCreation")), r) for r in unfinished]
dated = [(d, r) for d, r in dated if d is not None]
dated.sort(key=lambda x: x[0])

if dated:
    oldest_date = dated[0][0]
    newest_date = dated[-1][0]
    now = datetime.now()
    print(f"\n  самое старое незавершённое: {oldest_date.date()} "
          f"({(now - oldest_date).days} дней назад)")
    print(f"  самое свежее незавершённое: {newest_date.date()}")

    print("\n  Сколько незавершённых попадает в окно 'последних N дней':")
    for days in [1, 3, 7, 30, 90, 365]:
        cnt = sum(1 for d, _ in dated if (now - d).days <= days)
        share = cnt / len(dated) * 100
        print(f"    за {days:>3} дн.: {cnt:>6} из {len(dated)}  ({share:5.1f}%)")

# ---- по складам ----
by_stock = Counter(r.get("stockId") for r in unfinished)
print("\n" + "=" * 70)
print("НЕЗАВЕРШЁННЫЕ ПО СКЛАДАМ")
print("=" * 70)
for stock, cnt in sorted(by_stock.items(), key=lambda x: -x[1])[:15]:
    print(f"  склад {stock}: {cnt:>7}")

# ---- проверка поля deletet ----
deletet_values = Counter(r.get("deletet") for r in rows)
print("\n" + "=" * 70)
print("ЗНАЧЕНИЯ ПОЛЯ deletet (назначение неясно, проверяем)")
print("=" * 70)
for value, cnt in sorted(deletet_values.items(), key=lambda x: -x[1]):
    print(f"  {value}: {cnt}")

# если deletet бывает разным — посмотрим, влияет ли он на незавершённые
if len(deletet_values) > 1:
    combo = Counter((r.get("deletet"), r.get("status")) for r in rows)
    print("\n  сочетания (deletet, status), топ-10:")
    for (d, s), cnt in combo.most_common(10):
        print(f"    deletet={d}, status={s}: {cnt}")

print("\n" + "=" * 70)
print("Присылайте этот вывод — здесь только агрегаты, персональных данных нет.")
