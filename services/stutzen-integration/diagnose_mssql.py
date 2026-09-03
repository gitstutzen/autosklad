"""
Диагностика подключения к MS SQL.

Десктоп-программа к базе подключается, а pymssql — нет. Обычные причины:

  1. Нестандартный порт. В .NET он пишется через запятую в адресе:
     "Data Source=1.2.3.4,1435". Если из строки взяли только адрес,
     клиент пойдёт на стандартный 1433 и не достучится.
  2. Версия протокола TDS. Библиотека pymssql по умолчанию просит свежую
     версию; старые SQL Server её не понимают и рвут соединение.
  3. Драйвер. pyodbc с официальным драйвером Microsoft ведёт себя ближе
     к .NET, чем pymssql.

Скрипт проверяет всё это по очереди и говорит, что сработало.
Ничего не читает и не пишет — только устанавливает соединение и закрывает.

Запуск (из папки services/stutzen-integration, окружение активировано):

    $env:MSSQL_SERVER="адрес"          # только адрес, БЕЗ порта
    $env:MSSQL_PORT="1433"             # если знаете порт — укажите
    $env:MSSQL_DATABASE="ar_stutzen"
    $env:MSSQL_USER="пользователь"
    $env:MSSQL_PASSWORD="пароль"
    python diagnose_mssql.py
"""
import os
import socket
import time

SERVER = os.environ.get("MSSQL_SERVER")
DATABASE = os.environ.get("MSSQL_DATABASE", "ar_stutzen")
USER = os.environ.get("MSSQL_USER")
PASSWORD = os.environ.get("MSSQL_PASSWORD")
KNOWN_PORT = os.environ.get("MSSQL_PORT")

if not all([SERVER, USER, PASSWORD]):
    print("Не заданы MSSQL_SERVER, MSSQL_USER, MSSQL_PASSWORD.")
    raise SystemExit(1)

if "," in SERVER or "\\" in SERVER:
    print(f"ВНИМАНИЕ: в MSSQL_SERVER есть запятая или слэш ({SERVER}).")
    print("Укажите только адрес, а порт отдельно в MSSQL_PORT.\n")

# Порты: сначала указанный, затем стандартный и несколько частых нестандартных.
PORTS = []
if KNOWN_PORT:
    PORTS.append(int(KNOWN_PORT))
PORTS += [p for p in (1433, 1434, 1435, 14330, 14333) if p not in PORTS]


def header(text: str) -> None:
    print("\n" + "=" * 72)
    print(text)
    print("=" * 72)


# --------------------------------------------------------------------------
header("ШАГ 1. Какие порты вообще открыты")
# --------------------------------------------------------------------------
print("Проверяем, отвечает ли сервер на этих портах (без входа в базу).\n")

open_ports = []
for port in PORTS:
    started = time.monotonic()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((SERVER, port))
        elapsed = (time.monotonic() - started) * 1000
        print(f"  порт {port:<6} ОТКРЫТ  ({elapsed:.0f} мс)")
        open_ports.append(port)
    except socket.timeout:
        print(f"  порт {port:<6} нет ответа (таймаут)")
    except OSError as exc:
        print(f"  порт {port:<6} закрыт ({exc.__class__.__name__})")
    finally:
        sock.close()

if not open_ports:
    print("\nНи один порт не отвечает. Скорее всего:")
    print("  - подключения разрешены только с определённых адресов,")
    print("    и ваш компьютер в этот список не входит;")
    print("  - либо порт нестандартный — посмотрите строку _connection")
    print("    в LocalDb.cs целиком, там может быть 'адрес,ПОРТ'.")
    print("\nЕсли десктоп-программа работает с этого же компьютера,")
    print("значит порт другой — ищите его в строке подключения.")
    raise SystemExit(1)

print(f"\nОткрыты порты: {open_ports}")

# --------------------------------------------------------------------------
header("ШАГ 2. Вход в базу через pymssql, разные версии протокола")
# --------------------------------------------------------------------------

TDS_VERSIONS = [None, "7.4", "7.3", "7.2", "7.1", "7.0"]
success = None

try:
    import pymssql

    for port in open_ports:
        for tds in TDS_VERSIONS:
            label = f"порт {port}, TDS {tds or 'по умолчанию'}"
            kwargs = dict(
                server=SERVER, port=port, user=USER, password=PASSWORD,
                database=DATABASE, timeout=10, login_timeout=10,
            )
            if tds:
                kwargs["tds_version"] = tds
            try:
                connection = pymssql.connect(**kwargs)
                connection.close()
                print(f"  {label:<38} ПОЛУЧИЛОСЬ")
                success = ("pymssql", port, tds)
                break
            except Exception as exc:
                message = str(exc)[:60].replace("\n", " ")
                print(f"  {label:<38} нет ({message})")
        if success:
            break
except ImportError:
    print("  pymssql не установлен, пропускаем (pip install pymssql)")

# --------------------------------------------------------------------------
if not success:
    header("ШАГ 3. Вход через pyodbc")
    print("Официальный драйвер Microsoft ведёт себя ближе к .NET-программе.\n")
    try:
        import pyodbc

        available = [d for d in pyodbc.drivers() if "SQL Server" in d]
        if not available:
            print("  Драйверов SQL Server не установлено.")
            print("  Скачать: 'ODBC Driver for SQL Server' с сайта Microsoft.")
        else:
            print(f"  Найдены драйверы: {available}\n")
            for driver in available:
                for port in open_ports:
                    label = f"{driver}, порт {port}"
                    connection_string = (
                        f"DRIVER={{{driver}}};SERVER={SERVER},{port};"
                        f"DATABASE={DATABASE};UID={USER};PWD={PASSWORD};"
                        f"TrustServerCertificate=yes;Encrypt=no;Timeout=10"
                    )
                    try:
                        connection = pyodbc.connect(connection_string, timeout=10)
                        connection.close()
                        print(f"  {label:<45} ПОЛУЧИЛОСЬ")
                        success = ("pyodbc", port, driver)
                        break
                    except Exception as exc:
                        message = str(exc)[:60].replace("\n", " ")
                        print(f"  {label:<45} нет ({message})")
                if success:
                    break
    except ImportError:
        print("  pyodbc не установлен (pip install pyodbc)")

# --------------------------------------------------------------------------
header("ИТОГ")
# --------------------------------------------------------------------------

if success:
    driver, port, extra = success
    print(f"Рабочее сочетание: {driver}, порт {port}, вариант {extra}")
    print("\nЧтобы основной скрипт заработал, задайте порт:")
    print(f'    $env:MSSQL_PORT="{port}"')
    print("и запустите fetch_status_reference.py — я поправлю его под этот вариант,")
    print("пришлите этот вывод.")
else:
    print("Подключиться не удалось ни одним способом.")
    print("\nСамое вероятное: доступ к базе разрешён только с определённых адресов.")
    print("Десктоп-программа на складе работает изнутри разрешённой сети,")
    print("а ваш компьютер снаружи — тогда никакие настройки клиента не помогут.")
    print("\nПроверить просто: запустите десктоп-программу на ЭТОМ компьютере.")
    print("Если она тоже не подключается — дело в доступе, а не в скрипте.")
    print("\nЗапасной путь: посмотреть названия статусов прямо в программе,")
    print("в колонке статуса на экране приёмки.")
