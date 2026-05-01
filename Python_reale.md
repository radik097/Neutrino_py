# Python_reale.md

# NEUTRINO Python module для Windows 7/10/11 x32/x86

Документ описывает текущую Python-реализацию в этом репозитории: модуль `neutrino_py` с тремя публичными классами `Server`, `Client`, `Doctor`, CLI-запуском и низкоуровневым Windows/Winsock слоем через `ctypes`.

Используйте модуль только в своей лабораторной, корпоративной или иной разрешенной сети и с учетом местного законодательства.

## 1. Текущее состояние проекта

В репозитории уже добавлен рабочий Python-пакет:

```text
Neutrino_py/
├── pyproject.toml
├── Python_reale.md
├── README.md
├── LICENSE
├── src/
│   └── neutrino_py/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── core.py
│       ├── lowlevel.py
│       └── packet.py
├── tests/
│   ├── test_core.py
│   └── test_packet.py
└── scripts/
    ├── build_x86.bat
    └── smoke_test.bat
```

Публичный API модуля:

```python
from neutrino_py import Server, Client, Doctor
```

По условию проекта модуль содержит три основных класса:

- `Server` - серверная часть, принимает framed NEUTRINO-пакеты и отправляет ответ.
- `Client` - локальная клиентская часть, подключается к серверу и отправляет framed NEUTRINO-пакеты.
- `Doctor` - диагностика системы: Python, DLL, Winsock/raw socket, порты, DNS, TLS, доступ в интернет.

## 2. Назначение классов

### `Server`

Файл: `src/neutrino_py/core.py`

`Server` реализует асинхронный TCP endpoint на `asyncio`.

Текущие возможности:

- запуск на заданном `host:port`;
- прием подключений;
- чтение framed binary packets;
- декодирование пакетов через `packet.py`;
- обработка payload через handler;
- отправка framed ответа клиенту;
- корректная остановка сервера и закрытие клиентов.

Минимальный пример:

```python
import asyncio
from neutrino_py import Server

async def main():
    server = Server(host="127.0.0.1", port=8787)
    await server.serve_forever()

asyncio.run(main())
```

CLI-запуск:

```bat
python -m neutrino_py server --host 127.0.0.1 --port 8787
```

### `Client`

Файл: `src/neutrino_py/core.py`

`Client` реализует локальную клиентскую часть.

Текущие возможности:

- подключение к `Server`;
- отправка бинарного payload;
- автоматическая упаковка в NEUTRINO frame;
- проверка sequence number ответа;
- `ping()` для измерения RTT;
- закрытие соединения.

Минимальный пример:

```python
import asyncio
from neutrino_py import Client

async def main():
    client = Client(host="127.0.0.1", port=8787)
    try:
        response = await client.send(b"hello")
        print(response)
    finally:
        await client.close()

asyncio.run(main())
```

CLI-запуск:

```bat
python -m neutrino_py client --host 127.0.0.1 --port 8787 "hello"
```

### `Doctor`

Файл: `src/neutrino_py/core.py`

`Doctor` проверяет окружение и возвращает JSON-совместимый отчет.

Проверяется:

- версия Python;
- архитектура процесса: x86/x64;
- путь к интерпретатору;
- версия OpenSSL;
- наличие стандартных Python-модулей;
- наличие Windows DLL;
- доступность локальных портов;
- DNS resolution;
- TLS handshake;
- доступ в интернет по заданным target host/port;
- low-level Winsock raw socket capability.

Минимальный пример:

```python
from neutrino_py import Doctor

report = Doctor(timeout=3).run()
print(report)
```

CLI-запуск:

```bat
python -m neutrino_py doctor --timeout 3
```

## 3. Низкоуровневый Windows/C слой

Файл: `src/neutrino_py/lowlevel.py`

Низкоуровневые вызовы сделаны через стандартный Python `ctypes`, без внешних C-расширений. Это важно для Windows 7/10/11 x32/x86, потому что модуль можно запустить без компиляции `.pyd` на целевой машине.

Сейчас используются:

- `ctypes.WinDLL("ws2_32.dll")` - Winsock API;
- `ctypes.WinDLL(...)` / `ctypes.util.find_library(...)` - проверка DLL;
- `WSAStartup`;
- `WSACleanup`;
- `socket(AF_INET, SOCK_RAW, IPPROTO_ICMP)`;
- `closesocket`;
- `WSAGetLastError`.

Проверяемые DLL:

```text
ws2_32.dll
iphlpapi.dll
dnsapi.dll
crypt32.dll
bcrypt.dll
```

Raw socket probe только открывает и закрывает сокет. Он не отправляет пакеты. На Windows raw sockets обычно требуют запуск от Администратора и могут блокироваться локальной политикой безопасности или firewall.

## 4. Формат пакета

Файл: `src/neutrino_py/packet.py`

Текущий формат состоит из frame prefix и NEUTRINO packet.

Frame:

```text
length: 4 bytes, big endian
packet: N bytes
```

Packet:

```text
magic:    4 bytes, b"NTRN"
version:  1 byte
seq:      4 bytes, big endian
flags:    4 bytes, big endian
payload:  N bytes
```

Сейчас это минимальный транспортный формат для разработки Server/Client. Шифрование, мультиплексирование каналов и handshake должны добавляться следующим этапом поверх этого формата или через расширение `flags/payload`.

## 5. Установка в режиме разработки

Из корня репозитория:

```bat
cd D:\Python\NewProtocol\Neutrino_py
python -m pip install -e .
```

Если используется Codex runtime Python или другой прямой путь к интерпретатору:

```bat
"C:\path\to\python.exe" -m pip install -e .
```

Без установки можно запускать через `PYTHONPATH`:

```bat
set PYTHONPATH=D:\Python\NewProtocol\Neutrino_py\src
python -m neutrino_py doctor
```

В PowerShell:

```powershell
$env:PYTHONPATH="D:\Python\NewProtocol\Neutrino_py\src"
python -m neutrino_py doctor
```

## 6. Windows 7/10/11 x32/x86

`x32`, `x86` и `32-bit` здесь означают 32-битный Python-процесс и 32-битный `.exe`.

| ОС | Рекомендуемый Python | Комментарий |
|---|---:|---|
| Windows 7 SP1 x86 | Python 3.8.10 x86 | Практичная последняя ветка для Win7 без неофициальных патчей. |
| Windows 10 x86 | Python 3.8.10 x86 | Можно держать совместимость с Win7. |
| Windows 11 | Python x86 для x86-сборки | ОС обычно x64, но x86 Python может собрать x86 `.exe`. |

Для одного общего x86-бинарника под Windows 7/10/11 рекомендуется Python 3.8.10 x86.

Важно: запуск из 64-битного Python даст 64-битный процесс и 64-битный PyInstaller build. Для настоящей x86-сборки нужен именно 32-битный Python.

## 7. Сборка x86 `.exe`

Скрипт:

```bat
scripts\build_x86.bat
```

Что делает скрипт:

1. Переходит в корень репозитория.
2. Создает `.venv-win7-x86` через `py -3.8-32`.
3. Устанавливает `pip`, `setuptools`, `wheel`, `pyinstaller`.
4. Устанавливает пакет в editable mode.
5. Собирает `neutrino-py-x86.exe`.

Ручной вариант:

```bat
cd D:\Python\NewProtocol\Neutrino_py
py -3.8-32 -m venv .venv-win7-x86
.venv-win7-x86\Scripts\activate.bat
python -m pip install --upgrade pip setuptools wheel pyinstaller
python -m pip install -e .
pyinstaller --onefile --name neutrino-py-x86 src\neutrino_py\__main__.py
```

Проверка архитектуры:

```bat
dumpbin /headers dist\neutrino-py-x86.exe | findstr machine
```

Ожидаемо:

```text
14C machine (x86)
```

## 8. Тестирование

Запуск unit-тестов:

```bat
set PYTHONPATH=D:\Python\NewProtocol\Neutrino_py\src
python -m unittest discover -s tests
```

Smoke-test:

```bat
scripts\smoke_test.bat
```

Что уже покрыто:

- packet encode/decode;
- frame/unframe;
- `Doctor.system_info()`;
- локальный `Server` + `Client` echo round-trip.

Фактическая проверка в текущей среде:

```text
Ran 4 tests
OK
```

`Doctor` на текущей машине нашел Windows DLL и успешно открыл raw IPv4 ICMP socket через Winsock. При этом outbound TCP в sandbox-среде вернул `WinError 10013`, что означает запрет сетевого доступа политикой окружения, а не ошибку модуля.

## 9. Команды CLI

Показать справку:

```bat
python -m neutrino_py --help
```

Вывод:

```text
usage: neutrino-py [-h] {server,client,doctor} ...

positional arguments:
  {server,client,doctor}
    server              run server endpoint
    client              send one message to server
    doctor              run environment diagnostics
```

Запуск сервера:

```bat
python -m neutrino_py server --host 127.0.0.1 --port 8787
```

Отправка сообщения:

```bat
python -m neutrino_py client --host 127.0.0.1 --port 8787 "ping"
```

Диагностика:

```bat
python -m neutrino_py doctor --timeout 3
```

## 10. Что нужно реализовать следующим этапом

Текущий модуль - базовый каркас. Следующие инженерные шаги:

1. Добавить `crypto.py`:
   - X25519;
   - HKDF-SHA256;
   - AES-256-GCM;
   - Ed25519 server identity.

2. Добавить канальный слой:
   - `channels/base.py`;
   - `channels/tcp.py`;
   - `channels/ws.py`;
   - `channels/doh.py`;
   - `channels/dns_txt.py`;
   - исследовательский `channels/ntp_timing.py`.

3. Добавить `scheduler.py`:
   - probe каналов;
   - выбор канала;
   - failover;
   - round-robin chunks.

4. Расширить `Doctor`:
   - проверка firewall rules;
   - проверка прав Администратора;
   - проверка `PATH`;
   - проверка Visual C++ Redistributable x86;
   - проверка PyInstaller;
   - проверка доступности DNS/DoH endpoints;
   - экспорт отчета в `.json`.

5. Добавить серверный режим relay:
   - local TCP relay;
   - authenticated session;
   - лимиты соединений;
   - журнал диагностики.

## 11. Ограничения Windows x86

- 32-битный процесс ограничен адресным пространством, поэтому нельзя держать большие буферы.
- Windows 7 не поддерживает часть новых Windows API.
- Python 3.9+ официально не является хорошей базой для Windows 7.
- Raw sockets требуют прав Администратора и могут быть отключены политикой безопасности.
- Firewall/antivirus могут блокировать outbound TCP, raw sockets и PyInstaller `--onefile` бинарники.
- Для x86-сборки все бинарные зависимости должны иметь x86 wheels или собираться на x86 toolchain.

## 12. Git-синхронизация

Клонирование:

```bat
git clone https://github.com/radik097/Neutrino_py.git
cd Neutrino_py
```

Синхронизация:

```bat
git pull --rebase
```

Проверка изменений:

```bat
git status
git diff
```

Коммит текущего модуля:

```bat
git add Python_reale.md pyproject.toml src tests scripts
git commit -m "Add Python module prototype with diagnostics"
```

## 13. Краткий итог реализации

Сейчас проект уже можно использовать как Python-модуль:

```python
from neutrino_py import Server, Client, Doctor
```

И как CLI:

```bat
python -m neutrino_py doctor
python -m neutrino_py server
python -m neutrino_py client "hello"
```

Главная ценность текущего этапа: создана основа, на которую можно безопасно наращивать криптографию, каналы, scheduler и relay, не ломая публичный API из трех классов.

