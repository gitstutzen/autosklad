"""
Локальное зеркало складских заданий.

Зачем оно нужно: api1c/RoboStorage/GetStockTasks умеет только "верни последние N
записей" — без фильтров по складу и статусу, без постраничности, без выборки
по номеру. Полная выгрузка (452 000+ записей) занимает ~44 секунды, поэтому
дёргать её на каждый запрос нельзя.

При этом задание может оставаться незавершённым неделями: например, часть позиций
не приняли из-за задержки поставки, и кладовщик вернётся к этому приходу позже.
Значит, ограничиться свежим срезом нельзя — нужна вся история у себя.

Зеркало решает это: данные лежат в нашей базе, фильтры и поиск работают нормально,
экраны быстрые, а нагрузка на Stutzen — только фоновая синхронизация.
"""
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, Integer, String, Text, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class StockTaskMirror(Base):
    """Складское задание (приход от поставщика), скопированное из api1c.

    Это ЗЕРКАЛО, а не источник истины: сюда только пишет синхронизация,
    прикладной код отсюда только читает. Изменения статусов уходят в Stutzen
    через API, а не правкой этой таблицы.
    """
    __tablename__ = "stock_tasks_mirror"

    # id из api1c. Свой суррогатный ключ не заводим: id стабилен и уникален,
    # а совпадение ключей упрощает сверку с источником при разборе расхождений.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    receipt_number: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)
    document_number: Mapped[int | None] = mapped_column(BigInteger, index=True, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    status: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # ПОЧЕМУ ПОЧТИ ВСЁ NULLABLE: это зеркало чужой системы с данными с 2017 года,
    # качеством которых мы не управляем. Обязательное поле здесь означает не
    # защиту, а потерю: запись не проходит разбор и молча исчезает.
    # Так уже вышло дважды — с stock_id (потеряли 5 активных заданий)
    # и с login (потеряли 65 700 записей, 14,5% базы). Подробности
    # в app/stock_tasks.py, класс StockTask.
    stock_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    provider: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Поставщик в нижнем регистре — для поиска без учёта регистра.
    #
    # Зачем отдельное поле, а не ILIKE по provider: в SQLite (на нём идут тесты)
    # приведение регистра работает только для латиницы, кириллицу он не трогает.
    # В PostgreSQL (прод) ILIKE отработал бы верно — то есть один и тот же код
    # вёл бы себя в тестах и в проде по-разному. Это хуже обычной ошибки:
    # тесты бы врали.
    #
    # Приведение делается на стороне Python при записи (str.lower корректно
    # обрабатывает кириллицу), поэтому результат одинаков в любой базе.
    # Побочная польза: поле можно проиндексировать.
    provider_search: Mapped[str] = mapped_column(String(500), index=True, default="")
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    # login пустой у 65 700 записей — проверено на боевых данных 02.09.2026
    login: Mapped[str | None] = mapped_column(String(100), nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    comment_stock: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Когда эта строка последний раз обновлялась синхронизацией.
    # Нужно, чтобы отличать "данные свежие" от "синхронизация давно не отрабатывала".
    synced_at: Mapped[datetime] = mapped_column(DateTime)

    __table_args__ = (
        # Главный запрос экрана: незавершённые задания конкретного склада,
        # свежие сверху. Составной индекс покрывает его целиком.
        Index("ix_mirror_stock_status_created", "stock_id", "status", "created_at"),
    )


class SyncState(Base):
    """Отметки о том, когда какая синхронизация отрабатывала успешно.

    Нужны, чтобы (1) знать, актуальны ли данные, и (2) не гонять полную выгрузку
    чаще, чем нужно.
    """
    __tablename__ = "sync_state"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)  # "incremental" | "full"
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    rows_processed: Mapped[int] = mapped_column(Integer, default=0)
