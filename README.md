# 🧠 LC Waikiki PromoBot

Telegram-бот + FastAPI для пошуку по PDF-документах (RAG) і швидкого доступу до матеріалів промоушенів.

## 🚀 Деплой на Render (Blueprint)
1) Створи приватний репозиторій на GitHub, завантаж усі файли **без PDF**.  
2) На render.com: **New → Blueprint** → вибери репозиторій (Render прочитає `render.yaml`).  
3) Додай Environment Variables:
```
TELEGRAM_BOT_TOKEN=токен_від_BotFather
LLM_PROVIDER=openai
LLM_API_KEY=твій_API_ключ (можна залишити порожнім — тоді /chat відповість спрощено)
FILES_BASE=https://<name>.onrender.com/files
API_BASE=https://<name>.onrender.com
ADMIN_CHAT_ID=0
ALLOWED_CHATS=[]
```
4) Після деплою відкрий `https://<name>.onrender.com/health` — має бути `{"status":"ok"}`.
5) Завантаж PDF у чат боту (він покладе їх у `/app/docs` і виконає індексацію) або виконай у Shell: `python ingest.py`.

## 🧪 Тести
- `/ask Як працює SDUZ і який звіт дивитись?`
- Кнопка **⬆️ Промоушен** → вибери роль → **План / Модулі / E-learning / Іспити**.

## 📦 Структура
- `server.py` — FastAPI (`/health`, `/search`, `/chat`, статика `/files`)
- `ingest.py` — парсинг PDF, ембеддинги, індекс FAISS
- `retriever.py` — BM25 + векторний пошук (hybrid)
- `llm.py` — тонкий інтерфейс до LLM (OpenAI). Без ключа повертає просту відповідь із контексту
- `bot_telegram.py` — Telegram-бот з меню файлів і промо-напрямами

PDF тримай на Render-диску (`/app/docs`), індекси — у `/app/store`.
