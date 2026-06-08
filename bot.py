import asyncio
import logging
import aiosqlite
from aiogram import Router, F, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BOT_TOKEN       = "8608397551:AAE-8Kt72CfS_2zJVi3gO8mfyKw7S2OsGeQ"       # @BotFather
ADMIN_ID        = 8786590613                         # Твой Telegram ID (@userinfobot)
NOTIFY_GROUP_ID = 5213781096                         # ID группы уведомлений (или = ADMIN_ID)
TON_WALLET      = "UQC1-vfn2v8m350ax_UDKxxI5F8gAyFiGjfaERtK1QXX7qFE"       # Твой TON адрес
ADMIN_USERNAME  = "@CiteMsk"                 # Твой username для ссылки "Написать"
STARS_RECEIVER = "@citemsk"
DATABASE_PATH = "shop.db"
BOT_NAME = "🌸 Price"

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
    "real": "🔥 В реальной жизни",
    "video_call": "📹 Видеозвонки",
    "video_custom": "🎬 Видео по запросу",
    "private": "🔑 Приватный доступ",
    "roleplay": "🎭 Ролевые игры и виртуал",
    "exclusive": "💎 Эксклюзив",
}

CURRENCIES = {
    "stars": "⭐ Telegram Stars",
    "ton": "💙 TON Coins",
    "rub": "💰 Рубли",
    "usdt": "💵 USDT",
    "nft": "🖼 NFT / Буст",
    "cryptobot": "🤖 CryptoBot",
}

class ActionCB(CallbackData, prefix="act"):
    name: str

class CategoryCB(CallbackData, prefix="cat"):
    id: str
    page: int = 0

class ServiceCB(CallbackData, prefix="svc"):
    id: int

class BuyCB(CallbackData, prefix="buy"):
    id: int

class PayCB(CallbackData, prefix="pay"):
    id: int
    curr: str

class ConfirmCB(CallbackData, prefix="conf"):
    id: int
    curr: str

class AdminCB(CallbackData, prefix="adm"):
    action: str
    id: int = 0
    page: int = 0
    val: str = ""

class AdminStates(StatesGroup):
    waiting_price = State()

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
        ("real", "🚶 Встретиться (погулять/сходить куда-то)", "Встречаемся, гуляем, проводим время вместе 💕", 1000, 11.0, 900, 10.0, 1),
        ("real", "💋 Минет", "Время обсудим~ ⏰", 2500, 30.0, 2200, 25.0, 2),
        ("real", "🔥 Потрахаемся", "Дорого т.к. я девственница. Как лишусь — сделаю дешевле 💎", 20000, 270.0, 18000, 200.0, 3),
        ("video_call", "🍑 Встать раком", "3 минуты 🔥", 500, 6.6, 450, 5.0, 1),
        ("video_call", "💃 Тверк", "3 минуты 🍑", 150, 1.9, 135, 1.5, 2),
        ("video_call", "📞 Индивидуальный звонок", "Общаться / играть вместе — 45 минут 💕", 500, 6.6, 450, 5.0, 3),
        ("video_custom", "😈 Глубокий минет (резиновый хуй)", "1 минута. Больше время — больше оплата 🔥", 300, 3.9, 270, 3.0, 1),
        ("video_custom", "💦 Сквирт в кружок", "Спецэффект для тебя 😏", 750, 9.9, 675, 8.0, 2),
        ("video_custom", "📸 Сесть на камеру (крупным планом)", "То что ты хочешь увидеть 👀", 350, 4.6, 315, 3.5, 3),
        ("private", "🔑 Приватный доступ — 1 неделя", "Доступ к приватному контенту на 7 дней", 300, 3.3, 270, 3.0, 1),
        ("private", "🔑 Приватный доступ — 2 недели", "Доступ к приватному контенту на 14 дней", 500, 5.3, 450, 5.0, 2),
        ("private", "🔑 Приватный доступ — 1 месяц", "Доступ к приватному контенту на 30 дней", 700, 9.2, 630, 7.0, 3),
        ("private", "♾️ Приватный доступ — навсегда", "Вечный доступ к приватному контенту 💎", 3000, 39.8, 2700, 30.0, 4),
        ("roleplay", "💬 Виртуал (1 час)", "Ролевая игра по переписке 🔥", 1000, 6.6, 900, 10.0, 1),
        ("roleplay", "👑 В роли Госпожи (45 минут)", "Я командую, ты подчиняешься 😈", 1000, 6.6, 900, 10.0, 2),
        ("roleplay", "🐾 В роли Рабыни (45 минут)", "Полное подчинение 🔥", 1000, 6.6, 900, 10.0, 3),
        ("exclusive", "💍 Твоя личная девушка (навсегда)", "Я твоя и только твоя 💕 Полный эксклюзив", 4000, 39.8, 3600, 40.0, 1),
    ]
    await db.executemany(
        "INSERT INTO services (category,name,description,price_stars,price_ton,price_rub,price_usdt,sort_order) VALUES (?,?,?,?,?,?,?,?)",
        services
    )
    await db.commit()

async def get_services_by_category(category: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM services WHERE category=? AND is_active=1 ORDER BY sort_order", (category,))
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

async def update_service_price(service_id: int, value: int):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("UPDATE services SET price_stars=? WHERE id=?", (value, service_id))
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
    base_stars = svc["price_stars"]
    final_stars = max(1, int(base_stars * mult))
    final_rub = max(1, int(base_stars * 2.5 * mult))
    final_ton = round(final_rub / 600.0, 2)
    final_usdt = round(final_rub / 90.0, 2)
    if currency == "stars":
        return f"⭐ {final_stars} Stars" + (f" (~{base_stars} без скидки)" if discount else "")
    elif currency == "rub":
        return f"💰 {final_rub} ₽" + (f" (~{int(base_stars * 2.5)} без скидки)" if discount else "")
    elif currency == "ton":
        return f"💙 {final_ton} TON" + (f" (~{round(base_stars * 2.5 / 600.0, 2)} без скидки)" if discount else "")
    elif currency == "usdt":
        return f"💵 {final_usdt} USDT" + (f" (~{round(base_stars * 2.5 / 90.0, 2)} без скидки)" if discount else "")
    return ""

def get_final_price(svc, currency: str):
    discount = svc["discount"] or 0
    mult = 1 - discount / 100
    base_stars = svc["price_stars"]
    if currency == "stars":
        return max(1, int(base_stars * mult))
    elif currency == "rub":
        return max(1, int(base_stars * 2.5 * mult))
    elif currency == "ton":
        return round(max(1, int(base_stars * 2.5 * mult)) / 600.0, 2)
    elif currency == "usdt":
        return round(max(1, int(base_stars * 2.5 * mult)) / 90.0, 2)
    return 0

def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг", callback_data=ActionCB(name="catalog"))
    kb.button(text="💳 Способы оплаты", callback_data=ActionCB(name="payment_info"))
    kb.button(text="📞 Написать мне", url=f"https://t.me/{ADMIN_USERNAME.lstrip('@')}")
    kb.button(text="📋 Правила", callback_data=ActionCB(name="rules"))
    kb.adjust(1)
    return kb.as_markup()

def categories_kb():
    kb = InlineKeyboardBuilder()
    for key, name in CATEGORIES.items():
        kb.button(text=name, callback_data=CategoryCB(id=key))
    kb.button(text="🏠 Главное меню", callback_data=ActionCB(name="main_menu"))
    kb.adjust(1)
    return kb.as_markup()

def services_kb(services: list, category: str, page: int = 0, per_page: int = 5):
    kb = InlineKeyboardBuilder()
    total = len(services)
    start = page * per_page
    end = min(start + per_page, total)
    for svc in services[start:end]:
        disc = f" 🏷-{svc['discount']}%" if svc["discount"] else ""
        kb.button(text=f"{svc['name']}{disc}", callback_data=ServiceCB(id=svc["id"]))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️ Назад", callback_data=CategoryCB(id=category, page=page-1).pack()))
    if end < total:
        nav.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=CategoryCB(id=category, page=page+1).pack()))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="↩️ К категориям", callback_data=ActionCB(name="catalog").pack()))
    kb.adjust(1)
    return kb.as_markup()

def service_detail_kb(service_id: int, category: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="💳 Купить (выбрать валюту)", callback_data=BuyCB(id=service_id))
    kb.button(text="↩️ Назад к списку", callback_data=CategoryCB(id=category))
    kb.adjust(1)
    return kb.as_markup()

def currency_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for key, name in CURRENCIES.items():
        kb.button(text=name, callback_data=PayCB(id=service_id, curr=key))
    kb.button(text="↩️ Отмена", callback_data=ServiceCB(id=service_id))
    kb.adjust(2)
    return kb.as_markup()

def confirm_payment_kb(service_id: int, currency: str):
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Я оплатил(а)", callback_data=ConfirmCB(id=service_id, curr=currency))
    kb.button(text="↩️ Назад", callback_data=BuyCB(id=service_id))
    kb.adjust(1)
    return kb.as_markup()

def back_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="↩️ В админ-панель", callback_data=AdminCB(action="main"))
    return kb.as_markup()

def admin_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 Все услуги", callback_data=AdminCB(action="services"))
    kb.button(text="🏷 Установить скидку", callback_data=AdminCB(action="discount_pick"))
    kb.button(text="💰 Изменить цену", callback_data=AdminCB(action="price_pick"))
    kb.button(text="🔀 Вкл/Выкл услугу", callback_data=AdminCB(action="toggle_pick"))
    kb.button(text="📊 Статистика", callback_data=AdminCB(action="stats"))
    kb.button(text="📦 Последние заказы", callback_data=AdminCB(action="orders"))
    kb.adjust(2)
    return kb.as_markup()

def admin_services_kb(services: list, action: str, page: int = 0, per_page: int = 8):
    kb = InlineKeyboardBuilder()
    total = len(services)
    start = page * per_page
    end = min(start + per_page, total)
    for svc in services[start:end]:
        status = "" if svc["is_active"] else "🚫 "
        disc = f" [{svc['discount']}%]" if svc["discount"] else ""
        kb.button(text=f"{status}{svc['name'][:32]}{disc}", callback_data=AdminCB(action=action, id=svc["id"], page=page))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=AdminCB(action=f"{action}_page", page=page-1).pack()))
    if end < total:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=AdminCB(action=f"{action}_page", page=page+1).pack()))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="↩️ Назад", callback_data=AdminCB(action="main").pack()))
    kb.adjust(1)
    return kb.as_markup()

def discount_values_kb(service_id: int):
    kb = InlineKeyboardBuilder()
    for val in [0, 5, 10, 15, 20, 25, 30, 40, 50]:
        label = "❌ Убрать скидку" if val == 0 else f"-{val}%"
        kb.button(text=label, callback_data=AdminCB(action="set_disc", id=service_id, val=str(val)))
    kb.button(text="↩️ Назад", callback_data=AdminCB(action="discount_pick"))
    kb.adjust(3)
    return kb.as_markup()

router = Router()

def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(f"<b>{BOT_NAME}</b>\n\n{WELCOME_TEXT}", reply_markup=main_menu_kb(), parse_mode="HTML")

@router.callback_query(ActionCB.filter(F.name == "main_menu"))
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(f"<b>{BOT_NAME}</b>\n\n{WELCOME_TEXT}", reply_markup=main_menu_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(ActionCB.filter(F.name == "rules"))
async def cb_rules(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главное меню", callback_data=ActionCB(name="main_menu"))
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

@router.callback_query(ActionCB.filter(F.name == "payment_info"))
async def cb_payment_info(callback: CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="🛍 Каталог услуг", callback_data=ActionCB(name="catalog"))
    kb.button(text="🏠 Главное меню", callback_data=ActionCB(name="main_menu"))
    kb.adjust(1)
    await callback.message.edit_text(
        "💳 <b>Способы оплаты</b>\n\n"
        "⭐ <b>Telegram Stars</b> — перевод пользователю\n"
        "💙 <b>TON Coins</b> — перевод на кошелёк\n"
        "💰 <b>Рубли</b> — через @CryptoBot\n"
        "💵 <b>USDT</b> — через @CryptoBot\n"
        "🖼 <b>NFT / Буст</b> — пиши в ЛС\n\n"
        "📌 Работаю только по <b>предоплате</b>!",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(ActionCB.filter(F.name == "catalog"))
async def cb_catalog(callback: CallbackQuery):
    await callback.message.edit_text("🛍 <b>Каталог услуг</b>\n\nВыбери категорию~ 💕", reply_markup=categories_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(CategoryCB.filter())
async def cb_category(callback: CallbackQuery, callback_data: CategoryCB):
    services = await get_services_by_category(callback_data.id)
    cat_name = CATEGORIES.get(callback_data.id, callback_data.id)
    if not services:
        await callback.answer("😔 Услуги временно недоступны", show_alert=True)
        return
    await callback.message.edit_text(f"{cat_name}\n\n💕 Выбери услугу:", reply_markup=services_kb(services, callback_data.id, callback_data.page), parse_mode="HTML")
    await callback.answer()

@router.callback_query(ServiceCB.filter())
async def cb_service_detail(callback: CallbackQuery, callback_data: ServiceCB):
    svc = await get_service(callback_data.id)
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

@router.callback_query(BuyCB.filter())
async def cb_buy(callback: CallbackQuery, callback_data: BuyCB):
    svc = await get_service(callback_data.id)
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

@router.callback_query(PayCB.filter())
async def cb_pay(callback: CallbackQuery, callback_data: PayCB):
    svc = await get_service(callback_data.id)
    if not svc:
        await callback.answer("Услуга не найдена", show_alert=True)
        return
    amount = get_final_price(svc, callback_data.curr)
    if callback_data.curr == "stars":
        await callback.message.edit_text(
            f"⭐ <b>Оплата через Telegram Stars</b>\n\n"
            f"Услуга: <b>{svc['name']}</b>\n"
            f"Сумма: <b>{amount} Stars</b>\n\n"
            f"📤 Переведи <code>{amount}</code> Stars пользователю <b>{STARS_RECEIVER}</b>.\n\n"
            f"После оплаты нажми кнопку ниже 👇",
            reply_markup=confirm_payment_kb(svc["id"], "stars"),
            parse_mode="HTML"
        )
    elif callback_data.curr == "ton":
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
    elif callback_data.curr == "rub":
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
    elif callback_data.curr == "usdt":
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
    elif callback_data.curr in ("nft", "cryptobot"):
        labels = {"nft": "🖼 NFT / Буст", "cryptobot": "🤖 CryptoBot"}
        await callback.message.edit_text(
            f"<b>Оплата через {labels[callback_data.curr]}</b>\n\n"
            f"Услуга: <b>{svc['name']}</b>\n\n"
            f"Напиши мне в ЛС — обсудим детали 💕\n"
            f"👉 {ADMIN_USERNAME}\n\n"
            f"После отправки нажми кнопку ниже 👇",
            reply_markup=confirm_payment_kb(svc["id"], callback_data.curr),
            parse_mode="HTML"
        )
    await callback.answer()

@router.callback_query(ConfirmCB.filter())
async def cb_confirm_payment(callback: CallbackQuery, callback_data: ConfirmCB, bot: Bot):
    svc = await get_service(callback_data.id)
    user = callback.from_user
    username = f"@{user.username}" if user.username else f"id{user.id}"
    labels = {"stars": "Stars", "ton": "TON", "rub": "₽", "usdt": "USDT", "nft": "NFT/Буст", "cryptobot": "CryptoBot"}
    if svc and callback_data.curr in ("stars", "ton", "rub", "usdt"):
        amount_str = f"{get_final_price(svc, callback_data.curr)} {labels[callback_data.curr]}"
    else:
        amount_str = labels.get(callback_data.curr, callback_data.curr)
    order_id = await create_order(
        user.id, username, user.first_name,
        callback_data.id, svc["name"] if svc else "?",
        callback_data.curr.upper(), amount_str
    )
    await callback.message.edit_text(
        f"📩 <b>Заявка #{order_id} принята!</b>\n\n"
        f"Услуга: <b>{svc['name'] if svc else '?'}</b>\n"
        f"Способ: <b>{amount_str}</b>\n\n"
        f"✅ Я проверю оплату и свяжусь с тобой~ 💕\n"
        f"Если нет ответа 30 мин — напомни мне в ЛС!",
        parse_mode="HTML"
    )
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
        logger.error(f"Error admin notify: {e}")
    try:
        if NOTIFY_GROUP_ID != ADMIN_ID:
            await bot.send_message(NOTIFY_GROUP_ID, text, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Error group notify: {e}")
    await callback.answer("✅ Заявка отправлена!")

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Нет доступа")
        return
    await message.answer("👑 <b>Админ-панель</b>\n\nПривет! Выбери действие:", reply_markup=admin_main_kb(), parse_mode="HTML")

@router.callback_query(AdminCB.filter(F.action == "main"))
async def cb_admin_main(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("👑 <b>Админ-панель</b>\n\nВыбери действие:", reply_markup=admin_main_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "services"))
async def cb_admin_services(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    lines = []
    for s in services:
        st = "✅" if s["is_active"] else "🚫"
        disc = f" 🏷-{s['discount']}%" if s["discount"] else ""
        lines.append(f"{st} [{s['id']}] {s['name'][:35]}{disc}")
    await callback.message.edit_text("📋 <b>Все услуги:</b>\n\n" + "\n".join(lines), reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "discount_pick"))
async def cb_discount_pick(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text("🏷 <b>Выбери услугу для скидки:</b>", reply_markup=admin_services_kb(services, "disc_select", callback_data.page), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "disc_select_page"))
async def cb_discount_page(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "disc_select", callback_data.page))
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "disc_select"))
async def cb_discount_select(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(callback_data.id)
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

@router.callback_query(AdminCB.filter(F.action == "set_disc"))
async def cb_set_discount(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    discount = int(callback_data.val)
    await update_service_discount(callback_data.id, discount)
    svc = await get_service(callback_data.id)
    msg = "✅ Скидка убрана!" if discount == 0 else f"✅ Скидка <b>-{discount}%</b> на:\n<i>{svc['name'] if svc else '?'}</i>"
    await callback.message.edit_text(msg, reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer("✅ Сохранено!")

@router.callback_query(AdminCB.filter(F.action == "price_pick"))
async def cb_price_pick(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text("💰 <b>Выбери услугу для изменения цены:</b>", reply_markup=admin_services_kb(services, "price_select", callback_data.page), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "price_select_page"))
async def cb_price_page(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "price_select", callback_data.page))
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "price_select"))
async def cb_price_select(callback: CallbackQuery, callback_data: AdminCB, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(callback_data.id)
    if not svc:
        await callback.answer("Не найдено", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_price
    await state.update_data(service_id=svc["id"])
    await callback.message.edit_text(
        f"💰 <b>Изменить базовую цену:</b>\n<i>{svc['name']}</i>\n\n"
        f"Введи новое количество базовых Stars (остальные валюты пересчитаются автоматически):",
        reply_markup=back_admin_kb(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.message(AdminStates.waiting_price)
async def process_new_price(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    service_id = data["service_id"]
    try:
        value = int(message.text.strip())
        await update_service_price(service_id, value)
        svc = await get_service(service_id)
        await message.answer(f"✅ Базовая цена обновлена!\n<b>{svc['name'] if svc else '?'}</b>\nНовая базовая стоимость: <b>{value} Stars</b>", reply_markup=admin_main_kb(), parse_mode="HTML")
        await state.clear()
    except ValueError:
        await message.answer("❌ Введи корректное целое число!")

@router.callback_query(AdminCB.filter(F.action == "toggle_pick"))
async def cb_toggle_pick(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_text("🔀 <b>Вкл/Выкл услугу:</b>\n✅ — активна | 🚫 — скрыта", reply_markup=admin_services_kb(services, "toggle_select", callback_data.page), parse_mode="HTML")
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "toggle_select_page"))
async def cb_toggle_page(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle_select", callback_data.page))
    await callback.answer()

@router.callback_query(AdminCB.filter(F.action == "toggle_select"))
async def cb_toggle_service(callback: CallbackQuery, callback_data: AdminCB):
    if not is_admin(callback.from_user.id):
        return
    svc = await get_service(callback_data.id)
    if not svc:
        await callback.answer("Не найдено", show_alert=True)
        return
    new_state = 0 if svc["is_active"] else 1
    await toggle_service(svc["id"], new_state)
    status = "включена ✅" if new_state else "скрыта 🚫"
    await callback.answer(f"Услуга {status}!", show_alert=True)
    services = await get_all_services()
    await callback.message.edit_reply_markup(reply_markup=admin_services_kb(services, "toggle_select", callback_data.page))

@router.callback_query(AdminCB.filter(F.action == "stats"))
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

@router.callback_query(AdminCB.filter(F.action == "orders"))
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
        lines.append(f"#{o['id']} | {o['username']} | {o['service_name'][:20]} | {o['amount']} | {o['created_at'][:16]}")
    await callback.message.edit_text("\n".join(lines)[:4000], reply_markup=back_admin_kb(), parse_mode="HTML")
    await callback.answer()

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
