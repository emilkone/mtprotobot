# MTProxy Telegram Bot (telemt) — two-server scheme

Цель: держать 5 MTProxy на VPS1 (non-RU), проверять доступность из RU через VPS2, и автоматически ротировать упавшие слоты с уведомлением в Telegram.

Основа прокси: [telemt/telemt](https://github.com/telemt/telemt).

## Компоненты

- **VPS1 (non-RU)**: `docker compose` поднимает `telemt_1..5` и `mtprotobot_app` (бот+менеджер+планировщик).
- **VPS2 (RU)**: один скрипт `checker.py`, запускается по SSH, проверяет TCP-доступность портов из РФ.

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

Сгенерируй 5 конфигов telemt и начальный `data/proxies.json`:

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
- Если слот не проходит **хотя бы один** из тестов — генерируется новый `secret32`, обновляется `telemt/configs/config_N.toml`, и перезапускается контейнер `telemt_N`.
- После ротации бот присылает обновлённые 5 ссылок.

