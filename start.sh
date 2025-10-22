#!/usr/bin/env bash
set -e
mkdir -p /app/docs /app/store
exec supervisord -c /app/supervisord.conf
