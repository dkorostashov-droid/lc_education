FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Базові пакунки
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl && rm -rf /var/lib/apt/lists/*

# Залежності
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 🔧 Створюємо каталоги ще на етапі білду, щоб StaticFiles точно не падав
RUN mkdir -p /app/docs /app/store

# Код
COPY . .
EXPOSE 8000

# Запускаємо API та бота одним процесом (див. run_all.py)
CMD ["python", "run_all.py"]
