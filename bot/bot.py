import asyncio
import json
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import CommandStart, Command
from g4f.client import Client as G4fClient

from config import BOT_TOKEN, OWNER_ID, AI_MODEL, AI_TIMEOUT
import database as db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def is_owner(user_id: int) -> bool:
    return user_id == OWNER_ID


async def get_webapp_url() -> str:
    url = db.get_setting("webapp_url")
    if url:
        return url
    return "https://yourusername.github.io/your-repo/"


async def send_ai_message(text: str) -> str:
    g4f_client = G4fClient()
    prompt = db.get_setting("ai_prompt") or "Ты вежливый помощник. Отвечай кратко."
    owner_name = db.get_setting("owner_name") or "Владелец"
    prompt = prompt.replace("OWNER_NAME", owner_name)

    try:
        response = g4f_client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": text},
            ],
            timeout=AI_TIMEOUT,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"g4f error: {e}")
        return f"Я передам {owner_name}, как только он появится"


async def notify_owner(bot: Bot, sender_name: str, sender_username: str, text: str, reply: str, is_stranger: bool):
    icon = "🔴" if is_stranger else "🟢"
    username_part = f" (@{sender_username})" if sender_username else ""
    notification = (
        f"{icon} {sender_name}{username_part} написал(а):\n"
        f"\"{text}\"\n\n"
        f"🤖 Мой ответ:\n\"{reply}\""
    )
    try:
        await bot.send_message(OWNER_ID, notification)
    except Exception as e:
        logger.error(f"Failed to notify owner: {e}")


async def main():
    db.init_db()
    logger.info("Database initialized")

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    router = Router()

    @router.message(CommandStart())
    async def cmd_start(message: Message):
        webapp_url = await get_webapp_url()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Открыть настройки", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.answer(
            "👋 Привет! Я бот-автоответчик.\n\n"
            "Я отвечаю на сообщения, когда вы не в сети.\n"
            "Настройте меня через Mini App:",
            reply_markup=kb,
        )

    @router.message(Command("settings"))
    async def cmd_settings(message: Message):
        webapp_url = await get_webapp_url()
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Открыть настройки", web_app=WebAppInfo(url=webapp_url))]
        ])
        await message.answer("Настройки автоответчика:", reply_markup=kb)

    @router.message(Command("help"))
    async def cmd_help(message: Message):
        await message.answer(
            "📖 Справка:\n\n"
            "/start — Приветствие и кнопка настроек\n"
            "/settings — Открыть Mini App\n"
            "/help — Эта справка\n\n"
            "🤖 Автоответчик отвечает на сообщения по правилам или с помощью ИИ."
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
                await message.answer(f"✅ Правило добавлено: \"{phrase}\"")
            else:
                await message.answer("❌ Заполните фразу и ответ")

        elif action == "delete_rule":
            rule_id = data.get("rule_id")
            if rule_id:
                db.delete_rule(rule_id)
                await message.answer("✅ Правило удалено")

        elif action == "test_ai":
            test_text = "Привет, как дела?"
            reply = await send_ai_message(test_text)
            await message.answer(f"🧪 Тест ИИ:\nВопрос: {test_text}\nОтвет: {reply}")

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
        rule_reply = db.match_rule(text)

        if rule_reply:
            reply = rule_reply
        else:
            reply = await send_ai_message(text)

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
