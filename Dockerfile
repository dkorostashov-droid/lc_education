FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
PYTHONUNBUFFERED=1


# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
build-essential curl && rm -rf /var/lib/apt/lists/*


# App deps
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
&& pip install --no-cache-dir supervisor


# App
COPY . .
RUN chmod +x start.sh


# Expose FastAPI
EXPOSE 8000


CMD ["./start.sh"]