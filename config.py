# ==============================
# OpusGuru Anti-Scam Bot
# ==============================

# Токен бота от @BotFather
BOT_TOKEN = "8756817682:AAH2021c-Me3pDPDpWrklPUZyCfxMDIiX6A"

# Telegram API (получи на https://my.telegram.org)
# Нужно для парсинга каналов со скам-базами
API_ID = 38174721         # Вставь свой api_id
API_HASH = "81fae89bb1aa38bf21823c0fc220dd01"      # Вставь свой api_hash

# Единственный администратор бота
ADMIN_IDS = [599952947]

# Каналы со скам-базами для поиска
SCAM_CHANNELS = [
    "GID_ScamBase",
    "TonTakeScammers",
    "LiarsBase",
    "syndibase",
]

# Кэш результатов поиска (секунды)
CACHE_TTL = 3600  # 1 час

# Лимит сообщений для парсинга из каждого канала
PARSE_LIMIT = 5000
