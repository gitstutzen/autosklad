"""
Проверка полной синхронизации — самый тяжёлый режим.

Что проверяем:
  - выдержит ли машина 452 000 записей за один заход (186 МБ JSON,
    из них получаются сотни тысяч объектов в памяти);
  - попадут ли в зеркало СТАРЫЕ активные задания, которых нет в свежем срезе —
    ради них полная синхронизация и нужна;
  - попадут ли задания без склада, которые раньше терялись при разборе.

Замеряется расход памяти на каждом шаге. Если он растёт опаснее ожидаемого,
скрипт остановится сам, не доводя компьютер до свопа.

Безопасность: только чтение из Stutzen, запись в локальный файл full_sync.db.
Ни боевая база, ни Postgres не затрагиваются.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:API1C_BASE_URL="https://www.catalog.stutzen.ru/api1c"
    $env:API1C_API_KEY="ваш-ключ"
    python check_full_sync.py

Займёт около минуты. Файл full_sync.db потом можно удалить.
"""
import os
import sys
import time

os.environ["STUTZEN_READ_ONLY"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///full_sync.db"
os.environ.setdefault("JWT_SECRET", "not-used-here")
os.environ.setdefault("REDIS_URL", "redis://localhost:6399/0")
os.environ.setdefault("TRADESOFT_API_BASE_URL", "https://example.invalid/api/v1")
os.environ.setdefault("TRADESOFT_API_TOKEN", "not-used-here")

if not os.environ.get("API1C_API_KEY"):
    print("Не задана переменная API1C_API_KEY.")
    raise SystemExit(1)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from collections import Counter

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.models import Base, StockTaskMirror
from app import sync as sync_module
from app.stock_tasks import ACTIVE_STATUSES, STOCK_TASK_STATUS_NAMES

DB_PATH = "full_sync.db"
MEMORY_LIMIT_MB = 4000  # выше этого прерываемся, чтобы не уйти в своп


def memory_mb() -> float | None:
    """Сколько памяти занимает процесс. None, если измерить нечем."""
    try:
        import psutil
        return psutil.Process().memory_info().rss / 1024 / 1024
    except ImportError:
        pass
    try:
        # запасной путь для Windows без psutil
        import ctypes
        import ctypes.wintypes

        class Counters(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            return counters.WorkingSetSize / 1024 / 1024
    except Exception:
        pass
    return None


def report_memory(stage: str) -> float | None:
    used = memory_mb()
    if used is None:
        print(f"  [{stage}] измерить память нечем (pip install psutil для замеров)")
        return None
    print(f"  [{stage}] память процесса: {used:.0f} МБ")
    if used > MEMORY_LIMIT_MB:
        print(f"\nПревышен порог {MEMORY_LIMIT_MB} МБ — прерываемся, чтобы")
        print("не загнать компьютер в своп. Это и есть результат проверки:")
        print("полная синхронизация в текущем виде слишком прожорлива.")
        raise SystemExit(1)
    return used


def header(text: str) -> None:
    print("\n" + "=" * 74)
    print(text)
    print("=" * 74)


def main() -> None:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Удалён прежний {DB_PATH}, начинаем с чистого листа.")

    engine = create_engine(f"sqlite:///{DB_PATH}")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    header("ШАГ 1. Полная синхронизация")
    print("Забираем ВСЮ историю: около 452 000 записей, 186 МБ.")
    print("Это займёт примерно минуту. Только чтение.\n")

    report_memory("до начала")

    started = time.monotonic()
    with SessionLocal() as session:
        try:
            rows = sync_module.sync_full(session)
        except MemoryError:
            print("\nНе хватило памяти. Значит, выгружать всё разом нельзя —")
            print("нужна потоковая обработка. Это тоже результат.")
            raise SystemExit(1)
        except Exception as exc:
            print(f"\nСинхронизация не удалась: {type(exc).__name__}: {exc}")
            raise SystemExit(1)
    elapsed = time.monotonic() - started

    report_memory("после синхронизации")
    print(f"\nОбработано записей: {rows}, за {elapsed:.0f} сек")

    size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
    print(f"Размер локальной базы: {size_mb:.0f} МБ")

    # ---- что получилось ----
    header("ШАГ 2. Что в зеркале")

    with SessionLocal() as session:
        total = session.scalar(select(func.count()).select_from(StockTaskMirror))
        print(f"Всего записей: {total}")

        if rows != total:
            print(f"РАСХОЖДЕНИЕ: синхронизация отчиталась о {rows}, в базе {total}.")
            print("Возможно, часть записей не разобралась и была пропущена.")

        by_status = session.execute(
            select(StockTaskMirror.status, func.count())
            .group_by(StockTaskMirror.status)
            .order_by(StockTaskMirror.status)
        ).all()

        print("\nПо статусам:")
        active_total = 0
        for status, count in by_status:
            name = STOCK_TASK_STATUS_NAMES.get(status, "неизвестный")
            mark = ""
            if status in {int(s) for s in ACTIVE_STATUSES}:
                mark = "  <- активный"
                active_total += count
            print(f"  {status}: {count:>7}  {name}{mark}")
        print(f"\nИтого активных заданий: {active_total}")

    # ---- главная проверка ----
    header("ШАГ 3. Ради чего всё затевалось")
    print("Полная синхронизация нужна, чтобы увидеть СТАРЫЕ активные задания —")
    print("приостановленные приходы, ждущие задержанную поставку.\n")

    with SessionLocal() as session:
        active_rows = session.execute(
            select(StockTaskMirror.created_at, StockTaskMirror.stock_id,
                   StockTaskMirror.status, StockTaskMirror.amount)
            .where(StockTaskMirror.status.in_([int(s) for s in ACTIVE_STATUSES]))
            .order_by(StockTaskMirror.created_at)
        ).all()

        if not active_rows:
            print("Активных заданий не нашлось — это странно, стоит разобраться.")
            raise SystemExit(1)

        oldest = active_rows[0]
        newest = active_rows[-1]
        print(f"Самое старое активное задание: {oldest.created_at.date()} "
              f"(статус {oldest.status}, {STOCK_TASK_STATUS_NAMES.get(oldest.status, '?')})")
        print(f"Самое свежее активное задание: {newest.created_at.date()}")

        # сколько из них НЕ попало бы в свежий срез
        newest_ids = session.execute(
            select(StockTaskMirror.id)
            .order_by(StockTaskMirror.id.desc())
            .limit(sync_module.INCREMENTAL_COUNT)
        ).scalars().all()
        cutoff_id = min(newest_ids) if newest_ids else 0

        missed = session.scalar(
            select(func.count()).select_from(StockTaskMirror).where(
                StockTaskMirror.status.in_([int(s) for s in ACTIVE_STATUSES]),
                StockTaskMirror.id < cutoff_id,
            )
        )
        print(f"\nИз них НЕ попали бы в свежий срез ({sync_module.INCREMENTAL_COUNT} записей): "
              f"{missed}")
        print("Это те задания, которые кладовщик не увидел бы без полной синхронизации.")

        # задания без склада — раньше терялись при разборе
        no_stock = session.scalar(
            select(func.count()).select_from(StockTaskMirror).where(
                StockTaskMirror.stock_id.is_(None)
            )
        )
        print(f"\nЗаданий без склада: {no_stock}")
        if no_stock:
            print("Раньше такие записи молча выбрасывались при разборе — "
                  "теперь сохраняются.")

        by_stock = Counter(r.stock_id for r in active_rows)
        print("\nАктивные по складам:")
        for stock_id, count in sorted(by_stock.items(), key=lambda x: -x[1]):
            label = "без склада" if stock_id is None else f"склад {stock_id}"
            print(f"  {label}: {count}")

    header("ИТОГ")
    print("Полная синхронизация отработала. Сверьте числа с тем, что показала")
    print("выборка напрямую из базы: активных было 316, из них склад 2 — 112.")
    print(f"\nЛокальная база: {DB_PATH} ({size_mb:.0f} МБ, можно удалить)")


if __name__ == "__main__":
    main()
