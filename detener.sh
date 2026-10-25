#!/usr/bin/env bash
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ ! -f "logs/uvicorn.pid" ]; then
    PIDS=$(pgrep -f "uvicorn app.main:app" || true)
    if [ -n "$PIDS" ]; then
        echo "⚠️  No se encontró logs/uvicorn.pid, pero hay procesos activos: $PIDS"
        kill $PIDS
        echo "🛑 Procesos detenidos."
        exit 0
    fi
    echo "ℹ️  DIRPOLES-IA no está en ejecución."
    exit 0
fi

PID=$(cat logs/uvicorn.pid)

if kill -0 "$PID" 2>/dev/null; then
    echo "🛑 Deteniendo DIRPOLES-IA (PID: $PID)..."
    kill "$PID"
    
    for i in {1..5}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done

    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️  Forzando cierre (SIGKILL)..."
        kill -9 "$PID" 2>/dev/null || true
    fi

    rm -f logs/uvicorn.pid
    echo "✅ Servicio detenido correctamente."
else
    echo "ℹ️  El proceso $PID ya no estaba corriendo. Limpiando PID antiguo."
    rm -f logs/uvicorn.pid
fi
