import os
import json
import httpx
import pathlib
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

API_BASE = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")
FILES_BASE = os.getenv("FILES_BASE", f"{API_BASE}/files").rstrip("/")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

try:
    ALLOWED_CHATS = set(json.loads(os.getenv("ALLOWED_CHATS", "[]")))
except Exception:
    ALLOWED_CHATS = set()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# ======= КОНФІГ МЕНЮ / ЯКОРІ =======
# Назви мають збігатися з файлами у /files-list (імена PDF у /app/docs)
PROMO_DOCS = {
    # Базові/загальні
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

PROMO_ROLES = [
    ("2nd Store Manager", ["План", "Модулі", "E-learning", "Іспити"]),
    ("Section Manager", ["План", "Модулі", "E-learning", "Іспити"]),
    ("Head of Stockroom", ["План", "Модулі", "E-learning", "Іспити"]),
]

PROMO_MAP = {
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

# Якорі сторінок для конкретних документів
PAGE_ANCHORS = {
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

CHECKLISTS = {
    ("2nd Store Manager", "Модулі"): [
        "Опанувати математику магазину (LCM, Cover, Turnover)",
        "Ключові звіти RetailStore: №3, №6, №18, №19, №25, №30, №62, №130",
        "Склад: прийом/трансфери/SDUZ",
        "Каса: X/Z, повернення, невідповідність ціни",
    ],
    ("Section Manager", "Модулі"): [
        "Клієнтський сервіс: альтернативні/додаткові продажі",
        "Інформація про товар: групи, етикетки, тканини",
        "Капасіті: план магазину, LEGO, мерч-календар",
        "VM: стіни/столи/манекени, прайспоінти",
        "Каса: X/Z, повернення",
        "HR: графіки, підбір, орієнтація",
    ],
    ("Head of Stockroom", "Модулі"): [
        "Прийом вантажів: коробки/накладні/екран прийому",
        "Переміщення та трансфери: внутрішні/міжмагазинні, звіт №35",
        "Облік запасів: Sample Counting, відсутні розміри, мінусовий сток",
        "Безпека складу: аларми, пожежна безпека, CCTV",
        "Ключові звіти: №1, №22, №28, №55, №125, №133, №5003",
    ],
}

# ======= UI =======
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Файли")],
        [KeyboardButton(text="⬆️ Промоушен")],
    ],
    resize_keyboard=True,
)

async def guard(update: Update) -> bool:
    if not ALLOWED_CHATS:
        return True
    return update.effective_chat.id in ALLOWED_CHATS

# ======= HELPERS =======
async def list_files() -> list[dict]:
    async with httpx.AsyncClient(timeout=30) as c:
        r = await c.get(f"{API_BASE}/files-list")
        r.raise_for_status()
        return r.json().get("files", [])

def file_url(name: str, page: int | None = None) -> str:
    url = f"{FILES_BASE}/{name}"
    if page:
        url = f"{url}#page={int(page)}"
    return url

# ======= HANDLERS =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return await update.message.reply_text("⛔️ Доступ обмежено.")
    text = (
        "Привіт! Я бот довідник для лінійного персоналу.\n\n"
        "• **📚 Файли** — усі завантажені гайдлайни\n"
        "• **⬆️ Промоушен** — програма підвищення для 3 ролей\n\n"
        "Надішли PDF як документ — я збережу його у /files/."
    )
    await update.message.reply_text(text, reply_markup=MAIN_KB)

# --- ФАЙЛИ ---
async def files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    try:
        items = await list_files()
    except Exception as e:
        return await update.message.reply_text(f"Помилка отримання файлів: {e}")
    if not items:
        return await update.message.reply_text("Поки що немає жодного PDF у /files/. Надішли документ сюди.")
    rows = [[InlineKeyboardButton(text=it["name"], url=file_url(it["name"]))] for it in items]
    await update.message.reply_text("📚 Прямий доступ до файлів:", reply_markup=InlineKeyboardMarkup(rows), disable_web_page_preview=True)

# --- ПРОМОУШЕН ---
async def promo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    rows = [[InlineKeyboardButton(text=role, callback_data=f"promo:{role}")] for role, _ in PROMO_ROLES]
    await update.message.reply_text("⬆️ Обери напрям промоушену:", reply_markup=InlineKeyboardMarkup(rows))

async def on_promo_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    role = q.data.split(":", 1)[1]
    tabs = dict(PROMO_ROLES)[role]
    rows = [[InlineKeyboardButton(text=tab, callback_data=f"promo_nav:{role}:{tab}")] for tab in tabs]
    await q.edit_message_text(text=f"⬆️ {role}: оберіть розділ")
    await q.message.reply_text("Меню матеріалів:", reply_markup=InlineKeyboardMarkup(rows), disable_web_page_preview=True)

async def on_promo_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    q = update.callback_query
    await q.answer()
    _, role, tab = q.data.split(":", 2)
    items = PROMO_MAP.get(role, {}).get(tab, [])
    checklist = CHECKLISTS.get((role, tab))
    header = f"📂 {role} — {tab}"
    if checklist:
        bullets = "\n".join([f"• {x}" for x in checklist])
        await q.edit_message_text(text=f"{header}\n\nКороткий чек-лист:\n{bullets}")
    else:
        await q.edit_message_text(text=header)

    rows = []
    anchors = PAGE_ANCHORS.get(role, {}).get(tab, {})
    for title in items:
        rel = PROMO_DOCS.get(title)
        if not rel:
            # якщо у мапі нема — пропускаємо (не завантажений файл)
            continue
        page = anchors.get(title)
        rows.append([InlineKeyboardButton(text=title, url=file_url(rel, page))])
    if rows:
        await q.message.reply_text("Рекомендовані матеріали:", reply_markup=InlineKeyboardMarkup(rows), disable_web_page_preview=True)
    else:
        await q.message.reply_text("Для цього розділу поки що не знайдено документів у /files/.")

# --- ПРИЙОМ PDF ---
async def on_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".pdf"):
        return await update.message.reply_text("Потрібен PDF-документ (надішли як *Документ*, не як фото).")
    file = await doc.get_file()
    path = os.path.join("docs", doc.file_name)
    await file.download_to_drive(path)
    await update.message.reply_text("📄 PDF збережено. Кнопка **📚 Файли** уже покаже його.")

async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_cmd(update, context)
    if text == "⬆️ Промоушен":
        return await promo_menu(update, context)

def main():
    print("[bot] starting application...", flush=True)
    if not BOT_TOKEN:
        print("[bot] ERROR: TELEGRAM_BOT_TOKEN is empty", flush=True)
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("files", files_cmd))
    app.add_handler(CommandHandler("promo", promo_menu))

    # Кнопки та колбеки
    app.add_handler(CallbackQueryHandler(on_promo_role, pattern=r"^promo:"))
    app.add_handler(CallbackQueryHandler(on_promo_nav, pattern=r"^promo_nav:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))

    # Прийом PDF
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))

    print("[bot] polling...", flush=True)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
