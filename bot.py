import asyncio
import random
import html
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, ReactionTypeEmoji
)
from aiogram.utils.markdown import hbold, hcode
from config import BOT_TOKEN, ADMINS
from utils import (
    parse_time, get_user_mention, is_admin,
    get_random_joke, get_random_fact, get_random_quote,
    get_8ball_answer, roulette_game,
    get_weather_mock, ship_users
)

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML")
)
dp = Dispatcher()

# ─── ADMIN COMMANDS ─────────────────────────────────────────────────────────────

@dp.message(Command("ban"))
async def ban_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя: ответь на его сообщение или напиши @username.")

    reason = get_reason(message)
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        text = (
            f"🔨 <b>БАН</b>\n\n"
            f"👤 Пользователь: {get_user_mention(target)}\n"
            f"👮 Администратор: {get_user_mention(message.from_user)}\n"
            f"📝 Причина: {reason}"
        )
        await message.answer(text)
    except Exception as e:
        await message.reply(f"❌ Не удалось забанить: {e}")


@dp.message(Command("unban"))
async def unban_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя.")

    try:
        await bot.unban_chat_member(message.chat.id, target.id, only_if_banned=True)
        await message.answer(
            f"✅ <b>РАЗБАН</b>\n\n"
            f"👤 Пользователь: {get_user_mention(target)}\n"
            f"👮 Администратор: {get_user_mention(message.from_user)}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("mute"))
async def mute_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя.\nПример: /mute @user 30m причина")

    args = message.text.split()[2:] if message.reply_to_message is None else message.text.split()[1:]
    duration_str = args[0] if args else None
    duration, readable = parse_time(duration_str) if duration_str else (None, "навсегда")
    reason = get_reason(message)

    until_date = datetime.now() + timedelta(seconds=duration) if duration else None

    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        text = (
            f"🔇 <b>МУТ</b>\n\n"
            f"👤 Пользователь: {get_user_mention(target)}\n"
            f"⏱ Длительность: {readable}\n"
            f"👮 Администратор: {get_user_mention(message.from_user)}\n"
            f"📝 Причина: {reason}"
        )
        await message.answer(text)
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("unmute"))
async def unmute_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя.")

    try:
        await bot.restrict_chat_member(
            message.chat.id, target.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await message.answer(
            f"🔊 <b>РАЗМУТ</b>\n\n"
            f"👤 Пользователь: {get_user_mention(target)}\n"
            f"👮 Администратор: {get_user_mention(message.from_user)}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("kick"))
async def kick_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя.")

    reason = get_reason(message)
    try:
        await bot.ban_chat_member(message.chat.id, target.id)
        await bot.unban_chat_member(message.chat.id, target.id)
        await message.answer(
            f"👢 <b>КИК</b>\n\n"
            f"👤 Пользователь: {get_user_mention(target)}\n"
            f"👮 Администратор: {get_user_mention(message.from_user)}\n"
            f"📝 Причина: {reason}"
        )
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("warn"))
async def warn_user(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    target = await get_target_user(message)
    if not target:
        return await message.reply("⚠️ Укажи пользователя.")

    reason = get_reason(message)
    # Simple in-memory warn counter (replace with DB for production)
    if not hasattr(warn_user, "warns"):
        warn_user.warns = {}

    key = (message.chat.id, target.id)
    warn_user.warns[key] = warn_user.warns.get(key, 0) + 1
    count = warn_user.warns[key]

    text = (
        f"⚠️ <b>ПРЕДУПРЕЖДЕНИЕ {count}/3</b>\n\n"
        f"👤 Пользователь: {get_user_mention(target)}\n"
        f"👮 Администратор: {get_user_mention(message.from_user)}\n"
        f"📝 Причина: {reason}"
    )

    if count >= 3:
        try:
            await bot.ban_chat_member(message.chat.id, target.id)
            text += f"\n\n🔨 <b>Пользователь получил 3 варна и был забанен!</b>"
            warn_user.warns[key] = 0
        except:
            pass

    await message.answer(text)


@dp.message(Command("pin"))
async def pin_message(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    if not message.reply_to_message:
        return await message.reply("⚠️ Ответь на сообщение которое хочешь закрепить.")

    try:
        await bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        await message.reply("📌 Сообщение закреплено!")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("unpin"))
async def unpin_message(message: Message):
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    try:
        if message.reply_to_message:
            await bot.unpin_chat_message(message.chat.id, message.reply_to_message.message_id)
        else:
            await bot.unpin_chat_message(message.chat.id)
        await message.reply("📌 Сообщение откреплено!")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


@dp.message(Command("ro"))
async def readonly_mode(message: Message):
    """Режим только для чтения — мутит всех не-админов"""
    if not await is_admin(bot, message):
        return await message.reply("❌ Только администраторы могут использовать эту команду.")

    args = message.text.split()
    enable = len(args) < 2 or args[1].lower() not in ("off", "0", "нет")

    try:
        await bot.set_chat_permissions(
            message.chat.id,
            ChatPermissions(can_send_messages=not enable)
        )
        if enable:
            await message.answer("🔒 <b>Режим «только чтение» включён</b>\nОбычные участники не могут писать.")
        else:
            await message.answer("🔓 <b>Режим «только чтение» выключен</b>\nУчастники снова могут писать.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# ─── INFO COMMANDS ──────────────────────────────────────────────────────────────

@dp.message(Command("info"))
async def user_info(message: Message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    text = (
        f"👤 <b>Информация о пользователе</b>\n\n"
        f"🆔 ID: <code>{target.id}</code>\n"
        f"👾 Имя: {get_user_mention(target)}\n"
        f"🔤 Username: @{target.username or '—'}\n"
        f"🌐 Язык: {target.language_code or '—'}\n"
        f"🤖 Бот: {'Да' if target.is_bot else 'Нет'}"
    )
    await message.reply(text)


@dp.message(Command("chatinfo"))
async def chat_info(message: Message):
    chat = message.chat
    count = await bot.get_chat_member_count(chat.id)
    text = (
        f"💬 <b>Информация о чате</b>\n\n"
        f"🆔 ID: <code>{chat.id}</code>\n"
        f"📛 Название: {html.escape(chat.title or '—')}\n"
        f"🔤 Username: @{chat.username or '—'}\n"
        f"👥 Участников: {count}\n"
        f"📂 Тип: {chat.type}"
    )
    await message.reply(text)


@dp.message(Command("admins"))
async def list_admins(message: Message):
    admins = await bot.get_chat_administrators(message.chat.id)
    lines = []
    for a in admins:
        u = a.user
        role = "👑 Владелец" if a.status == "creator" else "🛡 Админ"
        lines.append(f"{role}: {get_user_mention(u)}")
    await message.reply("👮 <b>Администраторы чата:</b>\n\n" + "\n".join(lines))


# ─── FUN COMMANDS ───────────────────────────────────────────────────────────────

@dp.message(Command("joke"))
async def joke_cmd(message: Message):
    await message.reply(f"😂 {get_random_joke()}")


@dp.message(Command("fact"))
async def fact_cmd(message: Message):
    await message.reply(f"🧠 <b>Интересный факт:</b>\n\n{get_random_fact()}")


@dp.message(Command("quote"))
async def quote_cmd(message: Message):
    q, author = get_random_quote()
    await message.reply(f"💬 <i>{q}</i>\n\n— <b>{author}</b>")


@dp.message(Command("8ball"))
async def ball_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    question = args[1] if len(args) > 1 else "..."
    answer = get_8ball_answer()
    await message.reply(f"🎱 <b>Вопрос:</b> {html.escape(question)}\n\n<b>Ответ:</b> {answer}")


@dp.message(Command("roll"))
async def roll_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    try:
        sides = int(args[1]) if len(args) > 1 else 6
        sides = max(2, min(sides, 1000))
    except:
        sides = 6
    result = random.randint(1, sides)
    await message.reply(f"🎲 Бросаю кубик D{sides}...\n\nВыпало: <b>{result}</b>!")


@dp.message(Command("roulette"))
async def roulette_cmd(message: Message):
    if message.chat.type == "private":
        return await message.reply("🎰 Рулетка работает только в группах!")

    result, msg = roulette_game()
    await message.reply(msg)

    if result == "lose" and await is_admin(bot, message):
        pass  # don't mute admins
    elif result == "lose":
        try:
            duration = random.randint(60, 600)
            until = datetime.now() + timedelta(seconds=duration)
            await bot.restrict_chat_member(
                message.chat.id,
                message.from_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await message.answer(
                f"💀 {get_user_mention(message.from_user)} застрелился и получает мут на {duration // 60} мин!"
            )
        except:
            pass


@dp.message(Command("ship"))
async def ship_cmd(message: Message):
    args = message.text.split(maxsplit=2)
    if message.reply_to_message and len(args) < 2:
        name1 = message.from_user.first_name
        name2 = message.reply_to_message.from_user.first_name
    elif len(args) == 3:
        name1, name2 = args[1], args[2]
    elif len(args) == 2:
        name1 = message.from_user.first_name
        name2 = args[1]
    else:
        return await message.reply("💕 Использование: /ship @user1 @user2\nили ответь на сообщение")

    result = ship_users(name1, name2)
    await message.reply(result)


@dp.message(Command("rate"))
async def rate_cmd(message: Message):
    if message.reply_to_message:
        name = message.reply_to_message.from_user.first_name
    else:
        args = message.text.split(maxsplit=1)
        name = args[1] if len(args) > 1 else message.from_user.first_name

    score = random.randint(0, 100)
    bar = "█" * (score // 10) + "░" * (10 - score // 10)
    emoji = "🔥" if score >= 80 else "😊" if score >= 50 else "😐" if score >= 30 else "💀"
    await message.reply(
        f"{emoji} <b>{html.escape(name)}</b>\n\n"
        f"[{bar}] {score}/100"
    )


@dp.message(Command("coin"))
async def coin_cmd(message: Message):
    result = random.choice(["🪙 Орёл!", "🪙 Решка!"])
    await message.reply(result)


@dp.message(Command("weather"))
async def weather_cmd(message: Message):
    args = message.text.split(maxsplit=1)
    city = args[1] if len(args) > 1 else "Москва"
    result = get_weather_mock(city)
    await message.reply(result)





# ─── DIALOG (AI-like responses) ─────────────────────────────────────────────────

TRIGGERS = {
    ("привет", "хай", "здарова", "хеллоу", "добрый"): [
        "Привет! 👋 Как дела?",
        "Хай-хай! 😊",
        "О, живой! Привет!",
        "Здарова! Что стряслось? 😄",
    ],
    ("как дела", "как ты", "что делаешь", "как жизнь"): [
        "Отлично, обрабатываю команды и наслаждаюсь жизнью 🤖",
        "Норм, жду ваших /команд 😄",
        "Лучше всех! А у тебя как?",
        "Гоняю байты туда-сюда, всё хорошо 😎",
    ],
    ("спасибо", "благодарю", "пасиб", "спс"): [
        "Пожалуйста! 😊",
        "Всегда рад помочь!",
        "Не за что! Обращайся 🤝",
        "Это моя работа 🫡",
    ],
    ("бот", "ты бот", "ты человек"): [
        "Я — бот. Но бот с характером! 🤖✨",
        "Бот, но умный! 😄",
        "Искусственный интеллект на вашей службе 🛡",
    ],
    ("помощь", "помоги", "что умеешь", "команды"): [
        "Напиши /help и я всё расскажу! 📋",
    ],
    ("скучно", "нечего делать", "развлеки"): [
        "Попробуй /joke — там смешные анекдоты! 😂",
        "Сыграй в /roulette — если не страшно 😈",
        "Попроси /fact — узнаешь что-то новое 🧠",
        "Посмотри /8ball — он знает будущее 🎱",
    ],
}

@dp.message(F.text & ~F.text.startswith("/"))
async def dialog_handler(message: Message):
    text = message.text.lower()

    # Check if bot is mentioned or it's private chat
    is_private = message.chat.type == "private"
    bot_user = await bot.get_me()
    is_mentioned = bot_user.username and f"@{bot_user.username.lower()}" in text

    if not (is_private or is_mentioned):
        # In groups only respond to triggers without mention sometimes
        if not any(t in text for triggers in TRIGGERS for t in triggers):
            return

    for triggers, responses in TRIGGERS.items():
        if any(t in text for t in triggers):
            await message.reply(random.choice(responses))
            return

    # Default witty responses
    defaults = [
        "Интересная мысль... 🤔",
        "Хм, не знаю что ответить 😅",
        "Звучит как план! 🫡",
        "Ок, принято 👍",
        "Серьёзно? Расскажи подробнее! 👀",
        "А, понял тебя! Или нет? 😅",
        "Это ты мне? Я просто бот, но стараюсь 🤖",
        "Может лучше сыграем в /roulette? 😈",
    ]
    if is_private or is_mentioned:
        await message.reply(random.choice(defaults))


# ─── HELP ───────────────────────────────────────────────────────────────────────

@dp.message(CommandStart())
@dp.message(Command("help"))
async def help_cmd(message: Message):
    text = (
        "🤖 <b>Привет! Я чат-бот с суперспособностями!</b>\n\n"

        "👮 <b>Команды администратора:</b>\n"
        "/ban — забанить пользователя\n"
        "/unban — разбанить\n"
        "/mute [время] — замутить (30s/5m/2h/1d)\n"
        "/unmute — размутить\n"
        "/kick — кикнуть из чата\n"
        "/warn — выдать предупреждение (3 = бан)\n"
        "/pin — закрепить сообщение\n"
        "/unpin — открепить сообщение\n"
        "/ro [off] — режим только чтения\n\n"

        "ℹ️ <b>Информация:</b>\n"
        "/info — инфо о пользователе\n"
        "/chatinfo — инфо о чате\n"
        "/admins — список администраторов\n\n"

        "🎮 <b>Развлечения:</b>\n"
        "/joke — анекдот\n"
        "/fact — интересный факт\n"
        "/quote — цитата великих\n"
        "/8ball [вопрос] — магический шар\n"
        "/roll [стороны] — бросить кубик\n"
        "/roulette — русская рулетка 😈\n"
        "/ship [имя1] [имя2] — совместимость\n"
        "/rate [имя] — оценить кого-угодно\n"
        "/coin — орёл или решка\n"
        "/weather [город] — погода\n"

        "💬 <b>Диалог:</b>\nПросто напиши мне в личку или упомяни @меня в группе!"
    )
    await message.reply(text)


# ─── HELPERS ────────────────────────────────────────────────────────────────────

async def get_target_user(message: Message):
    """Get target user from reply or args"""
    if message.reply_to_message:
        return message.reply_to_message.from_user

    args = message.text.split()
    if len(args) < 2:
        return None

    username = args[1].lstrip("@")
    try:
        member = await bot.get_chat_member(message.chat.id, f"@{username}")
        return member.user
    except:
        pass

    # Try user_id
    try:
        uid = int(args[1])
        member = await bot.get_chat_member(message.chat.id, uid)
        return member.user
    except:
        return None


def get_reason(message: Message) -> str:
    args = message.text.split()
    start = 3 if not message.reply_to_message else 2
    if len(args) >= start:
        # skip time arg if present
        candidate = args[start - 1] if start - 1 < len(args) else ""
        if candidate and any(candidate.endswith(u) for u in ["s", "m", "h", "d"]):
            return " ".join(args[start:]) or "Не указана"
        return " ".join(args[start - 1:]) or "Не указана"
    return "Не указана"


async def main():
    print("🤖 Бот запускается...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
