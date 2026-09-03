"""
Справочники статусов из базы RoboStorages (MS SQL).

Названия статусов задания хранятся в таблице StockTasksStatus и через api1c
не отдаются. Десктоп-программа подтягивает их запросом при каждом открытии
списка приходов. Этот скрипт делает то же самое.

БЕЗОПАСНОСТЬ. Работаем против боевой базы, тестового контура нет:
  - выполняются только заранее прописанные SELECT-запросы;
  - произвольный SQL передать нельзя — запросы заданы константами;
  - соединение открывается в режиме только чтения, autocommit выключен,
    в конце делается rollback;
  - реквизиты берутся из переменных окружения, в файле их нет.

Запрашиваем только справочники и агрегаты — ни одной строки с данными
заказов, клиентов или сотрудников.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:MSSQL_SERVER="адрес-сервера"
    $env:MSSQL_PORT="1433"
    $env:MSSQL_DATABASE="ar_stutzen"
    $env:MSSQL_USER="пользователь"
    $env:MSSQL_PASSWORD="пароль"
    python fetch_status_reference.py

Нужен драйвер. Проще всего:
    pip install pymssql

Если соединение не устанавливается — запустите diagnose_mssql.py,
он подберёт рабочие порт и версию протокола.

Переменные живут только в текущем окне PowerShell и нигде не сохраняются.
"""
import os
import sys

SERVER = os.environ.get("MSSQL_SERVER")
DATABASE = os.environ.get("MSSQL_DATABASE", "ar_stutzen")
USER = os.environ.get("MSSQL_USER")
PASSWORD = os.environ.get("MSSQL_PASSWORD")
PORT = int(os.environ.get("MSSQL_PORT", "1433"))

# Версия протокола TDS. Подобрана диагностикой 02.09.2026: сервер принимает
# только 7.0, на 7.1-7.4 и на версии по умолчанию рвёт соединение с ошибкой
# "TDS server connection failed". Это протокол времён SQL Server 2000 —
# либо сервер старый, либо настроен консервативно.
# Если однажды перестанет работать, запустите diagnose_mssql.py: он переберёт
# варианты заново.
TDS_VERSION = os.environ.get("MSSQL_TDS_VERSION", "7.0")

# Кодировка. На старом протоколе кириллица иногда приходит искажённой —
# тогда помогает CP1251, обычная кодировка русских баз того поколения.
CHARSET = os.environ.get("MSSQL_CHARSET", "UTF-8")

if not all([SERVER, USER, PASSWORD]):
    print("Не заданы реквизиты подключения. См. инструкцию в начале файла.")
    print("Нужны: MSSQL_SERVER, MSSQL_USER, MSSQL_PASSWORD (и при желании MSSQL_DATABASE).")
    raise SystemExit(1)


# --------------------------------------------------------------------------
# Разрешённые запросы. Список закрыт: произвольный SQL сюда не попадёт.
# Все запросы — SELECT по справочникам и агрегаты, без строк с данными заказов.
# --------------------------------------------------------------------------
QUERIES = [
    (
        "СПРАВОЧНИК СТАТУСОВ ЗАДАНИЯ (StockTasksStatus)",
        "SELECT [Id], [StatusName] FROM [dbo].[StockTasksStatus] ORDER BY [Id]",
        "Ради этого всё и затевалось: расшифровка статусов 1-6.",
    ),
    (
        "СПРАВОЧНИК СТАТУСОВ ПОЗИЦИИ (PositionsStorageStatus)",
        "SELECT [Id], [StatusName] FROM [dbo].[PositionsStorageStatus] ORDER BY [Id]",
        "Проверим заодно наши догадки про статусы позиции (1-6).",
    ),
    (
        "СКОЛЬКО ЗАДАНИЙ В КАЖДОМ СТАТУСЕ",
        "SELECT [Status], COUNT(*) AS [Cnt] FROM [dbo].[StockTasks] "
        "WHERE [Deletet] = 1 GROUP BY [Status] ORDER BY [Status]",
        "Сверка с тем, что показал api1c.",
    ),
    (
        "АКТИВНЫЕ ЗАДАНИЯ ПО СКЛАДАМ",
        "SELECT [StockId], COUNT(*) AS [Cnt] FROM [dbo].[StockTasks] "
        "WHERE [Deletet] = 1 AND [Status] IN (1, 2, 5, 6) "
        "GROUP BY [StockId] ORDER BY COUNT(*) DESC",
        "Проверим, совпадает ли с картиной из зеркала.",
    ),
    (
        "СПРАВОЧНИК СКЛАДОВ (StocksMap)",
        "SELECT TOP 30 * FROM [dbo].[StocksMap]",
        "Названия складов вместо номеров. Единственный запрос, где берутся все "
        "колонки — состав таблицы заранее неизвестен, просмотрите перед отправкой.",
    ),
]


def connect():
    """Открывает соединение. Пробуем pymssql, при неудаче pyodbc."""
    try:
        import pymssql
        return pymssql.connect(
            server=SERVER, port=PORT, user=USER, password=PASSWORD,
            database=DATABASE, timeout=30, login_timeout=15,
            tds_version=TDS_VERSION,
            charset=CHARSET,    # названия статусов на кириллице
            autocommit=False,   # ничего не зафиксируется, даже если что-то пойдёт не так
        ), f"pymssql, TDS {TDS_VERSION}"
    except ImportError:
        pass

    try:
        import pyodbc
    except ImportError:
        print("Не найден драйвер для MS SQL.")
        print("Установите любой из двух:")
        print("    pip install pymssql        (проще, дополнительных установок не нужно)")
        print("    pip install pyodbc         (нужен ODBC Driver 18 от Microsoft)")
        raise SystemExit(1)

    connection_string = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={SERVER},{PORT};"
        f"DATABASE={DATABASE};UID={USER};PWD={PASSWORD};"
        f"TrustServerCertificate=yes;Encrypt=no;Timeout=30"
    )
    return pyodbc.connect(connection_string, autocommit=False), "pyodbc"


def run() -> None:
    try:
        connection, driver = connect()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Не удалось подключиться: {type(exc).__name__}: {exc}")
        print("\nВозможные причины: неверные реквизиты, сервер недоступен,")
        print("подключения с этого адреса не разрешены.")
        raise SystemExit(1)

    print(f"Подключились к базе {DATABASE} (драйвер {driver}). Только чтение.\n")

    if "7.0" in driver:
        print("Примечание: используется старая версия протокола TDS 7.0 —")
        print("единственная, которую принимает этот сервер. Если названия статусов")
        print("придут искажёнными (кракозябрами), попробуйте другую кодировку:")
        print('    $env:MSSQL_CHARSET="CP1251"')
        print()

    try:
        for title, sql, why in QUERIES:
            print("=" * 74)
            print(title)
            print(why)
            print("=" * 74)

            cursor = connection.cursor()
            try:
                cursor.execute(sql)
                columns = [d[0] for d in cursor.description]
                rows = cursor.fetchall()
            except Exception as exc:
                print(f"  Запрос не выполнился: {type(exc).__name__}: {exc}")
                print("  (возможно, таблицы с таким именем нет — это тоже результат)\n")
                continue
            finally:
                cursor.close()

            if not rows:
                print("  Пусто.\n")
                continue

            widths = [
                max(len(str(col)), max((len(str(r[i])) for r in rows), default=0))
                for i, col in enumerate(columns)
            ]
            header = "  " + "  ".join(str(c).ljust(widths[i]) for i, c in enumerate(columns))
            print(header)
            print("  " + "-" * (len(header) - 2))
            for row in rows:
                print("  " + "  ".join(str(row[i]).ljust(widths[i]) for i in range(len(columns))))
            print(f"  ({len(rows)} строк)\n")
    finally:
        # Ничего не меняли, но откатываем явно — на случай, если драйвер
        # открыл транзакцию сам.
        try:
            connection.rollback()
        except Exception:
            pass
        connection.close()

    print("=" * 74)
    print("Готово. В базе ничего не менялось: выполнялись только SELECT.")
    print("\nПрисылайте вывод. Справочники статусов и счётчики отправлять безопасно —")
    print("это просто числа и названия. Таблицу складов просмотрите перед отправкой:")
    print("состав её колонок заранее неизвестен, там могут оказаться адреса.")


if __name__ == "__main__":
    run()
