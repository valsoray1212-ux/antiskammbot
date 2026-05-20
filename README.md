# 🛡 OpusGuru Anti-Scam Bot

Telegram-бот для проверки пользователей по базам мошенников.

## Структура

```
antiscam_bot/
├── bot.py           — запуск
├── config.py        — настройки
├── database.py      — SQLite база
├── parser.py        — парсер каналов (Telethon)
├── keyboards.py     — кнопки
├── requirements.txt
└── handlers/
    ├── start.py     — /start, меню
    ├── check.py     — проверка по ID / @username
    └── admin.py     — /admin панель
```

---

## Установка

```bash
pip install -r requirements.txt
```

---

## Настройка (config.py)

### 1. Токен бота
```python
BOT_TOKEN = "твой_токен_от_BotFather"
```

### 2. Telegram API (для парсинга каналов)
Зайди на https://my.telegram.org → Log in → API development tools → создай приложение.

```python
API_ID = 12345678       # числовой
API_HASH = "abcdef..."  # строка
```

### 3. ID администратора (уже настроен)
```python
ADMIN_IDS = [599952947]
```

---

## Запуск

```bash
python bot.py
```

При первом запуске Telethon попросит:
1. Ввести номер телефона аккаунта Telegram
2. Ввести код из Telegram
3. (если есть 2FA) пароль

После этого создастся файл `antiscam_session.session` — сессия сохранена, повторный вход не нужен.

---

## Как работает поиск

### 🔍 Поиск по ID
1. Ищет ID в локальной БД (ранее спарсенные данные)
2. Делает живой поиск по тексту сообщений в каналах через Telegram Search API
3. Показывает все найденные упоминания со ссылками на сообщения

### 🔎 Поиск по @username
Аналогично — сначала БД, потом живой поиск.

### Живой ввод
Если написать боту просто число (5–12 цифр) — автоматически проверит как ID.
Если написать @username — проверит как username.

---

## Админ-панель (/admin)

- **📊 Статистика** — пользователи, записи, проверки
- **🔄 Обновить базу** — запускает парсинг всех каналов (сохраняет в БД)
- **🗑 Очистить кэш** — сбрасывает кэш результатов поиска
- **📋 Логи** — последние 15 проверок

---

## Каналы-источники

- [@GID_ScamBase](https://t.me/GID_ScamBase)
- [@TonTakeScammers](https://t.me/TonTakeScammers)

Добавить новый канал — в `config.py`:
```python
SCAM_CHANNELS = [
    "GID_ScamBase",
    "TonTakeScammers",
    "НовыйКанал",
]
```
