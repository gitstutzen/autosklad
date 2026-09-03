"""
Сквозная проверка: вся цепочка на настоящих данных.

Что проверяем:
    Stutzen -> синхронизация -> зеркало -> список заданий -> позиции задания

До сих пор части проверялись по отдельности (разбор ответа, фильтры зеркала,
преобразование позиции). Здесь впервые видно, работает ли всё вместе.

Безопасность:
  - только чтение, ничего не меняется в Stutzen;
  - режим только чтения включается принудительно внутри скрипта;
  - данные пишутся в локальный файл smoke.db, не в Postgres и не в боевую базу;
  - Docker и токены не нужны.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python smoke_check.py

Файл smoke.db после проверки можно удалить, он в .gitignore.
"""
import os
import sys
import time

# Порядок важен: переменные задаём ДО импорта модулей приложения,
# они читают их при импорте.
os.environ["STUTZEN_READ_ONLY"] = "true"
os.environ.setdefault("DATABASE_URL", "sqlite:///smoke.db")
os.environ.setdefault("JWT_SECRET", "not-used-here")
os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "not-used-here")

if not os.environ.get("API1C_API_KEY"):
    print("Не задана переменная API1C_API_KEY. См. инструкцию в начале файла.")
    raise SystemExit(1)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, StockTaskMirror
from app import sync as sync_module
from app import stock_tasks_service as svc
from app.api1c_client import Api1cClient
from app.task_positions import parse_positions

DB_PATH = "smoke.db"


def header(text: str) -> None:
    print("\n" + "=" * 74)
    print(text)
    print("=" * 74)


def main() -> None:
    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # ---- шаг 1: синхронизация ----
    header("ШАГ 1. Синхронизация из Stutzen в локальное зеркало")
    print(f"Забираем свежий срез заданий (count={sync_module.INCREMENTAL_COUNT}, только чтение)...")

    started = time.monotonic()
    with SessionLocal() as session:
        try:
            count = sync_module.sync_incremental(session)
        except Exception as exc:
            print(f"\nСинхронизация не удалась: {type(exc).__name__}: {exc}")
            print("Проверьте адрес, ключ и доступность сети.")
            raise SystemExit(1)
    elapsed = time.monotonic() - started
    print(f"Записей обработано: {count}, за {elapsed:.1f} сек")

    if count == 0:
        print("\nStutzen не вернул ни одной записи — дальше проверять нечего.")
        raise SystemExit(1)

    # ---- шаг 2: что попало в зеркало ----
    header("ШАГ 2. Что теперь в зеркале")
    with SessionLocal() as session:
        total = session.query(StockTaskMirror).count()
        print(f"Всего заданий в зеркале: {total}")

        # распределение по складам среди активных
        from collections import Counter
        active_rows = [
            t for t in session.query(StockTaskMirror).all()
            if t.status in (1, 2, 5, 6)
        ]
        by_stock = Counter(t.stock_id for t in active_rows)
        print(f"Из них активных (статусы 1, 2, 5, 6): {len(active_rows)}")
        if by_stock:
            print("\nАктивные по складам:")
            for stock_id, cnt in sorted(by_stock.items(), key=lambda x: -x[1])[:10]:
                print(f"  склад {stock_id}: {cnt}")

    if not by_stock:
        print("\nАктивных заданий не нашлось — проверять список и позиции не на чем.")
        print("Это возможно: все свежие приходы уже закрыты. Попробуйте позже.")
        raise SystemExit(0)

    # ---- шаг 3: выборка через сервис ----
    target_stock = by_stock.most_common(1)[0][0]
    header(f"ШАГ 3. Список активных заданий склада {target_stock}")

    with SessionLocal() as session:
        tasks = svc.list_tasks(session, stock_id=target_stock, limit=5)
        if not tasks:
            print("Сервис вернул пустой список — расхождение с шагом 2, стоит разобраться.")
            raise SystemExit(1)

        print(f"{'id':>8}  {'док.номер':>10}  {'статус':>6}  {'сумма':>12}  поставщик")
        print("-" * 74)
        for t in tasks:
            provider_short = (t.provider or "")[:35]
            print(f"{t.id:>8}  {t.document_number:>10}  {t.status:>6}  "
                  f"{t.amount:>12.2f}  {provider_short}")

        sample_task = tasks[0]

    # ---- шаг 4: позиции задания ----
    header(f"ШАГ 4. Позиции задания {sample_task.id}")
    print(f"Запрашиваем по dcc_id = {sample_task.document_number} "
          f"(поле document_number задания, НЕ его id)")

    payload = Api1cClient().get_stock_task_positions(
        document_number=sample_task.document_number
    )
    if not isinstance(payload, list):
        print(f"Ожидался список, пришло: {type(payload).__name__}")
        raise SystemExit(1)

    positions = parse_positions(payload)
    print(f"\nПозиций получено: {len(payload)}, разобрано успешно: {len(positions)}")

    if len(payload) != len(positions):
        print(f"ВНИМАНИЕ: {len(payload) - len(positions)} строк не разобрались — "
              f"стоит посмотреть, чем они отличаются.")

    if positions:
        print(f"\n{'артикул':<16} {'ожид':>5} {'факт':>5} {'ост':>5}  наименование")
        print("-" * 74)
        for p in positions[:10]:
            print(f"{p.article:<16} {p.quantity:>5} {p.quantity_fact:>5} "
                  f"{p.remaining:>5}  {p.name[:30]}")
        if len(positions) > 10:
            print(f"... и ещё {len(positions) - 10}")
    else:
        print("\nУ этого задания нет позиций. Это не обязательно ошибка —")
        print("приход мог быть создан, но ещё не наполнен.")

    # ---- итог ----
    header("ИТОГ")
    print("Цепочка отработала целиком:")
    print("  Stutzen -> синхронизация -> зеркало -> список заданий -> позиции")
    print(f"\nЛокальная база: {DB_PATH} (можно удалить)")
    print("В Stutzen ничего не менялось: режим только чтения был включён.")


if __name__ == "__main__":
    main()
