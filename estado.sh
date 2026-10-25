#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "============================================="
echo "   Estado del Microservicio DIRPOLES-IA      "
echo "============================================="

RUNNING=false
PID=""

if [ -f "logs/uvicorn.pid" ]; then
    PID=$(cat logs/uvicorn.pid)
    if kill -0 "$PID" 2>/dev/null; then
        RUNNING=true
    fi
fi

if [ "$RUNNING" = true ]; then
    echo "🟢 Proceso: ACTIVO en segundo plano (PID: $PID)"
else
    PIDS=$(pgrep -f "uvicorn app.main:app" || true)
    if [ -n "$PIDS" ]; then
        echo "🟢 Proceso: ACTIVO (PIDs detectados: $PIDS)"
        RUNNING=true
    else
        echo "🔴 Proceso: APAGADO / INACTIVO"
    fi
fi

echo ""
echo "🩺 Endpoint de salud (http://127.0.0.1:8000/api/v1/salud):"
SALUD=$(curl -s -m 3 http://127.0.0.1:8000/api/v1/salud 2>/dev/null || echo "")

if [ -n "$SALUD" ]; then
    echo "   $SALUD"
else
    echo "   ⚠️  Sin respuesta o conexión rechazada."
fi
echo "============================================="
