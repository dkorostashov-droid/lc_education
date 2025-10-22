import os, json, pathlib, httpx, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

API_BASE = os.getenv("API_BASE", "http://localhost:8000")
FILES_BASE = os.getenv("FILES_BASE", f"{API_BASE}/files")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_CHATS = set(json.loads(os.getenv("ALLOWED_CHATS", "[]")))
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

PROMO_DOCS = {
    "LC Waikiki Math (UA)": "LC Waikiki Math_Ukr.pdf",
    "Модуль 1 — Склад": "Module 1_Stockroom V2.0_UA.pdf",
    "Модуль 2 — Продажі та запаси": "Module 2_Sales & Stock Managment V2.0_UA.pdf",
    "Модуль 3 — Каса": "Module 3_Cashpoint V2.0_UA.pdf",
    "Модуль 4 — Бекофіс": "Module 4_Backoffice V2.0_UA.pdf",
    "RS Reports (звіти)": "RS Reports_UKR.pdf",
    "Stockroom Process Manual": "Stockroom Process Manual_UKR.pdf",
    "Welcome Book": "Welcome Book_2020_UA_A4-1.pdf",

    "2nd SM — Road Map": "Road Map_SM_UKR 1.pdf",
    "2nd SM — Introduction": "Promotion Training Program Introduction (for Second Store Manager candidates) UKR 1.pdf",
    "2nd SM — E-learning list": "e-learning list for Second Store Managers UKR 1.pdf",
    "2nd SM — On-the-Job Checklists": "On the Job Checklists (Second Store Manager) UKR 2.pdf",

    "Section — Road Map": "PP Road Map_Section Manager_UKR 1.pdf",
    "Section — Introduction": "Promotion Training Program Introduction (for Section Manager candidates)_UKR 1.pdf",
    "Section — E-learning list": "e-learning list for Section Managers_UKR 1.pdf",
    "Section — On-the-Job Checklists": "On the Job Checklists (Section Manager)_UKR 4.pdf",

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
        "Модулі": {
            "Stockroom Process Manual": 1,
            "RS Reports (звіти)": 1,
        },
        "E-learning": {},
        "Іспити": {},
    },
}

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧠 /ask"), KeyboardButton(text="🔎 /search")],
        [KeyboardButton(text="📚 Файли"), KeyboardButton(text="⬆️ Промоушен")],
    ], resize_keyboard=True
)

async def guard(update: Update) -> bool:
    if not ALLOWED_CHATS:
        return True
    return update.effective_chat.id in ALLOWED_CHATS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return await update.message.reply_text("⛔️ Доступ обмежено.")
    await update.message.reply_text(
        "Привіт! Я бот для промо-доків.
"
        "/ask <питання> — Q&A по PDF
"
        "/search <запит> — пошук фрагментів
"
        "/reindex — перебудувати індекс (адмінам)",
        reply_markup=MAIN_KB
    )

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    question = " ".join(context.args).strip()
    if not question:
        return await update.message.reply_text("Приклад: /ask як підготувати промо-пакет")
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API_BASE}/chat", json={"question": question, "top_k": 6})
        r.raise_for_status()
        data = r.json()
    ans = data.get("answer","(нема відповіді)")
    sources = data.get("sources", [])
    buttons = []
    for s in sources[:3]:
        label = f"{s['doc_id']} p.{s['page']}"
        url = s.get("source_path")
        if url and not url.startswith("http"):
            fname = pathlib.Path(url).name
            url = f"{FILES_BASE}/{fname}#page={int(s['page'])}"
        if url and url.startswith("http"):
            buttons.append([InlineKeyboardButton(text=label, url=url)])
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(ans, reply_markup=reply_markup, disable_web_page_preview=True)

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text("Приклад: /search критерії оцінювання рівня L5")
    async with httpx.AsyncClient(timeout=60) as c:
        r = await c.post(f"{API_BASE}/search", json={"question": query, "top_k": 6})
        r.raise_for_status()
        res = r.json().get("results", [])
    if not res:
        return await update.message.reply_text("Нічого не знайдено")
    lines = []
    for i, it in enumerate(res, 1):
        lines.append(f"{i}. {it['doc_id']} p.{int(it['page'])}: {it['text'][:180]}…")
    await update.message.reply_text("\n".join(lines))

async def files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    rows = []
    for title, rel in PROMO_DOCS.items():
        url = f"{FILES_BASE}/{rel}"
        rows.append([InlineKeyboardButton(text=title, url=url)])
    kb = InlineKeyboardMarkup(rows)
    await update.message.reply_text("📚 Прямий доступ до файлів:", reply_markup=kb, disable_web_page_preview=True)

async def promo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    rows = [[InlineKeyboardButton(text=role, callback_data=f"promo:{role}")] for role, _ in PROMO_ROLES]
    kb = InlineKeyboardMarkup(rows)
    await update.message.reply_text("⬆️ Обери напрям промоушену:", reply_markup=kb)

async def on_promo_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    query = update.callback_query
    await query.answer()
    role = query.data.split(":",1)[1]
    rows = [[InlineKeyboardButton(text=tab, callback_data=f"promo_nav:{role}:{tab}")]
            for tab in dict(PROMO_ROLES)[role]]
    kb = InlineKeyboardMarkup(rows)
    await query.edit_message_text(text=f"⬆️ {role}: оберіть розділ")
    await query.message.reply_text("Меню матеріалів:", reply_markup=kb, disable_web_page_preview=True)

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

async def on_promo_nav(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    query = update.callback_query
    await query.answer()
    _, role, tab = query.data.split(":", 2)
    items = PROMO_MAP.get(role, {}).get(tab, [])
    checklist = CHECKLISTS.get((role, tab))
    header = f"📂 {role} — {tab}"
    if checklist:
        bullets = "\n".join([f"• {x}" for x in checklist])
        await query.edit_message_text(text=f"{header}\n\nКороткий чек‑лист:\n{bullets}")
    else:
        await query.edit_message_text(text=header)

    rows = []
    anchors = PAGE_ANCHORS.get(role, {}).get(tab, {})
    for title in items:
        rel = PROMO_DOCS.get(title)
        if not rel:
            continue
        url = f"{FILES_BASE}/{rel}"
        page = anchors.get(title)
        if page:
            url = f"{url}#page={int(page)}"
        rows.append([InlineKeyboardButton(text=title, url=url)])
    if rows:
        kb = InlineKeyboardMarkup(rows)
        await query.message.reply_text("Рекомендовані матеріали:", reply_markup=kb, disable_web_page_preview=True)

async def reindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    if ADMIN_CHAT_ID and update.effective_chat.id != ADMIN_CHAT_ID:
        return await update.message.reply_text("Команда лише для адміна.")
    os.system("python ingest.py")
    await update.message.reply_text("✅ Індекс оновлено")

async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_menu(update, context)
    if text == "⬆️ Промоушен":
        return await promo_menu(update, context)

async def on_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".pdf"):
        return await update.message.reply_text("Потрібен PDF")
    file = await doc.get_file()
    path = os.path.join("docs", doc.file_name)
    await file.download_to_drive(path)
    await update.message.reply_text("PDF збережено, індексую…")
    os.system("python ingest.py")
    await update.message.reply_text("✅ Готово")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("reindex", reindex))
    app.add_handler(CallbackQueryHandler(on_promo_role, pattern=r"^promo:"))
    app.add_handler(CallbackQueryHandler(on_promo_nav, pattern=r"^promo_nav:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))
    app.run_polling(close_loop=False)

if __name__ == "__main__":
    main()
