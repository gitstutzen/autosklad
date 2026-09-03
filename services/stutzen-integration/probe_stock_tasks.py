"""
Пробник: один раз сходить в боевой api1c на ЧТЕНИЕ и показать, что реально приходит.

Зачем: код разбора ответа пишется по документации, а документация может расходиться
с реальностью. Прежде чем строить на предположениях, стоит посмотреть настоящий ответ.

Безопасность:
  - только GET-запросы, ничего не меняется;
  - режим только чтения включён принудительно внутри скрипта;
  - ключ берётся из переменной окружения, в вывод не попадает;
  - по умолчанию запрашивается 1 запись, чтобы не тянуть лишнего.

Запуск (из папки services/stutzen-integration, окружение активировано):

    Windows PowerShell:
        $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
        $env:API1C_API_KEY="ваш-ключ"
        python probe_stock_tasks.py

    Linux/macOS:
        API1C_BASE_URL=... API1C_API_KEY=... python probe_stock_tasks.py

Результат сохраняется в probe_output.json — этот файл НЕ коммитить,
в нём боевые данные.
"""
import json
import os
import sys

# Принудительно включаем режим только чтения ещё до импорта клиента —
# даже случайный вызов записи из этого скрипта будет заблокирован.
os.environ["STUTZEN_READ_ONLY"] = "true"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import httpx

BASE_URL = os.environ.get("API1C_BASE_URL", "https://www.catalog.stutzen.ru/api1c")
API_KEY = os.environ.get("API1C_API_KEY")

if not API_KEY:
    print("Не задана переменная API1C_API_KEY. См. инструкцию в начале файла.")
    raise SystemExit(1)


def show(title: str, data) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)
    text = json.dumps(data, ensure_ascii=False, indent=2)
    # печатаем только начало, чтобы не залить консоль
    print(text[:3000] + ("\n... (обрезано)" if len(text) > 3000 else ""))


def describe_shape(data, prefix: str = "") -> None:
    """Показывает структуру ответа: какие поля есть и какого они типа.
    Это важнее самих значений — по этому мы будем писать разбор."""
    if isinstance(data, dict):
        for key, value in data.items():
            kind = type(value).__name__
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}: {kind}")
                if isinstance(value, list) and value:
                    describe_shape(value[0], prefix + "  [0]. ")
                elif isinstance(value, dict):
                    describe_shape(value, prefix + "  ")
            else:
                preview = str(value)[:40]
                print(f"{prefix}{key}: {kind} = {preview}")
    elif isinstance(data, list):
        print(f"{prefix}(список из {len(data)} элементов)")
        if data:
            describe_shape(data[0], prefix + "  [0]. ")


def main() -> None:
    client = httpx.Client(base_url=BASE_URL, timeout=20.0, headers={"ApiKey": API_KEY})

    print(f"Обращаемся к {BASE_URL} (только чтение)")

    try:
        resp = client.get("/RoboStorage/GetStockTasks")
    except Exception as exc:
        print(f"\nЗапрос не удался: {type(exc).__name__}: {exc}")
        print("Проверьте адрес, ключ и доступность сети.")
        raise SystemExit(1)

    print(f"HTTP {resp.status_code}")

    if resp.status_code != 200:
        print("Тело ответа (первые 1000 символов):")
        print(resp.text[:1000])
        raise SystemExit(1)

    try:
        data = resp.json()
    except Exception:
        print("Ответ не является JSON. Первые 1000 символов:")
        print(resp.text[:1000])
        raise SystemExit(1)

    show("ОБРАЗЕЦ ОТВЕТА", data)

    print("\n" + "=" * 70)
    print("СТРУКТУРА ОТВЕТА (какие поля и типы)")
    print("=" * 70)
    describe_shape(data)

    with open("probe_output.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("\nПолный ответ сохранён в probe_output.json (не коммитить — там боевые данные)")


if __name__ == "__main__":
    main()
