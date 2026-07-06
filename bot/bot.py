import asyncio
import json
import logging
from collections import defaultdict

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import (
    Message, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup,
    BusinessConnection
)
from aiogram.filters import CommandStart, Command
from config import BOT_TOKEN, OWNER_ID
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

active_connections: dict[int, str] = defaultdict(str)


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def get_webapp_url() -> str:
    url = db.get_setting("webapp_url")
    if url:
        return url
    return "https://vladst6001.github.io/telegram-autoresponder/"


async def send_ai_message(text: str) -> str:
    owner_name = db.get_setting("owner_name") or "Владелец"
    return f"Я передам {owner_name}, как только он появится"


async def notify_owner(bot_instance, sender_name, sender_username, text, reply, is_stranger):
    icon = "\U0001f534" if is_stranger else "\U0001f7e2"
    username_part = f" (@{sender_username})" if sender_username else ""
    notification = (
        f"{icon} {sender_name}{username_part} написал(а):\n"
        f'"{text}"\n\n'
        f"🤖 Мой ответ:\n"
        f'"{reply}"'
    )
    try:
        await bot_instance.send_message(OWNER_ID, notification)
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")


async def generate_reply(text: str) -> str:
    rule_reply = db.match_rule(text)
    if rule_reply:
        return rule_reply
    return await send_ai_message(text)


async def main():
    db.init_db()
    logger.info("Database initialized")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    router = Router()

    @router.business_connection()
    async def on_business_connection(connection: BusinessConnection):
        if connection.user.id == OWNER_ID:
            active_connections[OWNER_ID] = connection.id
            logger.info(f"Business connected: {connection.id}")

    @router.message(CommandStart())
    async def cmd_start(message: Message):
        if not is_owner(message.from_user.id):
            enabled = db.get_setting("enabled")
            if enabled == "true":
                reply = await generate_reply("привет")
                await message.reply(reply)
                return
        webapp_url = await get_webapp_url()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\u2699\ufe0f Открыть настройки", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.answer(
            "👋 Привет! Я бот-автоответчик.\n\n"
            "Я отвечаю на сообщения, когда вы не в сети.\n"
            "Настройте меня через Mini App:",
            reply_markup=kb,
        )

    @router.message(Command("settings"))
    async def cmd_settings(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("❌ У вас нет доступа к настройкам.")
            return
        webapp_url = await get_webapp_url()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="\u2699\ufe0f Открыть настройки", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.answer("Настройки автоответчика:", reply_markup=kb)

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        if not is_owner(message.from_user.id):
            await message.answer("🤖 Я — помощник владельца. Чем могу помочь?")
            return
        status = "✅ Подключён" if active_connections.get(OWNER_ID) else "❌ Не подключён"
        await message.answer(
            "📖 Справка:\n\n"
            "/start — Приветствие и кнопка настроек\n"
            "/settings — Открыть Mini App\n"
            "/help — Эта справка\n\n"
            "🤖 Автоответчик отвечает на сообщения по правилам или с помощью ИИ.\n\n"
            f"📡 Business: {status}"
        )

    @router.message(F.web_app_data)
    async def handle_webapp_data(message: Message):
        if not is_owner(message.from_user.id):
            return
        try:
            data = json.loads(message.web_app_data.data)
        except json.JSONDecodeError:
            await message.answer("❌ Ошибка данных")
            return
        action = data.get("action")
        if action == "get_settings":
            settings = db.get_all_settings()
            rules = db.get_all_rules()
            await message.answer(json.dumps({"settings": settings, "rules": rules}, ensure_ascii=False))
        elif action == "save_settings":
            settings = data.get("settings", {})
            for key, value in settings.items():
                db.set_setting(key, value)
            if "whitelist_users" in settings:
                usernames = [u.strip().lstrip("@") for u in settings["whitelist_users"].split(",") if u.strip()]
                db.set_whitelist([hash(u) for u in usernames])
            if "blacklist_users" in settings:
                usernames = [u.strip().lstrip("@") for u in settings["blacklist_users"].split(",") if u.strip()]
                db.set_blacklist([hash(u) for u in usernames])
            await message.answer("✅ Настройки сохранены")
        elif action == "add_rule":
            phrase = data.get("phrase", "").strip()
            answer = data.get("answer", "").strip()
            match_type = data.get("match_type", "exact")
            if phrase and answer:
                db.add_rule(phrase, answer, match_type)
                await message.answer(f'✅ Правило добавлено: "{phrase}"')
            else:
                await message.answer("❌ Заполните фразу и ответ")
        elif action == "delete_rule":
            rule_id = data.get("rule_id")
            if rule_id:
                db.delete_rule(rule_id)
                await message.answer("✅ Правило удалено")
        elif action == "test_ai":
            await message.answer("⚠️ ИИ временно недоступен. Работают правила.")

    @router.message(F.business_connection)
    async def handle_business_message(message: Message):
        if not message.business_connection_id:
            return
        if message.from_user and message.from_user.id == OWNER_ID:
            return
        enabled = db.get_setting("enabled")
        if enabled != "true":
            return
        reply_mode = db.get_setting("reply_mode")
        user_id = message.from_user.id if message.from_user else 0
        username = (message.from_user.username or "") if message.from_user else ""
        if reply_mode == "blacklist":
            blacklist = db.get_blacklist()
            if user_id in blacklist or hash(username.lower()) in blacklist:
                return
        elif reply_mode == "whitelist":
            whitelist = db.get_whitelist()
            if user_id not in whitelist and hash(username.lower()) not in whitelist:
                return
        text = message.text or ""
        if not text:
            return
        reply = await generate_reply(text)
        await message.answer(reply, business_connection_id=message.business_connection_id)
        notifications = db.get_setting("notifications")
        if notifications == "true":
            sender_name = (message.from_user.first_name or "Пользователь") if message.from_user else "Пользователь"
            is_stranger = reply_mode == "strangers"
            await notify_owner(bot, sender_name, username, text, reply, is_stranger)

    @router.message(F.private)
    async def handle_private_message(message: Message):
        if is_owner(message.from_user.id):
            return
        enabled = db.get_setting("enabled")
        if enabled != "true":
            return
        reply_mode = db.get_setting("reply_mode")
        user_id = message.from_user.id
        username = message.from_user.username or ""
        if reply_mode == "blacklist":
            blacklist = db.get_blacklist()
            if user_id in blacklist or hash(username.lower()) in blacklist:
                return
        elif reply_mode == "whitelist":
            whitelist = db.get_whitelist()
            if user_id not in whitelist and hash(username.lower()) not in whitelist:
                return
        text = message.text or ""
        reply = await generate_reply(text)
        await message.reply(reply)
        notifications = db.get_setting("notifications")
        if notifications == "true":
            sender_name = message.from_user.first_name or "Пользователь"
            is_stranger = reply_mode == "strangers"
            await notify_owner(bot, sender_name, username, text, reply, is_stranger)

    async def health_handler(request):
        return web.Response(text="OK")

    app = web.Application()
    app.router.add_get("/health", health_handler)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 10000)
    await site.start()
    logger.info("Health server started on port 10000")
    dp.include_router(router)
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
