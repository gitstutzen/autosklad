"""
Пробник №5: какой параметр ждёт GetStockTaskPositions?

Задача: выяснить, как запросить позиции конкретного задания. Без этого экран
"что внутри прихода" не заработает.

Почему это неочевидно: в ответе GetStockTasks есть сразу несколько похожих полей —
id, documentNumber, receiptNumber, rcp_id, stk_id. При этом stk_id во ВСЕХ записях
равен нулю, хотя параметр метода в справочнике называется именно stk_id.

Рабочая гипотеза: связь идёт через documentNumber. Основание — SQL-запрос
из десктоп-версии (FormStock.cs):

    [PositionsStorage].[dcc_id] = [StockTasks].[DocumentNumber]

то есть позиции привязаны к номеру документа, а не к id задания.

Скрипт берёт несколько свежих заданий и для каждого пробует разные параметры,
пока не найдёт тот, что вернёт непустой список позиций.

Только чтение. Запросы маленькие и быстрые.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python probe_task_positions.py
"""
import os

os.environ["STUTZEN_READ_ONLY"] = "true"

import httpx

BASE_URL = os.environ.get("API1C_BASE_URL", "https://www.catalog.stutzen.ru/api1c")
API_KEY = os.environ.get("API1C_API_KEY")

if not API_KEY:
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

client = httpx.Client(base_url=BASE_URL, timeout=60.0, headers={"ApiKey": API_KEY})

# Имена параметров, которые стоит проверить.
PARAM_NAMES = ["stk_id", "id", "documentNumber", "dcc_id", "receiptNumber", "rcp_id", "stockTaskId"]

# Из каких полей задания брать значение для подстановки.
VALUE_FIELDS = ["id", "documentNumber", "receiptNumber"]


def fetch_positions(param_name: str, value):
    try:
        resp = client.get("/RoboStorage/GetStockTaskPositions", params={param_name: value})
    except Exception as exc:
        return None, f"ошибка сети: {type(exc).__name__}"
    if resp.status_code != 200:
        return None, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
    except Exception:
        return None, "ответ не JSON"
    if isinstance(data, list):
        return data, f"{len(data)} позиций"
    return data, f"не список: {type(data).__name__}"


print("Берём несколько свежих заданий...")
resp = client.get("/RoboStorage/GetStockTasks", params={"count": 10})
if resp.status_code != 200:
    print(f"Не удалось получить задания: HTTP {resp.status_code}")
    raise SystemExit(1)

tasks = resp.json()
if not tasks:
    print("Заданий не вернулось.")
    raise SystemExit(1)

print(f"Получено {len(tasks)} заданий. Пробуем найти рабочий параметр.\n")

found = []

for task in tasks[:3]:
    print("=" * 78)
    print(f"Задание: id={task.get('id')}, documentNumber={task.get('documentNumber')}, "
          f"receiptNumber={task.get('receiptNumber')}, статус={task.get('status')}")
    print("=" * 78)

    for param_name in PARAM_NAMES:
        for value_field in VALUE_FIELDS:
            value = task.get(value_field)
            if value is None:
                continue
            data, note = fetch_positions(param_name, value)
            got_positions = isinstance(data, list) and len(data) > 0
            mark = "  <== РАБОТАЕТ" if got_positions else ""
            print(f"  {param_name:<15} = {value_field:<15} ({value:<12}) -> {note}{mark}")
            if got_positions:
                found.append((param_name, value_field, data))
    print()

    if found:
        print("Рабочее сочетание найдено, дальше искать не нужно.\n")
        break

if not found:
    print("=" * 78)
    print("НИ ОДНО СОЧЕТАНИЕ НЕ ВЕРНУЛО ПОЗИЦИЙ")
    print("=" * 78)
    print("Возможные причины:")
    print("  - у свежих заданий ещё нет позиций (проверьте задание постарше);")
    print("  - метод ждёт параметр с другим именем;")
    print("  - метод требует дополнительных параметров.")
    raise SystemExit(0)

param_name, value_field, sample = found[0]
print("=" * 78)
print("РЕЗУЛЬТАТ")
print("=" * 78)
print(f"Параметр:            {param_name}")
print(f"Значение брать из:   поле '{value_field}' задания")
print(f"Позиций в примере:   {len(sample)}")

print("\n" + "=" * 78)
print("СТРУКТУРА ОДНОЙ ПОЗИЦИИ (имена полей и типы)")
print("=" * 78)
first = sample[0]
if isinstance(first, dict):
    for key, value in first.items():
        kind = type(value).__name__
        preview = str(value)[:45]
        print(f"  {key}: {kind} = {preview}")

print("\nПрисылайте раздел РЕЗУЛЬТАТ и СТРУКТУРУ — по ним напишем разбор ответа.")
print("Значения полей можно затереть, если среди них попадутся данные клиентов.")
