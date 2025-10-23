import os
import json
import httpx
from typing import Dict, List, Tuple, Optional
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ---------- ENV ----------
API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
FILES_BASE = os.getenv("FILES_BASE", f"{API_BASE}/files").rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

try:
    ALLOWED_CHATS = set(json.loads(os.getenv("ALLOWED_CHATS", "[]")))
except Exception:
    ALLOWED_CHATS = set()
try:
    ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
except Exception:
    ADMIN_CHAT_ID = 0

# ---------- МАПІНГ ФАЙЛІВ (назва в меню -> фактична назва PDF) ----------
PROMO_DOCS: Dict[str, str] = {
    # Загальні
    "LC Waikiki Math (UA)": "LC Waikiki Math_Ukr.pdf",
    "Модуль 1 — Склад": "Module 1_Stockroom V2.0_UA.pdf",
    "Модуль 2 — Продажі та запаси": "Module 2_Sales & Stock Managment V2.0_UA.pdf",
    "Модуль 3 — Каса": "Module 3_Cashpoint V2.0_UA.pdf",
    "Модуль 4 — Бекофіс": "Module 4_Backoffice V2.0_UA.pdf",
    "RS Reports (звіти)": "RS Reports_UKR.pdf",
    "Stockroom Process Manual": "Stockroom Process Manual_UKR.pdf",
    "Welcome Book": "Welcome Book_2020_UA_A4-1.pdf",

    # 2nd Store Manager
    "2nd SM — Road Map": "Road Map_SM_UKR 1.pdf",
    "2nd SM — Introduction": "Promotion Training Program Introduction (for Second Store Manager candidates) UKR 1.pdf",
    "2nd SM — E-learning list": "e-learning list for Second Store Managers UKR 1.pdf",
    "2nd SM — On-the-Job Checklists": "On the Job Checklists (Second Store Manager) UKR 2.pdf",

    # Section Manager
    "Section — Road Map": "PP Road Map_Section Manager_UKR 1.pdf",
    "Section — Introduction": "Promotion Training Program Introduction (for Section Manager candidates)_UKR 1.pdf",
    "Section — E-learning list": "e-learning list for Section Managers_UKR 1.pdf",
    "Section — On-the-Job Checklists": "On the Job Checklists (Section Manager)_UKR 4.pdf",

    # Head of Stockroom
    "HOS — Road Map": "PP Road Map_Head of Stock_UKR 1.pdf",
    "HOS — Introduction": "Promotion Training Program Intorduction (for HOC & HOS candidates)_UKR 1.pdf",
    "HOS — E-learning list": "e-learning list for HOS_UKR 1.pdf",
    "HOS — On-the-Job Checklists": "On the job Checklists (Head of Stockroom)_UKR 1.pdf",
}

# ---------- СТРУКТУРА ПРОМО (ролі -> вкладки) ----------
PROMO_ROLES: List[Tuple[str, List[str]]] = [
    ("2nd Store Manager", ["План", "Модулі", "E-learning", "Іспити"]),
    ("Section Manager", ["План", "Модулі", "E-learning", "Іспити"]),
    ("Head of Stockroom", ["План", "Модулі", "E-learning", "Іспити"]),
]

PROMO_MAP: Dict[str, Dict[str, List[str]]] = {
    "2nd Store Manager": {
        "План": ["2nd SM — Road Map", "2nd SM — Introduction"],
        "Модулі": [
            "LC Waikiki Math (UA)",
            "Модуль 2 — Продажі та запаси",
            "Модуль 1 — Склад",
            "RS Reports (звіти)",
            "Модуль 3 — Каса",
            "Модуль 4 — Бекофіс",
        ],
        "E-learning": ["2nd SM — E-learning list", "2nd SM — On-the-Job Checklists"],
        "Іспити": [],
    },
    "Section Manager": {
        "План": ["Section — Road Map", "Section — Introduction"],
        "Модулі": [
            "LC Waikiki Math (UA)",
            "Модуль 2 — Продажі та запаси",
            "Модуль 1 — Склад",
            "RS Reports (звіти)",
            "Модуль 3 — Каса",
        ],
        "E-learning": ["Section — E-learning list", "Section — On-the-Job Checklists"],
        "Іспити": [],
    },
    "Head of Stockroom": {
        "План": ["HOS — Road Map", "HOS — Introduction"],
        "Модулі": [
            "Stockroom Process Manual",
            "Модуль 1 — Склад",
            "RS Reports (звіти)",
            "LC Waikiki Math (UA)",
            "Модуль 2 — Продажі та запаси",
            "Модуль 3 — Каса",
            "Модуль 4 — Бекофіс",
        ],
        "E-learning": ["HOS — E-learning list", "HOS — On-the-Job Checklists"],
        "Іспити": [],
    },
}

# ---------- ЯКОРІ СТОРІНОК (#page=) ДЛЯ ПОСИЛАНЬ ----------
PAGE_ANCHORS: Dict[str, Dict[str, Dict[str, int]]] = {
    "2nd Store Manager": {
        "План": {"2nd SM — Road Map": 1, "2nd SM — Introduction": 1},
        "Модулі": {},
        "E-learning": {},
        "Іспити": {},
    },
    "Section Manager": {
        "План": {"Section — Road Map": 1, "Section — Introduction": 1},
        "Модулі": {},
        "E-learning": {},
        "Іспити": {},
    },
    "Head of Stockroom": {
        "План": {"HOS — Road Map": 1, "HOS — Introduction": 1},
        "Модулі": {"Stockroom Process Manual": 1, "RS Reports (звіти)": 1},
        "E-learning": {},
        "Іспити": {},
    },
}

# ---------- МІНІ-ГАЙДИ (5–7 пунктів) ----------
MINI_GUIDES: Dict[Tuple[str, str], List[str]] = {
    # 2nd SM
    ("2nd Store Manager", "План"): [
        "Ознайомся з Road Map та дедлайнами етапів.",
        "Зустрінься з SM/DSM: узгодь очікування та KPI.",
        "Склади особистий план навчання (щотижневі цілі).",
        "Забронюй час для shadowing у ключових зонах магазину.",
        "Веди простий трекер прогресу (Google Sheet/нотатник).",
    ],
    ("2nd Store Manager", "Модулі"): [
        "Розумій LCM/Cover/Turnover — базова математика магазину.",
        "Ключові звіти RS: №3, 6, 18, 19, 25, 30, 62, 130 — вмій пояснити, що вони показують.",
        "Склад: прийом, трансфери, SDUZ — без помилок і в строк.",
        "Каса: X/Z, повернення, розбіжності — діємо по SOP.",
        "Backoffice: документообіг і комунікація з HQ.",
        "Щотижня — короткий самотест із модулів.",
    ],
    ("2nd Store Manager", "E-learning"): [
        "Склади графік e-learning (30–45 хв на сесію, 3–4 рази/тиждень).",
        "По кожному курсу — 3 тези, 1 застосування на зміні.",
        "Перевір себе: короткий квіз або обговорення з наставником.",
        "Заведи нотатки: скріни/приклади для команди.",
        "Закрий усі модулі до дати промо-інтерв’ю.",
    ],
    ("2nd Store Manager", "Іспити"): [
        "Повтори ключові звіти та метрики магазину.",
        "Пройди mock-інтерв’ю з SM/HR.",
        "Підготуй 2–3 приклади «було/стало» з твоєї ділянки.",
        "Зберіть фідбек від колег/наставника (1–2 цитати).",
        "Прийди з пропозиціями: 3 поліпшення на наступний місяць.",
    ],

    # Section
    ("Section Manager", "План"): [
        "Узгодь з SM цілі секції (продаж, конверсія, AT/UPT).",
        "Сплануй ротації на секції та ключові дні мерчу.",
        "Домовся про shadowing з досвідченим SM.",
        "Налаштуй чек-ін 1р/тиждень (15 хв) з SM по прогресу.",
        "Веди чек-лист компетенцій (відмічай закриті пункти).",
    ],
    ("Section Manager", "Модулі"): [
        "Customer experience: альтернативні/додаткові продажі — тренуй сценарії.",
        "Product knowledge: склади міні-каталог матеріалів/етикеток.",
        "Capacity & планограма: план секції, LEGO, календар мерчу.",
        "VM: стіни/столи/манекени, прайспоінти — щоденний контроль.",
        "Каса: X/Z та повернення у складних кейсах.",
        "HR-основи: onboarding новачка + графіки.",
    ],
    ("Section Manager", "E-learning"): [
        "Розбий навчання на короткі сесії (до 45 хв).",
        "Після кожного курсу — мікро-ролеплей з колегою.",
        "Витягуй 1 прийом, який впровадиш сьогодні на зміні.",
        "Щотижня ділиться інсайтом із командою (5 хв).",
        "Фіксуй завершені курси у трекері.",
    ],
    ("Section Manager", "Іспити"): [
        "Підготуй порівняльні фото VM «до/після».",
        "Покажи, як читати ключові звіти секції.",
        "Опиши 2 кейси роботи з запереченнями клієнтів.",
        "План на місяць: 3 дії, 3 метрики успіху.",
        "Чітко сформулюй сильні сторони й зони росту.",
    ],

    # HOS
    ("Head of Stockroom", "План"): [
        "Узгодь із SM/HOS-менеджером метрики складу (точність, швидкість, втрати).",
        "Склади календар поставок/інвентаризацій.",
        "Організуй зони: прийом, зберігання, видача, повернення.",
        "Визнач регламент денних чеків і відповідальних.",
        "Веди логи інцидентів (помилки, втрати, пошкодження).",
    ],
    ("Head of Stockroom", "Модулі"): [
        "Прийом: звірка коробок/накладних, робота з екраном прийому.",
        "Трансфери: внутрішні/міжмагазинні, контроль звіту №35.",
        "Облік: sample counting, відсутні розміри, мінусовий сток.",
        "Безпека: аларми, пожежна безпека, CCTV — щоденні перевірки.",
        "Звіти: №1, 22, 28, 55, 125, 133, 5003 — розумій і контролюй.",
        "Комунікація із залом: швидка видача запитів.",
    ],
    ("Head of Stockroom", "E-learning"): [
        "Склади план курсів під пікові дні (менше навантаження — більше навчання).",
        "Після курсу — 1 покращення процесу (запиши у чек-лист).",
        "Проведи міні-навчання для колеги (5–7 хв).",
        "Зроби самоперевірку складу з чек-листом.",
        "Закрий усі модулі до наступної великої поставки.",
    ],
    ("Head of Stockroom", "Іспити"): [
        "Презентуй схему складу та регламенти.",
        "Покажи кейс «помилка → виправлення → профілактика».",
        "Підготуй дані: швидкість прийому, точність інвентаризації.",
        "План покращень на квартал (3 дії, відповідальні, строки).",
        "Фідбек від SM/кас/секцій — 2–3 короткі відгуки.",
    ],
}

# ---------- UI ----------
PERSISTENT_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Файли")],
        [KeyboardButton(text="⬆️ Промоушен")],
    ],
    resize_keyboard=True,
)

def inline_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Файли", callback_data="nav:files"),
         InlineKeyboardButton("⬆️ Промоушен", callback_data="nav:promo")],
    ])

# ---------- HELPERS ----------
async def guard(update: Update) -> bool:
    if not ALLOWED_CHATS:
        return True
    chat_id = update.effective_chat.id if update.effective_chat else None
    return chat_id in ALLOWED_CHATS

async def list_files() -> List[Dict]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API_BASE}/files-list")
        r.raise_for_status()
        return r.json().get("files", [])

def file_url(name: str, page: Optional[int] = None) -> str:
    url = f"{FILES_BASE}/{name}"
    return f"{url}#page={int(page)}" if page else url

# ---------- HANDLERS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return await update.message.reply_text("⛔️ Доступ обмежено.")
    text = (
        "👋 Ласкаво просимо до *LC Waikiki Guide Bot*.\n\n"
        "• **Файли** — усі гайдлайни та інструкції\n"
        "• **Промоушен** — матеріали програми підвищення (3 позиції)\n\n"
        "Надішліть PDF як документ — я додам його до бібліотеки."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=inline_home_kb())

# --- Files page ---
async def files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    try:
        files = await list_files()
    except Exception as e:
        return await update.message.reply_text(f"Помилка отримання списку файлів: {e}")
    if not files:
        return await update.message.reply_text("Поки що немає жодного PDF у /files/. Надішліть документ сюди.")
    rows = [[InlineKeyboardButton(text=f["name"], url=file_url(f["name"]))] for f in files]
    await update.message.reply_text(
        "📚 *Файлова бібліотека:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
        disable_web_page_preview=True
    )

# --- Promo home ---
async def promo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit_message=False):
    if not await guard(update): return
    rows = [
        [InlineKeyboardButton("👔 2nd Store Manager", callback_data="promo:2nd Store Manager")],
        [InlineKeyboardButton("🧥 Section Manager", callback_data="promo:Section Manager")],
        [InlineKeyboardButton("📦 Head of Stockroom", callback_data="promo:Head of Stockroom")],
        [InlineKeyboardButton("🏠 На головну", callback_data="nav:home")],
    ]
    text = "⬆️ Оберіть напрям *Promotion Program*:"
    if edit_message and update.callback_query:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(rows))

# --- Promo role selected ---
async def on_promo_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    role = q.data.split(":", 1)[1]
    tabs = dict(PROMO_ROLES)[role]
    rows = [[InlineKeyboardButton(tab, callback_data=f"promo_nav:{role}:{tab}")] for tab in tabs]
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="nav:promo"),
                 InlineKeyboardButton("🏠 Головна", callback_data="nav:home")])
    await q.edit_message_text(text=f"⬆️ {role}: оберіть розділ", reply_markup=InlineKeyboardMarkup(rows))

# --- Promo tab selected ---
async def on_promo_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    _, role, tab = q.data.split(":", 2)

    # 1) МІНІ-ГАЙД
    guide = MINI_GUIDES.get((role, tab))
    header = f"📂 {role} — {tab}"
    if guide:
        bullets = "\n".join([f"• {x}" for x in guide])
        await q.edit_message_text(text=f"{header}\n\n{bullets}")
    else:
        await q.edit_message_text(text=header)

    # 2) КНОПКИ З ДОКУМЕНТАМИ
    items = PROMO_MAP.get(role, {}).get(tab, [])
    anchors = PAGE_ANCHORS.get(role, {}).get(tab, {})
    buttons = []
    for title in items:
        filename = PROMO_DOCS.get(title)
        if not filename:
            continue  # файл не завантажено — пропускаємо
        page = anchors.get(title)
        buttons.append([InlineKeyboardButton(title, url=file_url(filename, page))])

    if buttons:
        buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"promo:{role}"),
                        InlineKeyboardButton("🏠 Головна", callback_data="nav:home")])
        await q.message.reply_text("Рекомендовані матеріали:", reply_markup=InlineKeyboardMarkup(buttons),
                                   disable_web_page_preview=True)
    else:
        await q.message.reply_text("Для цього розділу поки що не знайдено документів у /files/.",
                                   reply_markup=InlineKeyboardMarkup([
                                       [InlineKeyboardButton("⬅️ Назад", callback_data=f"promo:{role}")],
                                       [InlineKeyboardButton("🏠 Головна", callback_data="nav:home")],
                                   ]))

# --- Upload PDF ---
async def on_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".pdf"):
        return await update.message.reply_text("Потрібен PDF-документ (надішліть як *Документ*, не як фото).")
    file = await doc.get_file()
    path = os.path.join("docs", doc.file_name)
    await file.download_to_drive(path)
    await update.message.reply_text("✅ PDF збережено. Перевірте у 📚 Файли.")

# --- Text buttons ---
async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_cmd(update, context)
    if text == "⬆️ Промоушен":
        return await promo_menu(update, context)

# --- Inline nav router ---
async def on_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    _, where = q.data.split(":", 1)
    if where == "files":
        class Dummy: pass
        dummy_update = Dummy()
        dummy_update.message = q.message
        return await files_cmd(dummy_update, context)
    if where == "promo":
        return await promo_menu(update, context, edit_message=True)
    if where == "home":
        caption = (
            "👋 Ласкаво просимо до *LC Waikiki Guide Bot*.\n\n"
            "• **Файли** — усі гайдлайни та інструкції\n"
            "• **Промоушен** — матеріали програми підвищення (3 позиції)\n\n"
            "Надішліть PDF як документ — я додам його до бібліотеки."
        )
        try:
            await q.edit_message_text(caption, parse_mode="Markdown", reply_markup=inline_home_kb())
        except Exception:
            await q.message.reply_text(caption, parse_mode="Markdown", reply_markup=inline_home_kb())

# ---------- BOOT ----------
def main():
    print("[bot] starting application...", flush=True)
    if not BOT_TOKEN:
        print("[bot] ERROR: TELEGRAM_BOT_TOKEN is empty", flush=True)
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("files", files_cmd))
    app.add_handler(CommandHandler("promo", lambda u, c: promo_menu(u, c)))

    # Колбеки (inline)
    app.add_handler(CallbackQueryHandler(on_nav, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(on_promo_role, pattern=r"^promo:"))
    app.add_handler(CallbackQueryHandler(on_promo_nav, pattern=r"^promo_nav:"))

    # Текстові кнопки + прийом PDF
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))

    print("[bot] polling...", flush=True)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
