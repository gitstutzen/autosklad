"""
Пробник №2: выясняем, принимает ли GetStockTasks фильтры.

Зачем: первый пробник показал, что метод отдаёт 452 000+ записей одним ответом —
всю историю приходов. Строить на этом список заданий нельзя. Нужно понять,
можно ли попросить только нужное: конкретный склад, свежие записи, активные статусы.

Скрипт перебирает вероятные варианты имён параметров и смотрит, меняется ли
количество записей в ответе. Все запросы — GET, только чтение.

ВНИМАНИЕ: каждый неудачный вариант скачивает полный ответ (~100 МБ).
Поэтому запросы идут по одному, с ограничением по времени, а тело ответа
не разбирается целиком — считаем только размер и количество записей.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python probe_filters.py
"""
import os
import sys
import time

os.environ["STUTZEN_READ_ONLY"] = "true"

import httpx

BASE_URL = os.environ.get("API1C_BASE_URL", "https://www.catalog.stutzen.ru/api1c")
API_KEY = os.environ.get("API1C_API_KEY")

if not API_KEY:
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

# Варианты фильтров, которые стоит проверить. Имена подобраны по тому,
# как называются поля в самом ответе (stockId, status, dateCreation)
# и как назывались параметры в других методах api1c (stk_id, dtStart/dtStop).
CANDIDATES = [
    ("без параметров (базовая линия)", {}),
    ("stockId=8", {"stockId": 8}),
    ("stock_id=8", {"stock_id": 8}),
    ("stk_id=8", {"stk_id": 8}),
    ("status=1", {"status": 1}),
    ("dtStart/dtStop за сегодня", {"dtStart": "2026-08-31", "dtStop": "2026-08-31"}),
    ("dateStart/dateStop за сегодня", {"dateStart": "2026-08-31", "dateStop": "2026-08-31"}),
    ("top=10", {"top": 10}),
    ("limit=10", {"limit": 10}),
    ("count=10", {"count": 10}),
    ("deletet=0", {"deletet": 0}),
]


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=180.0, headers={"ApiKey": API_KEY})
    baseline = None

    print(f"Проверяем фильтры на {BASE_URL}/RoboStorage/GetStockTasks\n")
    print(f"{'вариант':<38} {'HTTP':<6} {'записей':>10} {'сек':>6}  вывод")
    print("-" * 90)

    for label, params in CANDIDATES:
        started = time.monotonic()
        try:
            resp = client.get("/RoboStorage/GetStockTasks", params=params)
        except Exception as exc:
            print(f"{label:<38} {'ERR':<6} {'-':>10} {'-':>6}  {type(exc).__name__}")
            continue

        elapsed = time.monotonic() - started

        if resp.status_code != 200:
            print(f"{label:<38} {resp.status_code:<6} {'-':>10} {elapsed:>6.1f}  не принят")
            continue

        try:
            data = resp.json()
            count = len(data) if isinstance(data, list) else -1
        except Exception:
            print(f"{label:<38} {resp.status_code:<6} {'?':>10} {elapsed:>6.1f}  ответ не JSON")
            continue

        if baseline is None:
            baseline = count
            verdict = "базовая линия"
        elif count < baseline * 0.95:
            verdict = f"РАБОТАЕТ: выборка меньше в {baseline / max(count, 1):.0f} раз"
        elif count == 0:
            verdict = "пусто — параметр принят, но ничего не нашлось"
        else:
            # Данные живые: за время перебора на складе создаются новые приходы,
            # поэтому счётчик может слегка вырасти. Это НЕ признак работающего фильтра.
            delta = count - baseline
            verdict = f"игнорируется (записей {'+' if delta >= 0 else ''}{delta} к базовой)"

        print(f"{label:<38} {resp.status_code:<6} {count:>10} {elapsed:>6.1f}  {verdict}")

    print("\nГотово. Присылайте эту таблицу — по ней будет понятно, как ограничивать выборку.")
    print("Если все варианты дали одинаковое число, значит фильтры не поддерживаются")
    print("и нужно запрашивать у Stutzen доработку метода.")


if __name__ == "__main__":
    main()
