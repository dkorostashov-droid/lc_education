import os
import json
import pathlib
import asyncio
import logging
import traceback
import httpx

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --------- ЛОГІНГ ---------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("promodocs-bot")

# --------- ENV ---------
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

# --------- UI ---------
MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🧠 /ask"), KeyboardButton(text="🔎 /search")],
        [KeyboardButton(text="📚 Файли")],
    ],
    resize_keyboard=True,
)

# --------- HELPERS ---------
async def guard(update: Update) -> bool:
    """Дозволяємо всім, якщо ALLOWED_CHATS порожній, інакше — лише whitelisted."""
    if not ALLOWED_CHATS:
        return True
    chat_id = update.effective_chat.id if update.effective_chat else None
    return chat_id in ALLOWED_CHATS

async def typing(chat):
    try:
        await chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

# --------- HANDLERS ---------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return await update.message.reply_text("⛔️ Доступ обмежено.")
    text = (
        "Привіт! Я *легкий* бот для промо-доків.\n"
        "/ask <питання> — відповіді з PDF (без LLM)\n"
        "/search <запит> — пошук фрагментів\n"
        "/files — список PDF\n"
        "/reindex — перебудувати індекс (адмін)\n"
        "Надішли PDF як документ — я збережу його у /files/."
    )
    await update.message.reply_text(text, reply_markup=MAIN_KB)

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    question = " ".join(context.args).strip()
    if not question:
        return await update.message.reply_text("Приклад: /ask як готувати промо-пакет")
    await typing(update.effective_chat)

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{API_BASE}/chat", json={"question": question, "top_k": 5})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        err = f"Помилка API (/chat): {e}"
        log.error(err)
        log.debug("TRACEBACK:\n%s", traceback.format_exc())
        return await update.message.reply_text(err)

    ans = (data.get("answer") or "").strip() or "Нічого не знайдено у документах."
    sources = data.get("sources", [])
    buttons = []
    for s in sources[:3]:
        fname = pathlib.Path(s.get("source_path", "")).name
        page = int(s.get("page", 1))
        if fname:
            url = f"{FILES_BASE}/{fname}#page={page}"
            buttons.append([InlineKeyboardButton(text=f"{s.get('doc_id')} p.{page}", url=url)])
    reply_markup = InlineKeyboardMarkup(buttons) if buttons else None
    await update.message.reply_text(ans, reply_markup=reply_markup, disable_web_page_preview=True)

async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    query = " ".join(context.args).strip()
    if not query:
        return await update.message.reply_text("Приклад: /search інвентаризація")
    await typing(update.effective_chat)

    try:
        async with httpx.AsyncClient(timeout=120) as c:
            r = await c.post(f"{API_BASE}/search", json={"question": query, "top_k": 6})
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        err = f"Помилка API (/search): {e}"
        log.error(err)
        log.debug("TRACEBACK:\n%s", traceback.format_exc())
        return await update.message.reply_text(err)

    res = data.get("results", [])
    if not res:
        return await update.message.reply_text("Нічого не знайдено. Спробуй /reindex, а потім повтори пошук.")

    lines = []
    for i, it in enumerate(res, 1):
        page = int(it.get("page", 1))
        snippet = (it.get("text") or "").replace("\n", " ")
        if len(snippet) > 160:
            snippet = snippet[:160] + "…"
        lines.append(f"{i}. {it.get('doc_id')} p.{page}: {snippet}")
    await update.message.reply_text("\n".join(lines))

async def files_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    await typing(update.effective_chat)
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{API_BASE}/files-list")
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        err = f"Помилка API (/files-list): {e}"
        log.error(err)
        return await update.message.reply_text(err)

    items = data.get("files", [])
    if not items:
        return await update.message.reply_text("Поки що немає жодного PDF у /files/. Надішли документ сюди.")

    rows = [[InlineKeyboardButton(text=it["name"], url=f"{FILES_BASE}/{it['name']}")] for it in items]
    await update.message.reply_text(
        "📚 Прямий доступ до файлів:",
        reply_markup=InlineKeyboardMarkup(rows),
        disable_web_page_preview=True,
    )

async def reindex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    if ADMIN_CHAT_ID and update.effective_chat.id != ADMIN_CHAT_ID:
        return await update.message.reply_text("Команда лише для адміна.")
    await update.message.reply_text("🔄 Перебудовую індекс…")
    try:
        async with httpx.AsyncClient(timeout=None) as c:
            r = await c.post(f"{API_BASE}/reindex")
            r.raise_for_status()
            data = r.json()
        chunks = data.get("chunks")
        if chunks is not None:
            return await update.message.reply_text(f"✅ Індекс оновлено. Чанків: {chunks}")
        return await update.message.reply_text("✅ Індекс оновлено")
    except Exception as e:
        err = f"Помилка API (/reindex): {e}"
        log.error(err)
        return await update.message.reply_text(err)

async def on_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".pdf"):
        return await update.message.reply_text("Потрібен PDF-документ (надішли як *Документ*, не як фото).")
    file = await doc.get_file()
    path = os.path.join("docs", doc.file_name)
    await file.download_to_drive(path)
    await update.message.reply_text("📄 PDF збережено у /files/. Для пошуку виконай /reindex")

async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_menu(update, context)

# --------- BOOT ---------
def main():
    print("[bot] starting application...", flush=True)
    if not BOT_TOKEN:
        print("[bot] ERROR: TELEGRAM_BOT_TOKEN is empty", flush=True)
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команди
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ask", ask))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("files", files_menu))
    app.add_handler(CommandHandler("reindex", reindex))

    # Текстові кнопки і PDF
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))

    print("[bot] polling...", flush=True)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
