#!/usr/bin/env bash
set -e
mkdir -p /app/data/docs /app/data/store
# симлінки для коду, який очікує /app/docs і /app/store
rm -rf /app/docs /app/store 2>/dev/null || true
ln -s /app/data/docs /app/docs
ln -s /app/data/store /app/store
exec supervisord -c /app/supervisord.conf
