#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -f "logs/uvicorn.log" ]; then
    mkdir -p logs
    touch logs/uvicorn.log
fi

echo "📋 Mostrando logs en vivo (Presiona Ctrl+C para salir sin apagar el servidor)..."
echo "-------------------------------------------------------------------------------"
tail -n 50 -f logs/uvicorn.log
