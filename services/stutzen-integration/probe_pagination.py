"""
Пробник №3: выясняем, как именно работает count и есть ли постраничность.

Что уже известно из пробника №2:
  - из всех проверенных параметров работает ТОЛЬКО count;
  - фильтры по складу, статусу и датам игнорируются;
  - count=10 отдаёт ответ за 0.1 сек против 44 сек на полной выгрузке.

Что нужно выяснить сейчас:
  1. count возвращает САМЫЕ СВЕЖИЕ записи или самые старые?
     От этого зависит, годится ли метод для экрана кладовщика вообще.
  2. Есть ли параметр смещения (взять следующую порцию)?
     Без него нельзя пролистать дальше первых N записей.
  3. Можно ли получить конкретное задание по его id?

Все запросы — GET, только чтение. Запросы с count маленькие и быстрые,
проверка смещений тоже ограничена по count, так что полных выгрузок не будет.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python probe_pagination.py
"""
import os
import time

os.environ["STUTZEN_READ_ONLY"] = "true"

import httpx

BASE_URL = os.environ.get("API1C_BASE_URL", "https://www.catalog.stutzen.ru/api1c")
API_KEY = os.environ.get("API1C_API_KEY")

if not API_KEY:
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

client = httpx.Client(base_url=BASE_URL, timeout=180.0, headers={"ApiKey": API_KEY})


def fetch(params: dict):
    started = time.monotonic()
    resp = client.get("/RoboStorage/GetStockTasks", params=params)
    elapsed = time.monotonic() - started
    if resp.status_code != 200:
        return None, resp.status_code, elapsed
    try:
        return resp.json(), 200, elapsed
    except Exception:
        return None, 200, elapsed


def ids_of(rows) -> list:
    if not isinstance(rows, list):
        return []
    return [r.get("id") for r in rows if isinstance(r, dict)]


print("=" * 78)
print("1. ЧТО ИМЕННО ВОЗВРАЩАЕТ count — свежие записи или старые?")
print("=" * 78)

rows, code, elapsed = fetch({"count": 5})
if rows is None:
    print(f"Запрос не удался (HTTP {code})")
    raise SystemExit(1)

first_ids = ids_of(rows)
print(f"count=5 -> id: {first_ids}   ({elapsed:.2f} сек)")

if first_ids:
    biggest = max(first_ids)
    smallest = min(first_ids)
    print(f"\nдиапазон id: от {smallest} до {biggest}")
    print("Ориентир: в прошлом пробнике самый свежий приход имел id около 486234.")
    if biggest > 480000:
        print("=> Похоже, возвращаются СВЕЖИЕ записи (это хорошо).")
    elif biggest < 50000:
        print("=> Похоже, возвращаются САМЫЕ СТАРЫЕ записи (это плохо:")
        print("   для экрана кладовщика нужны свежие, придётся искать обходной путь).")
    else:
        print("=> Непонятно, нужен ручной взгляд на id.")

print("\n" + "=" * 78)
print("2. ЕСТЬ ЛИ ПАРАМЕТР СМЕЩЕНИЯ (постраничность)?")
print("=" * 78)
print("Если смещение работает, вторая порция будет содержать ДРУГИЕ id.\n")

OFFSET_CANDIDATES = ["skip", "offset", "start", "startRow", "from", "page", "startIndex"]

for name in OFFSET_CANDIDATES:
    rows2, code2, el2 = fetch({"count": 5, name: 5})
    if rows2 is None:
        print(f"  {name:<12} HTTP {code2} — не принят")
        continue
    second_ids = ids_of(rows2)
    if second_ids == first_ids:
        print(f"  {name:<12} игнорируется (те же id)")
    elif set(second_ids) & set(first_ids):
        print(f"  {name:<12} частично сдвинул: {second_ids}")
    else:
        print(f"  {name:<12} РАБОТАЕТ! другие id: {second_ids}")

print("\n" + "=" * 78)
print("3. МОЖНО ЛИ ЗАПРОСИТЬ КОНКРЕТНОЕ ЗАДАНИЕ ПО id?")
print("=" * 78)

if first_ids:
    target = first_ids[0]
    for name in ["id", "stockTaskId", "stk_id", "rcp_id", "receiptNumber"]:
        rows3, code3, el3 = fetch({name: target, "count": 5})
        if rows3 is None:
            print(f"  {name:<15} HTTP {code3} — не принят")
            continue
        got = ids_of(rows3)
        if got == [target]:
            print(f"  {name:<15} РАБОТАЕТ! вернул ровно нужную запись")
        elif len(got) == 1:
            print(f"  {name:<15} вернул одну запись, но другую: {got}")
        else:
            print(f"  {name:<15} игнорируется (вернул {len(got)} записей)")

print("\n" + "=" * 78)
print("4. СКОЛЬКО МОЖНО ЗАПРОСИТЬ ЗА РАЗ (скорость на разных count)")
print("=" * 78)

for n in [50, 200, 1000, 5000]:
    rows4, code4, el4 = fetch({"count": n})
    got = len(rows4) if isinstance(rows4, list) else -1
    print(f"  count={n:<6} -> получено {got:<6} за {el4:.2f} сек")

print("\nГотово. Присылайте вывод целиком — id это внутренние номера,")
print("персональных данных здесь нет.")
