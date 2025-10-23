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

# ---------- КАРТИ ДОКУМЕНТІВ ----------
# 1) ПРОМО (видимі тільки в меню Промоушен, у "📚 Файли" НЕ показуємо)
PROMO_DOCS: Dict[str, str] = {
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

# 2) ФАЙЛИ (видимі у "📚 Файли")
FILES_DOCS: Dict[str, str] = {
    # Модулі (окремою категорією)
    "Module 1_Stockroom V2.0_UA": "Module 1_Stockroom V2.0_UA.pdf",
    "Module 2_Sales & Stock Managment V2.0_UA": "Module 2_Sales & Stock Managment V2.0_UA.pdf",
    "Module 3_Cashpoint V2.0_UA": "Module 3_Cashpoint V2.0_UA.pdf",
    "Module 4_Backoffice V2.0_UA": "Module 4_Backoffice V2.0_UA.pdf",

    # Довідники
    "LC Waikiki Math (UA)": "LC Waikiki Math_Ukr.pdf",
    "RS Reports (звіти)": "RS Reports_UKR.pdf",
    "Stockroom Process Manual": "Stockroom Process Manual_UKR.pdf",

    # Welcome
    "Welcome Book_2020_UA_A4-1": "Welcome Book_2020_UA_A4-1.pdf",
}

# 3) Категорії у "📚 Файли" (лише з FILES_DOCS)
FILE_CATEGORIES: Dict[str, List[str]] = {
    "Модулі": [
        "Module 1_Stockroom V2.0_UA",
        "Module 2_Sales & Stock Managment V2.0_UA",
        "Module 3_Cashpoint V2.0_UA",
        "Module 4_Backoffice V2.0_UA",
    ],
    "Довідники": [
        "LC Waikiki Math (UA)",
        "RS Reports (звіти)",
        "Stockroom Process Manual",
    ],
    "Welcome для новачків": [
        "Welcome Book_2020_UA_A4-1",
    ],
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
            "Module 2_Sales & Stock Managment V2.0_UA",
            "Module 1_Stockroom V2.0_UA",
            "RS Reports (звіти)",
            "Module 3_Cashpoint V2.0_UA",
            "Module 4_Backoffice V2.0_UA",
        ],
        "E-learning": ["2nd SM — E-learning list", "2nd SM — On-the-Job Checklists"],
        "Іспити": [],
    },
    "Section Manager": {
        "План": ["Section — Road Map", "Section — Introduction"],
        "Модулі": [
            "LC Waikiki Math (UA)",
            "Module 2_Sales & Stock Managment V2.0_UA",
            "Module 1_Stockroom V2.0_UA",
            "RS Reports (звіти)",
            "Module 3_Cashpoint V2.0_UA",
        ],
        "E-learning": ["Section — E-learning list", "Section — On-the-Job Checklists"],
        "Іспити": [],
    },
    "Head of Stockroom": {
        "План": ["HOS — Road Map", "HOS — Introduction"],
        "Модулі": [
            "Stockroom Process Manual",
            "Module 1_Stockroom V2.0_UA",
            "RS Reports (звіти)",
            "LC Waikiki Math (UA)",
            "Module 2_Sales & Stock Managment V2.0_UA",
            "Module 3_Cashpoint V2.0_UA",
            "Module 4_Backoffice V2.0_UA",
        ],
        "E-learning": ["HOS — E-learning list", "HOS — On-the-Job Checklists"],
        "Іспити": [],
    },
}

# ---------- ЯКОРІ СТОРІНОК (#page=) ----------
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
        "Забронюй shadowing у ключових зонах магазину.",
        "Веди трекер прогресу (Google Sheet/нотатник).",
    ],
    ("2nd Store Manager", "Модулі"): [
        "LCM/Cover/Turnover — базова математика магазину.",
        "Ключові звіти RS: №3, 6, 18, 19, 25, 30, 62, 130.",
        "Склад: прийом/трансфери/SDUZ — без помилок і в строк.",
        "Каса: X/Z, повернення, розбіжності — по SOP.",
        "Backoffice: документообіг і комунікація з HQ.",
    ],
    ("2nd Store Manager", "E-learning"): [
        "Графік сесій: 30–45 хв, 3–4 рази/тиждень.",
        "Після курсу — 3 тези + 1 застосування на зміні.",
        "Короткий квіз чи обговорення з наставником.",
        "Нотатки/скріни — ділись з командою.",
    ],
    ("2nd Store Manager", "Іспити"): [
        "Повтори ключові звіти та метрики магазину.",
        "Mock-інтерв’ю з SM/HR.",
        "2–3 кейси «було/стало» з твоєї ділянки.",
        "3 покращення на місяць — чіткий план.",
    ],

    # Section Manager
    ("Section Manager", "План"): [
        "Узгодь з SM цілі секції (продаж, конверсія, AT/UPT).",
        "Сплануй ротації та ключові дні мерчу.",
        "Shadowing з досвідченим SM.",
        "Щотижневий чек-ін 15 хв із SM.",
        "Веди чек-лист компетенцій.",
    ],
    ("Section Manager", "Модулі"): [
        "Customer experience: тренуй альтернативні/додаткові продажі.",
        "Product knowledge: міні-каталог матеріалів/етикеток.",
        "Capacity & планограма: план секції, LEGO, календар мерчу.",
        "VM: стіни/столи/манекени, прайспоінти — щоденний контроль.",
        "Каса: X/Z, повернення у складних кейсах.",
    ],
    ("Section Manager", "E-learning"): [
        "Сесії до 45 хв; по кожному курсу — 1 прийом у роботу.",
        "Міні-ролеплей із колегою (5 хв).",
        "Щотижня ділитись інсайтами з командою.",
        "Відзначай у трекері завершені курси.",
    ],
    ("Section Manager", "Іспити"): [
        "Фотокейси VM «до/після».",
        "Презентація читання ключових звітів секції.",
        "2 кейси роботи з запереченнями клієнтів.",
        "План на місяць: 3 дії та метрики успіху.",
    ],

    # HOS
    ("Head of Stockroom", "План"): [
        "Узгодь метрики складу: точність, швидкість, втрати.",
        "Календар поставок/інвентаризацій.",
        "Організуй зони: прийом, зберігання, видача, повернення.",
        "Щоденні чеки та відповідальні.",
        "Логи інцидентів: помилки/втрати/пошкодження.",
    ],
    ("Head of Stockroom", "Модулі"): [
        "Прийом: звірка коробок/накладних, екран прийому.",
        "Трансфери: внутрішні/міжмагазинні, контроль звіту №35.",
        "Облік: sample counting, відсутні розміри, мінусовий сток.",
        "Безпека: аларми, пожежна безпека, CCTV — щоденні перевірки.",
        "Звіти: №1, 22, 28, 55, 125, 133, 5003 — розумій і контролюй.",
    ],
    ("Head of Stockroom", "E-learning"): [
        "Плануй курси на менш завантажені дні.",
        "Після курсу — 1 покращення процесу, зафіксуй у чек-листі.",
        "Міні-навчання для колеги (5–7 хв).",
        "Самоперевірки складу за чек-листом.",
    ],
    ("Head of Stockroom", "Іспити"): [
        "Схема складу та регламенти.",
        "Кейс «помилка → виправлення → профілактика».",
        "Метрики: швидкість прийому, точність інвентаризації.",
        "План покращень на квартал (3 дії, відповідальні, строки).",
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
        "• **Файли** — категорії: *Модулі*, *Довідники*, *Welcome*\n"
        "• **Промоушен** — програма для 3 позицій (з міні-гайдами)\n\n"
        "Надішліть PDF як документ — я додам його до бібліотеки."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=inline_home_kb())

# === 📚 Файли: головне меню категорій ===
async def files_home(update: Update, context: ContextTypes.DEFAULT_TYPE, as_edit=False):
    if not await guard(update): return
    rows = [[InlineKeyboardButton(cat, callback_data=f"files_cat:{cat}")] for cat in FILE_CATEGORIES.keys()]
    rows.append([InlineKeyboardButton("🏠 На головну", callback_data="nav:home")])
    text = "📚 Оберіть категорію файлів:"
    if as_edit and update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
    else:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(rows), disable_web_page_preview=True)

# === 📚 Файли: конкретна категорія ===
async def files_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    _, cat = q.data.split(":", 1)

    # список файлів на сервері
    try:
        files = await list_files()
        available = {f["name"] for f in files}
    except Exception:
        available = set()

    titles = FILE_CATEGORIES.get(cat, [])
    buttons = []
    missing = []

    for title in titles:
        filename = FILES_DOCS.get(title)
        if not filename:
            missing.append(f"⚠️ Немає мапінгу: {title}")
            continue
        if filename in available:
            buttons.append([InlineKeyboardButton(title, url=file_url(filename))])
        else:
            missing.append(f"— {title} (файл ще не завантажено)")

    footer = ""
    if missing:
        footer = "\n\n_Примітка:_\n" + "\n".join(missing)

    rows = buttons or [[InlineKeyboardButton("Наразі файлів у цій категорії немає", callback_data="noop")]]
    rows.append([InlineKeyboardButton("⬅️ Назад", callback_data="nav:files"),
                 InlineKeyboardButton("🏠 Головна", callback_data="nav:home")])

    await q.edit_message_text(
        text=f"📂 {cat}{footer}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
        disable_web_page_preview=True
    )

# === ⬆️ Промоушен: головне меню ===
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

# --- Промо-ролі ---
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

# --- Промо-вкладки з міні-гідами та кнопками документів ---
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

    # 2) КНОПКИ З ДОКУМЕНТАМИ (лише наявні)
    try:
        files = await list_files()
        available = {f["name"] for f in files}
    except Exception:
        available = set()

    items = PROMO_MAP.get(role, {}).get(tab, [])
    anchors = PAGE_ANCHORS.get(role, {}).get(tab, {})
    buttons = []
    for title in items:
        # джерело може бути як із FILES_DOCS (модулі/довідники), так і з PROMO_DOCS (специфіка ролі)
        filename = FILES_DOCS.get(title) or PROMO_DOCS.get(title)
        if not filename or filename not in available:
            continue
        page = anchors.get(title)
        url = file_url(filename, page)
        buttons.append([InlineKeyboardButton(title, url=url)])

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
    await update.message.reply_text("✅ PDF збережено. Перевірте у 📚 Файли або в розділах Промоушен.")

# --- Text buttons ---
async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_home(update, context)
    if text == "⬆️ Промоушен":
        return await promo_menu(update, context)

# --- Inline nav router ---
async def on_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    _, where = q.data.split(":", 1)
    if where == "files":
        return await files_home(update, context, as_edit=True)
    if where == "promo":
        return await promo_menu(update, context, edit_message=True)
    if where == "home":
        caption = (
            "👋 Ласкаво просимо до *LC Waikiki Guide Bot*.\n\n"
            "• **Файли** — категорії: *Модулі*, *Довідники*, *Welcome*\n"
            "• **Промоушен** — програма для 3 позицій (з міні-гайдами)\n\n"
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
    app.add_handler(CommandHandler("files", lambda u, c: files_home(u, c)))
    app.add_handler(CommandHandler("promo", lambda u, c: promo_menu(u, c)))

    # Inline колбеки
    app.add_handler(CallbackQueryHandler(on_nav, pattern=r"^nav:"))
    app.add_handler(CallbackQueryHandler(files_category, pattern=r"^files_cat:"))
    app.add_handler(CallbackQueryHandler(on_promo_role, pattern=r"^promo:"))
    app.add_handler(CallbackQueryHandler(on_promo_nav, pattern=r"^promo_nav:"))

    # Текстові кнопки + прийом PDF
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))

    print("[bot] polling...", flush=True)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()

    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
