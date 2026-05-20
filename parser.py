"""
Парсер скам-каналов через Telethon (MTProto API).
Ищет упоминания ID и @username в сообщениях каналов.
"""

import re
import logging
from datetime import datetime
from typing import Optional

from telethon import TelegramClient
from telethon.tl.types import MessageEntityMention, MessageEntityMentionName
from telethon.errors import FloodWaitError

import database as db
from config import API_ID, API_HASH, SCAM_CHANNELS, PARSE_LIMIT

logger = logging.getLogger(__name__)

# Паттерны для извлечения ID и username из текста
RE_ID = re.compile(r'\b(\d{5,12})\b')
RE_USERNAME = re.compile(r'@([a-zA-Z][a-zA-Z0-9_]{3,31})')
RE_TG_LINK = re.compile(r't\.me/([a-zA-Z][a-zA-Z0-9_]{3,31})')


def get_client() -> TelegramClient:
    return TelegramClient("antiscam_session", API_ID, API_HASH)


async def parse_channel(channel: str, limit: int = PARSE_LIMIT) -> int:
    """
    Парсит канал и сохраняет упоминания мошенников в БД.
    Возвращает количество новых записей.
    """
    saved = 0
    async with get_client() as client:
        try:
            async for message in client.iter_messages(channel, limit=limit):
                if not message.text:
                    continue

                text = message.text
                date_str = message.date.isoformat() if message.date else ""

                # Ищем @username через entities (самый точный способ)
                usernames = []
                ids_from_entities = []

                if message.entities:
                    for ent in message.entities:
                        if isinstance(ent, MessageEntityMention):
                            uname = text[ent.offset:ent.offset + ent.length].strip("@")
                            usernames.append(uname)
                        elif isinstance(ent, MessageEntityMentionName):
                            ids_from_entities.append(str(ent.user_id))

                # Ищем через regex как fallback
                regex_usernames = RE_USERNAME.findall(text)
                regex_ids = RE_ID.findall(text)
                link_usernames = RE_TG_LINK.findall(text)

                all_usernames = list(set(usernames + regex_usernames + link_usernames))
                all_ids = list(set(ids_from_entities + regex_ids))

                # Если в одном сообщении есть и username и ID — сохраняем связанно
                if all_usernames and all_ids:
                    for uname in all_usernames:
                        for tid in all_ids:
                            db.save_scammer(
                                telegram_id=tid,
                                username=uname.lower(),
                                mention=f"@{uname}",
                                source_channel=channel,
                                message_text=text[:500],
                                message_id=message.id,
                                message_date=date_str,
                            )
                            saved += 1
                else:
                    # Сохраняем отдельно
                    for uname in all_usernames:
                        db.save_scammer(
                            telegram_id="",
                            username=uname.lower(),
                            mention=f"@{uname}",
                            source_channel=channel,
                            message_text=text[:500],
                            message_id=message.id,
                            message_date=date_str,
                        )
                        saved += 1

                    for tid in all_ids:
                        db.save_scammer(
                            telegram_id=tid,
                            username="",
                            mention=tid,
                            source_channel=channel,
                            message_text=text[:500],
                            message_id=message.id,
                            message_date=date_str,
                        )
                        saved += 1

        except FloodWaitError as e:
            logger.warning(f"FloodWait {e.seconds}s on channel {channel}")
        except Exception as e:
            logger.error(f"Error parsing channel {channel}: {e}")

    return saved


async def parse_all_channels() -> dict:
    """Парсит все активные каналы из БД."""
    import database as db
    channels = db.get_channels(active_only=True)
    results = {}
    for ch in channels:
        username = ch["username"]
        logger.info(f"Parsing channel: {username}")
        count = await parse_channel(username)
        db.update_channel_parsed(username, count)
        results[username] = count
        logger.info(f"  Saved {count} records from {username}")
    return results


async def search_in_channels_live(query: str) -> list:
    """
    Живой поиск по каналам через Telegram Search API.
    """
    import database as db
    channels = db.get_channels(active_only=True)
    results = []
    query_clean = query.strip("@").lower()

    async with get_client() as client:
        for ch in channels:
            channel = ch["username"]
            try:
                async for message in client.iter_messages(channel, search=query_clean, limit=20):
                    if not message.text:
                        continue
                    results.append({
                        "channel": channel,
                        "message_id": message.id,
                        "text": message.text[:600],
                        "date": message.date.strftime("%d.%m.%Y") if message.date else "—",
                        "link": f"https://t.me/{channel}/{message.id}",
                    })
            except Exception as e:
                logger.error(f"Live search error in {channel}: {e}")

    return results


async def resolve_user_id(user_id: int) -> Optional[dict]:
    """Пытается получить информацию о пользователе по ID через Telethon."""
    try:
        async with get_client() as client:
            entity = await client.get_entity(user_id)
            return {
                "id": entity.id,
                "username": getattr(entity, "username", None),
                "first_name": getattr(entity, "first_name", None),
                "last_name": getattr(entity, "last_name", None),
            }
    except Exception:
        return None
