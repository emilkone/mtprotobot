# MTProxy Telegram Bot — two-server scheme

Цель: держать 5 MTProxy на VPS1 (non-RU), проверять доступность из RU через VPS2, и автоматически ротировать упавшие слоты с уведомлением в Telegram.

Прокси: официальный образ [telegrammessenger/proxy](https://hub.docker.com/r/telegrammessenger/proxy) (Fake TLS через префикс `ee` + hex(SNI) + 32 hex в `SECRET`).

## Компоненты

- **VPS1 (non-RU)**: `docker compose` поднимает `mtproto_1..5` и `mtprotobot_app` (бот+менеджер+планировщик).
- **VPS2 (RU)**: один скрипт `checker.py`, запускается по SSH, проверяет TCP-доступность портов из РФ.

## Порт 443 и xray / VLESS Reality

Если на том же VPS уже слушает **443** (например xray с Reality), не биндите хост на 443 для MTProxy. По умолчанию слот 1 использует **4443** на хосте (в контейнере прокси слушает **443**). Список портов задаётся при генерации и должен совпадать с `docker-compose.yml`:

```bash
MTPROTO_PORTS="4443,8443,2053,2083,2096" TLS_DOMAIN=google.com VPS1_PUBLIC_IP=<IP> ./scripts/init.sh
```

Устаревшее имя переменной `TELEMT_PORTS` по-прежнему поддерживается как алиас для `MTPROTO_PORTS`.

После смены портов обновите в `docker-compose.yml` у каждого `mtproto_N` секцию `ports:` в формате `"<HOST_PORT>:443"`.

## Требования

- VPS1: Docker + Docker Compose plugin
- VPS2: Python 3
- SSH доступ с VPS1 на VPS2 по ключу

## Быстрый старт

### 1) Подготовить VPS2 (RU)

Создай пользователя (пример):

```bash
sudo useradd -m -s /bin/bash checker
```

Разреши SSH ключом и добавь публичный ключ в `~checker/.ssh/authorized_keys`.

На локальной машине (или на VPS1, где есть репозиторий) выполни:

```bash
./vps2/setup.sh <VPS2_HOST> checker <PATH_TO_SSH_KEY>
```

После этого на VPS2 должен быть `/home/checker/checker.py`.

### 2) Подготовить VPS1 (non-RU)

Склонируй репозиторий, затем:

1. Положи SSH-ключ для доступа к VPS2 сюда: `./.ssh/vps2_ssh_key` (без passphrase или с агентом; для простоты — без passphrase).
2. Создай `.env` из примера:

```bash
cp .env.example .env
```

Заполни минимум:

- `BOT_TOKEN`
- `OWNER_CHAT_ID`
- `VPS1_PUBLIC_IP`
- `VPS2_HOST`
- `VPS2_USER=checker`
- `VPS2_SSH_KEY_PATH=/run/secrets/vps2_ssh_key`

Сгенерируй `data/mtproto/slot_1..5.env` (полный `SECRET` для образа) и начальный `data/proxies.json`:

```bash
TLS_DOMAIN=google.com VPS1_PUBLIC_IP=<VPS1_PUBLIC_IP> ./scripts/init.sh
```

Запусти:

```bash
docker compose up -d --build
```

## Команды бота

- `/proxies` — показать текущие 5 ссылок
- `/status` — количество слотов в состоянии
- `/check` — проверить (local + RU) и при необходимости перегенерировать слоты

Бот отвечает только владельцу (`OWNER_CHAT_ID`).

## Как работает ротация

- Раз в `CHECK_INTERVAL_HOURS` приложение делает:
  - **local TCP check** с VPS1 на `VPS1_PUBLIC_IP:port`
  - **RU TCP check** с VPS2 (по SSH) на те же адреса
- Если слот не проходит **хотя бы один** из тестов — генерируется новый `secret32`, обновляется `data/mtproto/slot_N.env` (переменная `SECRET`), и контейнер `mtproto_N` **пересоздаётся** через `docker compose up --force-recreate` (официальный прокси читает секрет только при старте контейнера).
- После ротации бот присылает обновлённые 5 ссылок.
