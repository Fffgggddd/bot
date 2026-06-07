import asyncio
import logging
import aiosqlite
from aiogram import Router, F, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice,
    PreCheckoutQuery, SuccessfulPayment,
    InlineKeyboardButton
)
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ============================================================
#  ⚙️  НАСТРОЙКИ — МЕНЯЙ ЗДЕСЬ
# ============================================================

BOT_TOKEN       = "8608397551:AAE-8Kt72CfS_2zJVi3gO8mfyKw7S2OsGeQ"       # @BotFather
ADMIN_ID        = 8786590613                         # Твой Telegram ID (@userinfobot)
NOTIFY_GROUP_ID = 5213781096                         # ID группы уведомлений (или = ADMIN_ID)
TON_WALLET      = "UQC1-vfn2v8m350ax_UDKxxI5F8gAyFiGjfaERtK1QXX7qFE"       # Твой TON адрес
ADMIN_USERNAME  = "@CiteMsk"                 # Твой username для ссылки "Написать"

DATABASE_PATH   = "shop.db"
BOT_NAME        = "🌸 Price"

# ============================================================

WELCOME_TEXT = (
    "💕 Привет, милый!\n\n"
    "Я рада что ты здесь 🥰\n"
    "Выбери что тебя интересует и я всё устрою~ ✨\n\n"
    "💎 <b>Оплата принимается:</b>\n"
    "⭐ Telegram Stars\n"
    "💙 TON Coins\n"
    "💰 Рубли (CryptoBot)\n"
    "💵 USDT (CryptoBot)\n"
    "🖼 NFT / Буст\n\n"
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
    "stars":     "⭐ Telegram Stars",
    "ton":       "💙 TON Coins",
    "rub":       "💰 Рубли",
    "usdt":      "💵 USDT",
    "nft":       "🖼 NFT / Буст",
    "cryptobot": "🤖 CryptoBot",
}

# ============================================================
#  🗄  БАЗА ДАННЫХ
# ============================================================

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                price_stars INTEGER NOT NULL,
                price_ton REAL NOT NULL,
                price_rub INTEGER NOT NULL,
                price_usdt REAL NOT NULL,
                discount INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                service_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                amount TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()
        await _seed_services(db)


async def _seed_services(db):
    cur = await db.execute("SELECT COUNT(*) FROM services")
    row = await cur.fetchone()
    if row[0] > 0:
        return

    services = [
        # (category, name, description, stars, ton, rub, usdt, sort)
        ("real",         "🚶 Встретиться (погулять/сходить куда-то)", "Встречаемся, гуляем, проводим время вместе 💕", 1000, 11.0, 900, 10.0, 1),
        ("real",         "💋 Минет",                                   "Время обсудим~ ⏰",                              2500, 30.0, 2200, 25.0, 2),
        ("real",         "🔥 Потрахаемся",                             "Дорого т.к. я девственница. Как лишусь — сделаю дешевле 💎", 20000, 270.0, 18000, 200.0, 3),
        ("video_call",   "🍑 Встать раком",                            "3 минуты 🔥",                                   500,  6.6,  450,  5.0,  1),
        ("video_call",   "💃 Тверк",                                   "3 минуты 🍑",                                   150,  1.9,  135,  1.5,  2),
        ("video_call",   "📞 Индивидуальный звонок",                   "Общаться / играть вместе — 45 минут 💕",        500,  6.6,  450,  5.0,  3),
        ("video_custom", "😈 Глубокий минет (резиновый хуй)",         "1 минута. Больше время — больше оплата 🔥",     300,  3.9,  270,  3.0,  1),
        ("video_custom", "💦 Сквирт в кружок",                        "Спецэффект для тебя 😏",                        750,  9.9,  675,  8.0,  2),
        ("video_custom", "📸 Сесть на камеру (крупным планом)",       "То что ты хочешь увидеть 👀",                   350,  4.6,  315,  3.5,  3),
        ("private",      "🔑 Приватный доступ — 1 неделя",            "Доступ к приватному контенту на 7 дней",        300,  3.3,  270,  3.0,  1),
        ("private",      "🔑 Приватный доступ — 2 недели",            "Доступ к приватному контенту на 14 дней",       500,  5.3,  450,  5.0,  2),
        ("private",      "🔑 Приватный доступ — 1 месяц",             "Доступ к приватному контенту на 30 дней",       700,  9.2,  630,  7.0,  3),
        ("private",      "♾️ Приватный доступ — навсегда",            "Вечный доступ к приватному контенту 💎",       3000, 39.8, 2700, 30.0, 4),
        ("roleplay",     "💬 Виртуал (1 час)",                        "Ролевая игра по переписке 🔥",                  1000,  6.6,  900, 10.0,  1),
        ("roleplay",     "👑 В роли Госпожи (45 минут)",              "Я командую, ты подчиняешься 😈",                1000,  6.6,  900, 10.0,  2),
        ("roleplay",     "🐾 В роли Рабыни (45 минут)",               "Полное подчинение 🔥",                          1000,  6.6,  900, 10.0,  3),
        ("exclusive",    "💍 Твоя личная девушка (навсегда)",         "Я твоя и только твоя 💕 Полный эксклюзив",     4000, 39.8, 3600, 40.0,  1),
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
    allowed = {"price_stars", "price_ton", "price_rub", "price_usdt"}
    if field not in allowed:
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


async def get_orders(limit=10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT ?", (limit,))
        return await cur.fetchall()


async def get_orders_count():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT COUNT(*) FROM orders")
        row = await cur.fetchone()
        return row[0]


def calc_price(svc, currency: str) -> str:
    discount = svc["discount"] or 0
    mult = 1 - discount / 100
    if currency == "stars":
        base = svc["price_stars"]
        final = max(1, int(base * mult))
        return f"⭐ {final} Stars" + (f" (~{base} без скидки)" if discount else "")
    elif currency == "ton":
        base = svc["price_ton"]
        final = round(base * mult, 2)
        return f"💙 {final} TON" + (f" (~{base} без скидки)" if discount else "")
    elif currency == "rub":
        base = svc["price_rub"]
        final = max(1, int(base * mult))
        return f"💰 {final} ₽" + (f" (~{base} без скидки)" if discount else "")
    elif currency == "usdt":
        base = svc["price_usdt"]
        final = round(base * mult, 2)
        return f"💵 {final} USDT" + (f" (~{base} без скидки)" if discount else "")
    return ""


def get_final_price(svc, currency: str):
    discount = svc["discount"] or 0
    mult = 1 - discount / 100
    if currency == "stars":
        return max(1, int(svc["price_stars"] * mult))
    elif currency == "ton":
        return round(svc["price_ton"] * mult, 2)
    elif currency == "rub":
        return max(1, int(svc["price_rub"] * mult))
    elif currency == "usdt":
        return round(svc["price_usdt"] * mult, 2)
    return 0

# ============================================================
#  ⌨️  КЛАВИАТУРЫ
# ============================================================

def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг",   callback_data="catalog")
    kb.button(text="💳 Способы оплаты",  callback_data="payment_info")
    kb.button(text="📞 Написать мне",    url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    kb.button(text="📋 Правила",         callback_data="rules")
    kb.adjust(1)
    return kb.as_markup()


def categories_kb():
    kb = InlineKeyboardBuilder()
    for key, name in CATEGORIES.items():
        kb.button(text=name, callback_data=f"cat:{key}")
    kb.button(text="🏠 Главное меню", callback_data="main_menu")
    kb.adjust(1)
    return kb.as_markup()


def services_kb(services: list, category: str, page: int = 0, per_page: int = 5):
    kb = InlineKeyboardBuilder()
    total = len(services)
    start = page * per_page
    end = min(start + per_page, total)

    for svc in services[start:end]:
        disc = f" 🏷-{svc['discount']}%" if svc["discount"] else ""
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
    kb.button(text="💳 Купить (выбрать валюту)", callback_data=f"buy:{service_id}")
    kb.button(text="↩️ Назад к списку",          callback_data=f"cat:{category}")
    kb.adjust(1)
    return kb.as_markup()


def currency_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for key, name in CURRENCIES.items():
        kb.button(text=name, callback_data=f"pay:{service_id}:{key}")
    kb.button(text="↩️ Отмена", callback_data=f"svc:{service_id}")
    kb.adjust(2)
    return kb.as_markup()


def confirm_payment_kb(service_id: int, currency: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил(а)", callback_data=f"confirm:{service_id}:{currency}")
    kb.button(text="↩️ Назад",        callback_data=f"buy:{service_id}")
    kb.adjust(1)
    return kb.as_markup()


def stars_payment_kb(service_id: int, stars_amount: int):
    kb = InlineKeyboardBuilder()
    kb.button(text=f"⭐ Оплатить {stars_amount} Stars", pay=True)
    kb.button(text="❌ Отмена", callback_data=f"svc:{service_id}")
    kb.adjust(1)
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
    kb.button(text="🔀 Вкл/Выкл услугу",  callback_data="adm:toggle_pick")
    kb.button(text="📊 Статистика",        callback_data="adm:stats")
    kb.button(text="📦 Последние заказы",  callback_data="adm:orders")
    kb.adjust(2)
    return kb.as_markup()


def admin_services_kb(services: list, action: str, page: int = 0, per_page: int = 8):
    kb = InlineKeyboardBuilder()
    total = len(services)
    start = page * per_page
    end = min(start + per_page, total)

    for svc in services[start:end]:
        status = "" if svc["is_active"] else "🚫 "
        disc   = f" [{svc['discount']}%]" if svc["discount"] else ""
        kb.button(
            text=f"{status}{svc['name'][:32]}{disc}",
            callback_data=f"adm:{action}:{svc['id']}:{page}"  # Передаем страницу, чтобы не сбрасывать меню
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
    for label, cur in [("⭐ Stars","stars"),("💙 TON","ton"),("💰 Рубли","rub"),("💵 USDT","usdt")]:
        kb.button(text=label, callback_data=f"adm:set_price:{service_id}:{cur}")
    kb.button(text="↩️ Назад", callback_data="adm:price_pick")
    kb.adjust(2)
    return kb.as_markup()

# ============================================================
#  🤖  ХЭНДЛЕРЫ
# ============================================================

router = Router()


class AdminStates(StatesGroup):
    waiting_price = State()


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


# ---------- СТАРТ / МЕНЮ ----------

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
    kb.button(text="🏠 Главное меню", callback_data="main_menu")
    await callback.message.edit_text(
        "📌 <b>Правила работы</b>\n\n"
        "1️⃣ Работаю <b>только по предоплате</b>\n"
        "2️⃣ После оплаты пиши мне в личку — договоримся о деталях\n"
        "3️⃣ Фоточки <b>не продаю</b> 🚫\n"
        "4️⃣ За фейков не ручаюсь\n"
        "5️⃣ Все вопросы — <b>только в ЛС</b>\n\n"
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
        "⭐ <b>Telegram Stars</b> — прямо в боте\n"
        "💙 <b>TON Coins</b> — перевод на кошелёк\n"
        "💰 <b>Рубли</b> — через @CryptoBot\n"
        "💵 <b>USDT</b> — через @CryptoBot\n"
        "🖼 <b>NFT / Буст</b> — пиши в ЛС\n\n"
        "📌 Работаю только по <b>предоплате</b>!",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()


# ---------- КАТАЛОГ ----------

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
        f"{cat_name}\n\n💕 Выбери услугу:",
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
        f"{cat_name}\n\n💕 Выбери услугу:",
        reply_markup=services_kb(services, category, int(page_str)),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("svc:"))
async def cb_service_detail(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена 😔", show_alert=True)
        return

    discount = svc["discount"] or 0
    disc_text = f"\n🏷 <b>Скидка: -{discount}%</b>" if discount else ""

    await callback.message.edit_text(
        f"<b>{svc['name']}</b>{disc_text}\n\n"
        f"📝 {svc['description']}\n\n"
        f"💰 <b>Цены:</b>\n"
        f"  {calc_price(svc, 'stars')}\n"
        f"  {calc_price(svc, 'ton')}\n"
        f"  {calc_price(svc, 'rub')}\n"
        f"  {calc_price(svc, 'usdt')}\n\n"
        f"📌 Работаю по предоплате!",
        reply_markup=service_detail_kb(svc["id"], svc["category"]),
        parse_mode="HTML"
    )
    await callback.answer()


# ---------- ОПЛАТА ----------

@router.callback_query(F.data.startswith("buy:"))
async def cb_buy(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    disc = svc["discount"] or 0
    disc_text = f"\n🏷 Скидка: <b>-{disc}%</b>" if disc else ""
    await callback.message.edit_text(
        f"💳 <b>Оплата</b>\n\nУслуга: <b>{svc['name']}</b>{disc_text}\n\nВыбери способ оплаты:",
        reply_markup=currency_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


# ⭐ Stars
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":stars"))
async def cb_pay_stars(callback: CallbackQuery, bot: Bot):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    stars = get_final_price(svc, "stars")
    await callback.message.delete()
    await bot.send_invoice(
        chat_id=callback.from_user.id,
        title=svc["name"][:32],
        description=(svc["description"] or "Услуга")[:255],
        payload=f"svc_{svc['id']}",
        currency="XTR",
        prices=[LabeledPrice(label=svc["name"][:32], amount=stars)],
        reply_markup=stars_payment_kb(svc["id"], stars)
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message, bot: Bot):
    payment: SuccessfulPayment = message.successful_payment
    service_id = int(payment.invoice_payload.split("_")[1])
    svc = await get_service(service_id)
    user = message.from_user
    username = f"@{user.username}" if user.username else f"id{user.id}"
    order_id = await create_order(user.id, username, user.first_name, service_id,
                                  svc["name"] if svc else "?", "Stars", f"{payment.total_amount} ⭐")
    await message.answer(
        f"✅ <b>Оплата прошла!</b>\n\n"
        f"🎉 Спасибо за покупку~ 💕\n"
        f"Заказ #{order_id}: <b>{svc['name'] if svc else '?'}</b>\n\n"
        f"📩 Напиши мне в ЛС — договоримся о деталях!",
        parse_mode="HTML"
    )
    await _notify_admin(bot, user, username, svc, f"{payment.total_amount} ⭐ Stars", order_id)


# 💙 TON
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":ton"))
async def cb_pay_ton(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "ton")
    await callback.message.edit_text(
        f"💙 <b>Оплата через TON</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} TON</b>\n\n"
        f"📤 Отправь <code>{amount}</code> TON на адрес:\n"
        f"<code>{TON_WALLET}</code>\n\n"
        f"⚠️ В комментарии укажи свой username!\n\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "ton"),
        parse_mode="HTML"
    )
    await callback.answer()


# 💰 Рубли
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":rub"))
async def cb_pay_rub(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "rub")
    await callback.message.edit_text(
        f"💰 <b>Оплата в рублях</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} ₽</b>\n\n"
        f"📲 Переведи через @CryptoBot → Отправить → Рубли\n"
        f"Реквизиты уточни в ЛС~ 💕\n\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "rub"),
        parse_mode="HTML"
    )
    await callback.answer()


# 💵 USDT
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":usdt"))
async def cb_pay_usdt(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, "usdt")
    await callback.message.edit_text(
        f"💵 <b>Оплата в USDT</b>\n\n"
        f"Услуга: <b>{svc['name']}</b>\n"
        f"Сумма: <b>{amount} USDT</b>\n\n"
        f"📲 Переведи через @CryptoBot → Отправить → USDT\n"
        f"Реквизиты уточни в ЛС~ 💕\n\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"], "usdt"),
        parse_mode="HTML"
    )
    await callback.answer()


# 🖼 NFT
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":nft"))
async def cb_pay_nft(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    await callback.message.edit_text(
        f"🖼 <b>Оплата NFT / Буст</b>\n\n"
        f"Услуга: <b>{svc['name'] if svc else '?'}</b>\n\n"
        f"Напиши мне в ЛС — обсудим детали 💕\n"
        f"👉 {ADMIN_USERNAME}\n\n"
        f"После отправки нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"] if svc else 0, "nft"),
        parse_mode="HTML"
    )
    await callback.answer()


# 🤖 CryptoBot
@router.callback_query(F.data.startswith("pay:") & F.data.endswith(":cryptobot"))
async def cb_pay_cryptobot(callback: CallbackQuery):
    svc = await get_service(int(callback.data.split(":")[1]))
    await callback.message.edit_text(
        f"🤖 <b>Оплата через CryptoBot</b>\n\n"
        f"Услуга: <b>{svc['name'] if svc else '?'}</b>\n\n"
        f"Перейди в @CryptoBot и отправь оплату.\n"
        f"Подробности уточни в ЛС~ 💕\n\n"
        f"После оплаты нажми кнопку ниже 👇",
        reply_markup=confirm_payment_kb(svc["id"] if svc else 0, "cryptobot"),
        parse_mode="HTML"
    )
    await callback.answer()


# ✅ Подтверждение ручных оплат
@router.callback_query(F.data.startswith("confirm:"))
async def cb_confirm_payment(callback: CallbackQuery, bot: Bot):
    _, service_id_str, currency = callback.data.split(":")
    svc = await get_service(int(service_id_str))
    user = callback.from_user
    username = f"@{user.username}" if user.username else f"id{user.id}"

    labels = {"ton": "TON", "rub": "₽", "usdt": "USDT", "nft": "NFT/Буст", "cryptobot": "CryptoBot"}
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
        f"Способ: <b>{amount_str}</b>\n\n"
        f"✅ Я проверю оплату и свяжусь с тобой~ 💕\n"
        f"Если нет ответа 30 мин — напомни мне в ЛС!",
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
        f"🛍 <b>{svc['name'] if svc else '?'}</b>\n"
        f"💰 {amount_str}"
    )
    try:
        await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Уведомление админу: {e}")
    try:
        if NOTIFY_GROUP_ID != ADMIN_ID:
            await bot.send_message(NOTIFY_GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Уведомление в группу: {e}")


# ---------- АДМИН-ПАНЕЛЬ ----------

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
async def cb_admin_main(callback: CallbackQuery, state: FSMContext = None):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    if state:
        await state.clear()  # Сбрасываем состояние, если админ вернулся в меню во время ввода цены
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
        st = "✅" if s["is_active"] else "🚫"
        disc = f" 🏷-{s['discount']}%" if s["discount"] else ""
        lines.append(f"{st} [{s['id']}] {s['name'][:35]}{disc}")
    await callback.message.edit_text(
        "📋 <b>Все услуги:</b>\n\n" + "\n".join(lines),
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


# --- Скидки ---

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
    page = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "disc", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:disc:"))
async def cb_discount_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    svc = await get_service(int(parts[2]))
    if not svc:
        await callback.answer("Не найдено", show_alert=True)
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
    parts = callback.data.split(":")
    service_id, discount = int(parts[2]), int(parts[3])
    await update_service_discount(service_id, discount)
    svc = await get_service(service_id)
    msg = "✅ Скидка убрана!" if discount == 0 else f"✅ Скидка <b>-{discount}%</b> на:\n<i>{svc['name'] if svc else '?'}</i>"
    await callback.message.edit_text(msg, reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer("✅ Сохранено!")


# --- Цены ---

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
    page = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "price", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:price:"))
async def cb_price_select(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    svc = await get_service(int(parts[2]))
    if not svc:
        await callback.answer("Не найдено", show_alert=True)
        return
    await callback.message.edit_text(
        f"💰 <b>Изменить цену:</b>\n<i>{svc['name']}</i>\n\n"
        f"Текущие:\n"
        f"⭐ {svc['price_stars']} Stars\n"
        f"💙 {svc['price_ton']} TON\n"
        f"💰 {svc['price_rub']} ₽\n"
        f"💵 {svc['price_usdt']} USDT\n\nВыбери валюту:",
        reply_markup=price_currency_kb(svc["id"]),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:set_price:"))
async def cb_set_price_currency(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    service_id, currency = int(parts[2]), parts[3]
    labels = {"stars": "⭐ Stars", "ton": "💙 TON", "rub": "💰 Рублей", "usdt": "💵 USDT"}
    await state.set_state(AdminStates.waiting_price)
    await state.update_data(service_id=service_id, currency=currency)
    await callback.message.edit_text(
        f"💰 Введи новую цену в <b>{labels.get(currency, currency)}</b>:\n(Отправь число)",
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_price)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    service_id, currency = data["service_id"], data["currency"]
    try:
        value = float(message.text.strip().replace(",", "."))
        if currency in ("stars", "rub"):
            value = int(value)
        await update_service_price(service_id, f"price_{currency}", value)
        svc = await get_service(service_id)
        await message.answer(
            f"✅ Цена обновлена!\n<b>{svc['name'] if svc else '?'}</b>\nНовая: <b>{value}</b>",
            reply_markup=admin_main_kb(),
            parse_mode="HTML"
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи корректное число!")


# --- Вкл/Выкл ---

@router.callback_query(F.data == "adm:toggle_pick")
async def cb_toggle_pick(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text(
        "🔀 <b>Вкл/Выкл услугу:</b>\n✅ — активна | 🚫 — скрыта",
        reply_markup=admin_services_kb(services, "toggle"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("adm:toggle_page:"))
async def cb_toggle_page(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    page = int(callback.data.split(":")[-1])
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle", page))
    await callback.answer()


@router.callback_query(F.data.startswith("adm:toggle:"))
async def cb_toggle_service(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    parts = callback.data.split(":")
    service_id = int(parts[2])
    current_page = int(parts[3]) if len(parts) > 3 else 0
    
    svc = await get_service(service_id)
    if not svc:
        await callback.answer("Не найдено", show_alert=True)
        return
    new_state = 0 if svc["is_active"] else 1
    await toggle_service(svc["id"], new_state)
    status = "включена ✅" if new_state else "скрыта 🚫"
    await callback.answer(f"Услуга {status}!", show_alert=True)
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle", current_page))


# --- Статистика и заказы ---

@router.callback_query(F.data == "adm:stats")
async def cb_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    total = await get_orders_count()
    services = await get_all_services()
    active = sum(1 for s in services if s["is_active"])
    discounted = sum(1 for s in services if s["discount"])
    await callback.message.edit_text(
        f"📊 <b>Статистика</b>\n\n"
        f"📦 Заказов всего: <b>{total}</b>\n"
        f"🛍 Активных услуг: <b>{active}</b>\n"
        f"🏷 Со скидкой: <b>{discounted}</b>",
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
        # Урезаем данные строк во избежание поломки разметки HTML при превышении лимитов Telegram
        safe_username = o['username'].replace('<', '&lt;').replace('>', '&gt;') if o['username'] else "id"
        safe_service = o['service_name'][:20].replace('<', '&lt;').replace('>', '&gt;')
        lines.append(f"#{o['id']} | {safe_username} | {safe_service} | {o['amount']} | {o['created_at'][:16]}")
    await callback.message.edit_text("\n".join(lines), reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer()


# ============================================================
#  🚀  ЗАПУСК
# ============================================================

async def main():
    await init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    logger.info("🌸 Бот запущен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
