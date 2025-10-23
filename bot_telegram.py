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
    InputMediaPhoto,
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

# === Основні константи ===
LOGO_URL = "https://upload.wikimedia.org/wikipedia/commons/4/4f/LC_Waikiki_logo.svg"

MAIN_KB = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📚 Файли")],
        [KeyboardButton(text="⬆️ Промоушен")],
    ],
    resize_keyboard=True,
)

# ======= Дозвіл на використання =======
async def guard(update: Update) -> bool:
    if not ALLOWED_CHATS:
        return True
    return update.effective_chat.id in ALLOWED_CHATS

# ======= Допоміжні функції =======
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

# ======= Вітальний екран =======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update):
        return await update.message.reply_text("⛔️ Доступ обмежено.")
    text = (
        "👋 Вітаємо у *LC Waikiki Guide Bot*!\n\n"
        "Цей бот створений для лінійного персоналу магазинів LC Waikiki.\n\n"
        "📚 *Файли* — усі гайдлайни, інструкції та мануали\n"
        "⬆️ *Промоушен* — матеріали програми підвищення для 3 позицій\n\n"
        "_Надішліть PDF як документ — і я додам його до бібліотеки._"
    )
    await update.message.reply_photo(
        photo=LOGO_URL,
        caption=text,
        parse_mode="Markdown",
        reply_markup=MAIN_KB,
    )

# ======= Файли =======
async def files_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    try:
        items = await list_files()
    except Exception as e:
        return await update.message.reply_text(f"Помилка отримання файлів: {e}")
    if not items:
        return await update.message.reply_text("Поки що немає жодного PDF у /files/. Надішліть документ сюди.")
    rows = [[InlineKeyboardButton(text=it["name"], url=file_url(it["name"]))] for it in items]
    await update.message.reply_text(
        "📚 *Файлова бібліотека:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
        disable_web_page_preview=True,
    )

# ======= Промоушен =======
async def promo_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    rows = [
        [InlineKeyboardButton(text="👔 2nd Store Manager", callback_data="promo:2nd Store Manager")],
        [InlineKeyboardButton(text="🧥 Section Manager", callback_data="promo:Section Manager")],
        [InlineKeyboardButton(text="📦 Head of Stockroom", callback_data="promo:Head of Stockroom")],
    ]
    await update.message.reply_text(
        "⬆️ Оберіть напрям *Promotion Program*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(rows),
    )

# --- TODO: промо-навігація (залишається як у попередній версії) ---
# Можеш скопіювати свій блок із попереднього `bot_telegram.py`,
# бо там уже готова логіка для ролей та файлів.

# ======= Прийом PDF =======
async def on_doc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await guard(update): return
    doc = update.message.document
    if not doc or not doc.file_name.lower().endswith(".pdf"):
        return await update.message.reply_text("Потрібен PDF-документ (надішліть як *Документ*, не як фото).")
    file = await doc.get_file()
    path = os.path.join("docs", doc.file_name)
    await file.download_to_drive(path)
    await update.message.reply_text("✅ PDF збережено. Перевірте у меню 📚 Файли.")

# ======= Меню кнопок =======
async def on_text_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text == "📚 Файли":
        return await files_cmd(update, context)
    if text == "⬆️ Промоушен":
        return await promo_menu(update, context)

# ======= Запуск =======
def main():
    print("[bot] starting application...", flush=True)
    if not BOT_TOKEN:
        print("[bot] ERROR: TELEGRAM_BOT_TOKEN is empty", flush=True)
        raise SystemExit(1)

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("files", files_cmd))
    app.add_handler(CommandHandler("promo", promo_menu))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text_buttons))
    app.add_handler(MessageHandler(filters.Document.PDF, on_doc))

    print("[bot] polling...", flush=True)
    app.run_polling(drop_pending_updates=True, close_loop=False)

if __name__ == "__main__":
    main()
