#!/usr/bin/env bash
set -e
# Створюємо каталоги (на випадок чистого диска)
mkdir -p /app/docs /app/store
# Запускаємо supervisord, який підніме і API, і бота
exec supervisord -c /app/supervisord.conf