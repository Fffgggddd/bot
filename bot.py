import asyncio
import logging
import aiosqlite
from aiogram import Router, F, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN       = "8608э397551:AAE-8Kt72CfS_2zJVi3gO8mfyKw7S2OsGeQ"       # @BotFather
ADMIN_ID        = 8786590613                         # Твой Telegram ID (@userinfobot)
NOTIFY_GROUP_ID = 5213781096                         # ID группы уведомлений (или = ADMIN_ID)
TON_WALLET      = "UQC1-vfn2v8m350ax_UDKxxI5F8gAyFiGjfaERtK1QXX7qFE"       # Твой TON адрес
ADMIN_USERNAME  = "@CiteMsk"                 # Твой username для ссылки "Написать"
PAYMENT_USERNAME = "@citemsk"

DATABASE_PATH = "shop.db"
BOT_NAME      = "🌸 Price"

WELCOME_TEXT = (
    "💕 <b>Привет, милый!</b>\n\n"
    "Рада видеть тебя здесь~ 🥰\n"
    "Выбери что тебя интересует — я всё устрою ✨\n\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "💎 <b>Принимаю оплату:</b>\n"
    "  ⭐ Telegram Stars\n"
    "  💙 TON Coins\n"
    "  💰 Рубли\n"
    "  💵 USDT\n"
    "  🖼 NFT / Буст\n"
    "━━━━━━━━━━━━━━━━━━\n"
    "📌 Работаю только по <b>предоплате</b>!"
)

CATEGORIES = {
    "real":         "🔥 В реальной жизни",
    "video_call":   "📹 Видеозвонки",
    "video_custom": "🎬 Видео по запросу",
    "private":      "🔑 Приватный доступ",
    "roleplay":     "🎭 Ролевые игры и виртуал",
    "exclusive":    "💎 Эксклюзив",
}

CURRENCIES = {
    "stars": "⭐ Telegram Stars",
    "ton":   "💙 TON Coins",
    "rub":   "💰 Рубли",
    "usdt":  "💵 USDT",
    "nft":   "🖼 NFT / Буст",
}

CURRENCY_LABELS = {
    "stars": "⭐ Stars",
    "ton":   "💙 TON",
    "rub":   "💰 Рублей",
    "usdt":  "💵 USDT",
}


async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                name        TEXT    NOT NULL,
                description TEXT,
                price_stars INTEGER NOT NULL,
                price_ton   REAL    NOT NULL,
                price_rub   INTEGER NOT NULL,
                price_usdt  REAL    NOT NULL,
                discount    INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                sort_order  INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id        INTEGER NOT NULL,
                username       TEXT,
                first_name     TEXT,
                service_id     INTEGER NOT NULL,
                service_name   TEXT    NOT NULL,
                payment_method TEXT    NOT NULL,
                amount         TEXT    NOT NULL,
                status         TEXT    DEFAULT 'pending',
                created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        await _seed_services(db)


async def _seed_services(db):
    cur = await db.execute("SELECT COUNT(*) FROM services")
    if (await cur.fetchone())[0] > 0:
        return

    services = [
        ("real",         "🚶 Встретиться (погулять/сходить куда-то)", "Встречаемся, гуляем, проводим время вместе 💕",                           1000,  11.0,  1150,  10.0, 1),
        ("real",         "💋 Минет",                                   "Время обсудим~ ⏰",                                                        2500,  30.0,  2900,  25.0, 2),
        ("real",         "🔥 Потрахаемся",                             "Дорого т.к. я девственница. Как лишусь — сделаю дешевле 💎",              20000, 270.0, 23000, 200.0, 3),
        ("video_call",   "🍑 Встать раком",                            "3 минуты 🔥",                                                              500,   6.6,   580,   5.0,  1),
        ("video_call",   "💃 Тверк",                                   "3 минуты 🍑",                                                              150,   1.9,   175,   1.5,  2),
        ("video_call",   "📞 Индивидуальный звонок",                   "Общаться / играть вместе — 45 минут 💕",                                   500,   6.6,   580,   5.0,  3),
        ("video_custom", "😈 Глубокий минет (резиновый хуй)",         "1 минута. Больше время — больше оплата 🔥",                               300,   3.9,   350,   3.0,  1),
        ("video_custom", "💦 Сквирт в кружок",                        "Спецэффект для тебя 😏",                                                  750,   9.9,   870,   8.0,  2),
        ("video_custom", "📸 Сесть на камеру (крупным планом)",       "То что ты хочешь увидеть 👀",                                              350,   4.6,   405,   3.5,  3),
        ("private",      "🔑 Приватный доступ — 1 неделя",            "Доступ к приватному контенту на 7 дней",                                   300,   3.3,   350,   3.0,  1),
        ("private",      "🔑 Приватный доступ — 2 недели",            "Доступ к приватному контенту на 14 дней",                                  500,   5.3,   580,   5.0,  2),
        ("private",      "🔑 Приватный доступ — 1 месяц",             "Доступ к приватному контенту на 30 дней",                                  700,   9.2,   810,   7.0,  3),
        ("private",      "♾️ Приватный доступ — навсегда",            "Вечный доступ к приватному контенту 💎",                                  3000,  39.8,  3450,  30.0, 4),
        ("roleplay",     "💬 Виртуал (1 час)",                        "Ролевая игра по переписке 🔥",                                             1000,  6.6,   1150,  10.0, 1),
        ("roleplay",     "👑 В роли Госпожи (45 минут)",              "Я командую, ты подчиняешься 😈",                                           1000,  6.6,   1150,  10.0, 2),
        ("roleplay",     "🐾 В роли Рабыни (45 минут)",               "Полное подчинение 🔥",                                                     1000,  6.6,   1150,  10.0, 3),
        ("exclusive",    "💍 Твоя личная девушка (навсегда)",         "Я твоя и только твоя 💕 Полный эксклюзив",                                 4000,  39.8,  4600,  40.0, 1),
    ]
    await db.executemany(
        "INSERT INTO services (category,name,description,price_stars,price_ton,price_rub,price_usdt,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        services
    )
    await db.commit()


async def get_services_by_category(category: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM services WHERE category=? AND is_active=1 ORDER BY sort_order", (category,)
        )
        return await cur.fetchall()


async def get_service(service_id: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services WHERE id=?", (service_id,))
        return await cur.fetchone()


async def get_all_services():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services ORDER BY category, sort_order")
        return await cur.fetchall()


async def update_service_discount(service_id: int, discount: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE services SET discount=? WHERE id=?", (discount, service_id))
        await db.commit()


async def toggle_service(service_id: int, is_active: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE services SET is_active=? WHERE id=?", (is_active, service_id))
        await db.commit()


async def update_service_price(service_id: int, field: str, value):
    if field not in {"price_stars", "price_ton", "price_rub", "price_usdt"}:
        return
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(f"UPDATE services SET {field}=? WHERE id=?", (value, service_id))
        await db.commit()


async def create_order(user_id, username, first_name, service_id, service_name, payment_method, amount):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (user_id,username,first_name,service_id,service_name,payment_method,amount) VALUES (?,?,?,?,?,?,?)",
            (user_id, username, first_name, service_id, service_name, payment_method, amount)
        )
        await db.commit()
        return cur.lastrowid


async def get_orders(limit: int = 10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
        return await cur.fetchall()


async def get_orders_count():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        return (await cur.fetchone())[0]


def _apply_discount(base, discount: int, is_int: bool = False):
    result = base * (1 - discount / 100)
    return max(1, int(result)) if is_int else round(result, 2)


def calc_price(svc, currency: str) -> str:
    discount = svc["discount"] or 0
    if currency == "stars":
        base  = svc["price_stars"]
        final = _apply_discount(base, discount, is_int=True)
        note  = f" <s>{base}</s>" if discount else ""
        return f"⭐ <b>{final} Stars</b>{note}"
    elif currency == "ton":
        base  = svc["price_ton"]
        final = _apply_discount(base, discount)
        note  = f" <s>{base}</s>" if discount else ""
        return f"💙 <b>{final} TON</b>{note}"
    elif currency == "rub":
        base  = svc["price_rub"]
        final = _apply_discount(base, discount, is_int=True)
        note  = f" <s>{base}</s>" if discount else ""
        return f"💰 <b>{final} ₽</b>{note}"
    elif currency == "usdt":
        base  = svc["price_usdt"]
        final = _apply_discount(base, discount)
        note  = f" <s>{base}</s>" if discount else ""
        return f"💵 <b>{final} USDT</b>{note}"
    return ""


def get_final_price(svc, currency: str):
    discount = svc["discount"] or 0
    if currency == "stars":
        return _apply_discount(svc["price_stars"], discount, is_int=True)
    elif currency == "ton":
        return _apply_discount(svc["price_ton"], discount)
    elif currency == "rub":
        return _apply_discount(svc["price_rub"], discount, is_int=True)
    elif currency == "usdt":
        return _apply_discount(svc["price_usdt"], discount)
    return 0


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг",  callback_data="catalog")
    kb.button(text="💳 Способы оплаты", callback_data="payment_info")
    kb.button(text="📋 Правила",        callback_data="rules")
    kb.button(text="📩 Написать мне",   url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    kb.adjust(2, 2)
    return kb.as_markup()


def categories_kb():
    kb = InlineKeyboardBuilder()
    for key, name in CATEGORIES.items():
        kb.button(text=name, callback_data=f"cat:{key}")
    kb.button(text="🏠 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def services_kb(services: list, category: str, page: int = 0, per_page: int = 5):
    kb     = InlineKeyboardBuilder()
    total  = len(services)
    start  = page * per_page
    end    = min(start + per_page, total)

    for svc in services[start:end]:
        disc = f"  🏷 -{svc['discount']}%" if svc["discount"] else ""
        kb.button(text=f"{svc['name']}{disc}", callback_data=f"svc:{svc['id']}")

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_page:{category}:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"cat_page:{category}:{page+1}"))
    if nav:
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text="↩️ К категориям", callback_data="catalog"))
    kb.adjust(1)
    return kb.as_markup()


def service_detail_kb(service_id: int, category: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Купить",          callback_data=f"buy:{service_id}")
    kb.button(text="↩️ К списку",        callback_data=f"cat:{category}")
    kb.adjust(1)
    return kb.as_markup()


def currency_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for key, name in CURRENCIES.items():
        kb.button(text=name, callback_data=f"pay:{service_id}:{key}")
    kb.adjust(2)
    kb.row(InlineKeyboardButton(text="↩️ Отмена", callback_data=f"svc:{service_id}"))
    return kb.as_markup()


def confirm_payment_kb(service_id: int, currency: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил(а)", callback_data=f"confirm:{service_id}:{currency}")
    kb.button(text="↩️ Назад",        callback_data=f"buy:{service_id}")
    kb.adjust(1)
    return kb.as_markup()


def stars_method_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="🎁 Отправить подарок", callback_data=f"stars_method:{service_id}:gift")
    kb.button(text="🖼 Отправить NFT",     callback_data=f"stars_method:{service_id}:nft")
    kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=f"buy:{service_id}"))
    return kb.as_markup()


def stars_confirm_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я отправил(а)", callback_data=f"confirm:{service_id}:stars")
    kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=f"buy:{service_id}"))
    return kb.as_markup()


def back_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="↩️ В админ-панель", callback_data="adm:main")
    return kb.as_markup()


def admin_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Все услуги",        callback_data="adm:services")
    kb.button(text="🏷 Установить скидку", callback_data="adm:discount_pick")
    kb.button(text="💰 Изменить цену",     callback_data="adm:price_pick")
    kb.button(text="🔀 Вкл / Выкл",       callback_data="adm:toggle_pick")
    kb.button(text="📊 Статистика",        callback_data="adm:stats")
    kb.button(text="📦 Последние заказы",  callback_data="adm:orders")
    kb.adjust(2)
    return kb.as_markup()


def admin_services_kb(services: list, action: str, page: int = 0, per_page: int = 8):
    kb    = InlineKeyboardBuilder()
    total = len(services)
    start = page * per_page
    end   = min(start + per_page, total)

    for svc in services[start:end]:
        status = "" if svc["is_active"] else "🚫 "
        disc   = f" [{svc['discount']}%]" if svc["discount"] else ""
        kb.button(
            text=f"{status}{svc['name'][:32]}{disc}",
            callback_data=f"adm:{action}:{svc['id']}"
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"adm:{action}_page:{page-1}"))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"adm:{action}_page:{page+1}"))
    if nav:
        kb.row(*nav)

    kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data="adm:main"))
    kb.adjust(1)
    return kb.as_markup()


def discount_values_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for val in [0, 5, 10, 15, 20, 25, 30, 40, 50]:
        label = "❌ Убрать скидку" if val == 0 else f"-{val}%"
        kb.button(text=label, callback_data=f"adm:set_disc:{service_id}:{val}")
    kb.button(text="↩️ Назад", callback_data="adm:discount_pick")
    kb.adjust(3)
    return kb.as_markup()


def price_currency_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for label, cur in [("⭐ Stars", "stars"), ("💙 TON", "ton"), ("💰 Рубли", "rub"), ("💵 USDT", "usdt")]:
        kb.button(text=label, callback_data=f"adm:set_price:{service_id}:{cur}")
    kb.button(text="↩️ Назад", callback_data="adm:price_pick")
    kb.adjust(2)
    return kb.as_markup()


router = Router()


class AdminStates(StatesGroup):
    waiting_price = State()


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


def fmt_username(user) -> str:
    return f"@{user.username}" if user.username else f"id{user.id}"


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        f"<b>{BOT_NAME}</b>\n\n{WELCOME_TEXT}",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        f"<b>{BOT_NAME}</b>\n\n{WELCOME_TEXT}",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "rules")
async def cb_rules(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг", callback_data="catalog")
    kb.button(text="🏠 Главное меню",  callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        "📌 <b>Правила работы</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "1️⃣ Работаю <b>только по предоплате</b>\n"
        "2️⃣ После оплаты пиши в личку — договоримся о деталях\n"
        "3️⃣ Фоточки <b>не продаю</b> 🚫\n"
        "4️⃣ Все вопросы — <b>только в ЛС</b>\n"
        "5️⃣ Нет ответа 30 минут — напомни мне\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💕 Спасибо что выбрал(а) меня~",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "payment_info")
async def cb_payment_info(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг", callback_data="catalog")
    kb.button(text="🏠 Главное меню",  callback_data="main_menu")
    kb.adjust(1)
    await callback.message.edit_text(
        "💳 <b>Способы оплаты</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⭐ <b>Telegram Stars</b> — прямо в боте ({PAYMENT_USERNAME})\n"
        "💙 <b>TON Coins</b> — перевод на кошелёк\n"
        "💰 <b>Рубли</b> — перевод в Telegram\n"
        "💵 <b>USDT</b> — через @CryptoBot\n"
        "🖼 <b>NFT / Буст</b> — обсудим в ЛС\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "📌 Работаю только по <b>предоплате</b>!",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "catalog")
async def cb_catalog(callback: CallbackQuery):
    await callback.message.edit_text(
        "🛍 <b>Каталог услуг</b>\n\nВыбери категорию~ 💕",
        reply_markup=categories_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat:"))
async def cb_category(callback: CallbackQuery):
    category = callback.data.split(":")[1]
    services = await get_services_by_category(category)
    cat_name = CATEGORIES.get(category, category)
    if not services:
        await callback.answer("😔 Услуги временно недоступны", show_alert=True)
        return
    await callback.message.edit_text(
        f"<b>{cat_name}</b>\n\n💕 Выбери услугу:",
        reply_markup=services_kb(services, category),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_page:"))
async def cb_category_page(callback: CallbackQuery):
    _, category, page_str = callback.data.split(":")
    services = await get_services_by_category(category)
    cat_name = CATEGORIES.get(category, category)
    await callback.message.edit_text(
        f"<b>{cat_name}</b>\n\n💕 Выбери услугу:",
        reply_markup=services_kb(services, category, int(page_str)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("svc:"))
async def cb_service_detail(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return

    discount  = svc["discount"] or 0
    disc_text = f"\n🏷 <b>Скидка: -{discount}%</b>" if discount else ""

    await callback.message.edit_text(
        f"<b>{svc['name']}</b>{disc_text}\n\n"
        f"📝 {svc['description']}\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Цены:</b>\n"
        f"  {calc_price(svc, 'stars')}\n"
        f"  {calc_price(svc, 'ton')}\n"
        f"  {calc_price(svc, 'rub')}\n"
        f"  {calc_price(svc, 'usdt')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 Работаю по предоплате!",
        reply_markup=service_detail_kb(svc["id"], svc["category"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    disc      = svc["discount"] or 0
    disc_text = f"\n🏷 Скидка: <b>-{disc}%</b>" if disc else ""
    await callback.message.edit_text(
        f"💳 <b>Оплата</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>{disc_text}\n\n"
        f"Выбери способ оплаты 👇",
        reply_markup=currency_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":stars"))
async def cb_pay_stars(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    stars = get_final_price(svc, "stars")
    await callback.message.edit_text(
        f"⭐ <b>Оплата звёздами</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{stars} Stars</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Выбери способ отправки 👇\n\n"
        f"🎁 <b>Подарок</b> — открой профиль {PAYMENT_USERNAME},\n"
        f"нажми «Подарить Stars» и укажи сумму\n\n"
        f"🖼 <b>NFT</b> — отправь NFT на {PAYMENT_USERNAME}\n"
        f"━━━━━━━━━━━━━━━━━━",
        reply_markup=stars_method_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("stars_method:"))
async def cb_stars_method(callback: CallbackQuery):
    parts = callback.data.split(":")
    service_id_str, method = parts[1], parts[2]
    svc = await get_service(int(service_id_str))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    stars = get_final_price(svc, "stars")

    if method == "gift":
        instruction = (
            f"🎁 <b>Как отправить подарок:</b>\n\n"
            f"1️⃣ Открой профиль {PAYMENT_USERNAME}\n"
            f"2️⃣ Нажми «⭐ Подарить Stars»\n"
            f"3️⃣ Укажи сумму: <b>{stars} Stars</b>\n"
            f"4️⃣ Подтверди отправку"
        )
    else:
        instruction = (
            f"🖼 <b>Как отправить NFT:</b>\n\n"
            f"1️⃣ Открой профиль {PAYMENT_USERNAME}\n"
            f"2️⃣ Отправь NFT эквивалентный <b>{stars} Stars</b>\n"
            f"3️⃣ Подтверди отправку"
        )

    await callback.message.edit_text(
        f"⭐ <b>Оплата звёздами</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{stars} Stars</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{instruction}\n\n"
        f"После отправки нажми кнопку ниже 👇\n"
        f"━━━━━━━━━━━━━━━━━━",
        reply_markup=stars_confirm_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":ton"))
async def cb_pay_ton(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "ton")
    await callback.message.edit_text(
        f"💙 <b>Оплата через TON</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} TON</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📤 Отправь <code>{amount}</code> TON на адрес:\n"
        f"<code>{TON_WALLET}</code>\n\n"
        f"⚠️ В комментарии укажи свой username!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "ton"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":rub"))
async def cb_pay_rub(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "rub")
    await callback.message.edit_text(
        f"💰 <b>Оплата в рублях</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} ₽</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📲 Переведи <b>{amount} ₽</b> пользователю:\n"
        f"👉 {PAYMENT_USERNAME}\n\n"
        f"⚠️ В комментарии укажи свой username!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "rub"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":usdt"))
async def cb_pay_usdt(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("😔 Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "usdt")
    await callback.message.edit_text(
        f"💵 <b>Оплата в USDT</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} USDT</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📲 Переведи через @CryptoBot → Отправить → USDT\n"
        f"👉 {PAYMENT_USERNAME}\n\n"
        f"⚠️ В комментарии укажи свой username!\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "usdt"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":nft"))
async def cb_pay_nft(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    await callback.message.edit_text(
        f"🖼 <b>Оплата NFT / Буст</b>\n\n"
        f"Услуга: <b>{svc['name'] if svc else '?'}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Напиши мне в ЛС — обсудим детали 💕\n"
        f"👉 {ADMIN_USERNAME}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"После отправки нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"] if svc else 0, "nft"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm:"))
async def cb_confirm_payment(callback: CallbackQuery, bot: Bot):
    _, service_id_str, currency = callback.data.split(":")
    svc      = await get_service(int(service_id_str))
    user     = callback.from_user
    username = fmt_username(user)

    labels = {"ton": "TON", "rub": "₽", "usdt": "USDT", "nft": "NFT/Буст"}
    if svc and currency in ("ton", "rub", "usdt"):
        amount_str = f"{get_final_price(svc, currency)} {labels[currency]}"
    else:
        amount_str = labels.get(currency, currency)

    order_id = await create_order(
        user.id, username, user.first_name,
        int(service_id_str), svc["name"] if svc else "?",
        currency.upper(), amount_str
    )

    await callback.message.edit_text(
        f"📩 <b>Заявка #{order_id} принята!</b>\n\n"
        f"Услуга: <b>{svc['name'] if svc else '?'}</b>\n"
        f"Оплата: <b>{amount_str}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"✅ Проверю оплату и свяжусь с тобой~ 💕\n"
        f"Нет ответа 30 минут — напомни мне в ЛС!\n"
        f"👉 {ADMIN_USERNAME}",
        parse_mode="HTML"
    )
    await _notify_admin(bot, user, username, svc, amount_str, order_id)
    await callback.answer("✅ Заявка отправлена!")


async def _notify_admin(bot: Bot, user, username: str, svc, amount_str: str, order_id: int):
    text = (
        f"🛒 <b>Новый заказ #{order_id}</b>\n\n"
        f"👤 {username}\n"
        f"📛 {user.first_name}\n"
        f"🆔 <code>{user.id}</code>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🛍 <b>{svc['name'] if svc else '?'}</b>\n"
        f"💰 {amount_str}"
    )
    for chat_id in {ADMIN_ID, NOTIFY_GROUP_ID}:
        try:
            await bot.send_message(chat_id, text, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Ошибка уведомления [{chat_id}]: {e}")


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    await message.answer(
        "👑 <b>Админ-панель</b>\n\nПривет! Выбери действие:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "adm:main")
async def cb_admin_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text(
        "👑 <b>Админ-панель</b>\n\nВыбери действие:",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm:services")
async def cb_admin_services(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    lines = []
    for s in services:
        st   = "✅" if s["is_active"] else "🚫"
        disc = f" 🏷-{s['discount']}%" if s["discount"] else ""
        lines.append(f"{st} [{s['id']}] {s['name'][:35]}{disc}")
    await callback.message.edit_text(
        "📋 <b>Все услуги:</b>\n\n" + "\n".join(lines),
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm:discount_pick")
async def cb_discount_pick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text(
        "🏷 <b>Выбери услугу для скидки:</b>",
        reply_markup=admin_services_kb(services, "disc"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:disc_page:"))
async def cb_discount_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page     = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "disc", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:disc:"))
async def cb_discount_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(int(callback.data.split(":")[-1]))
    if not svc:
        await callback.answer("😔 Не найдено", show_alert=True)
        return
    await callback.message.edit_text(
        f"🏷 Услуга: <i>{svc['name']}</i>\n\n"
        f"Текущая скидка: <b>{svc['discount'] or 0}%</b>\n\nВыбери новое значение:",
        reply_markup=discount_values_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set_disc:"))
async def cb_set_discount(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts             = callback.data.split(":")
    service_id        = int(parts[2])
    discount          = int(parts[3])
    await update_service_discount(service_id, discount)
    svc  = await get_service(service_id)
    name = svc["name"] if svc else "?"
    msg  = "✅ Скидка убрана!" if discount == 0 else f"✅ Скидка <b>-{discount}%</b> установлена:\n<i>{name}</i>"
    await callback.message.edit_text(msg, reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer("✅ Сохранено!")


@router.callback_query(F.data == "adm:price_pick")
async def cb_price_pick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text(
        "💰 <b>Выбери услугу для изменения цены:</b>",
        reply_markup=admin_services_kb(services, "price"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:price_page:"))
async def cb_price_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page     = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "price", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:price:"))
async def cb_price_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(int(callback.data.split(":")[-1]))
    if not svc:
        await callback.answer("😔 Не найдено", show_alert=True)
        return
    await callback.message.edit_text(
        f"💰 <b>Изменить цену:</b>\n<i>{svc['name']}</i>\n\n"
        f"Текущие цены:\n"
        f"  ⭐ {svc['price_stars']} Stars\n"
        f"  💙 {svc['price_ton']} TON\n"
        f"  💰 {svc['price_rub']} ₽\n"
        f"  💵 {svc['price_usdt']} USDT\n\n"
        f"Выбери валюту:",
        reply_markup=price_currency_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set_price:"))
async def cb_set_price_currency(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    parts      = callback.data.split(":")
    service_id = int(parts[2])
    currency   = parts[3]
    await state.set_state(AdminStates.waiting_price)
    await state.update_data(service_id=service_id, currency=currency)
    await callback.message.edit_text(
        f"💰 Введи новую цену в <b>{CURRENCY_LABELS.get(currency, currency)}</b>:\n(Отправь число)",
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_price)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data               = await state.get_data()
    service_id, currency = data["service_id"], data["currency"]
    try:
        value = float(message.text.strip().replace(",", "."))
        if currency in ("stars", "rub"):
            value = int(value)
        await update_service_price(service_id, f"price_{currency}", value)
        svc = await get_service(service_id)
        await message.answer(
            f"✅ Цена обновлена!\n"
            f"<b>{svc['name'] if svc else '?'}</b>\n"
            f"Новая цена: <b>{value} {CURRENCY_LABELS.get(currency, currency)}</b>",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи корректное число!")


@router.callback_query(F.data == "adm:toggle_pick")
async def cb_toggle_pick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text(
        "🔀 <b>Вкл / Выкл услугу:</b>\n✅ — активна  |  🚫 — скрыта",
        reply_markup=admin_services_kb(services, "toggle"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:toggle_page:"))
async def cb_toggle_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page     = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:toggle:"))
async def cb_toggle_service(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(int(callback.data.split(":")[-1]))
    if not svc:
        await callback.answer("😔 Не найдено", show_alert=True)
        return
    new_state = 0 if svc["is_active"] else 1
    await toggle_service(svc["id"], new_state)
    status = "включена ✅" if new_state else "скрыта 🚫"
    await callback.answer(f"Услуга {status}!", show_alert=True)
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle"))


@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    total     = await get_orders_count()
    services  = await get_all_services()
    active    = sum(1 for s in services if s["is_active"])
    discounted = sum(1 for s in services if s["discount"])
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Заказов всего: <b>{total}</b>\n"
        f"🛍 Активных услуг: <b>{active}</b>\n"
        f"🏷 Со скидкой: <b>{discounted}</b>\n"
        f"━━━━━━━━━━━━━━━━━━",
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "adm:orders")
async def cb_orders(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    orders = await get_orders(10)
    if not orders:
        await callback.message.edit_text("📦 Заказов пока нет", reply_markup=back_admin_kb())
        await callback.answer()
        return
    lines = ["📦 <b>Последние 10 заказов:</b>\n"]
    for o in orders:
        lines.append(
            f"<b>#{o['id']}</b> · {o['username']} · {o['service_name'][:20]} · {o['amount']} · {o['created_at'][:16]}"
        )
    await callback.message.edit_text("\n".join(lines)[:4000], reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer()


async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("🌸 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
