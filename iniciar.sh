#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# 1. Verificar entorno virtual y que uvicorn sea ejecutable
if [ ! -f ".venv/bin/uvicorn" ] || ! .venv/bin/uvicorn --version >/dev/null 2>&1; then
    echo "❌ Error: El entorno virtual '.venv' no está configurado o es incompatible con este sistema."
    echo "          (Suele ocurrir si el proyecto se copió desde otra máquina o usuario anterior)."
    echo ""
    echo "💡 Solución en Fedora 44 (ejecuta esto en tu terminal):"
    echo "   cd ~/Proyectos/DIRPOLES-IA"
    echo "   rm -rf .venv"
    echo "   python3 -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install --upgrade pip"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# 2. Verificar si ya está corriendo
mkdir -p logs
if [ -f "logs/uvicorn.pid" ]; then
    PID=$(cat logs/uvicorn.pid)
    if kill -0 "$PID" 2>/dev/null; then
        echo "⚠️  DIRPOLES-IA ya está en ejecución (PID: $PID)."
        echo "   Para ver estado:  ./estado.sh"
        echo "   Para detener:     ./detener.sh"
        echo "   Para ver logs:    ./logs.sh"
        exit 0
    else
        rm -f logs/uvicorn.pid
    fi
fi

# 3. Iniciar uvicorn en segundo plano
echo "🚀 Iniciando DIRPOLES-IA en segundo plano..."
nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 > logs/uvicorn.log 2>&1 &
PID=$!
disown $PID 2>/dev/null || true
echo $PID > logs/uvicorn.pid

# 4. Esperar y comprobar
sleep 2
if kill -0 "$PID" 2>/dev/null; then
    echo "✅ DIRPOLES-IA encendido exitosamente (PID: $PID)."
    echo "   🌐 URL API:  http://127.0.0.1:8000"
    echo "   📚 Swagger:  http://127.0.0.1:8000/docs"
    echo "   📋 Logs:     ./logs.sh"
else
    echo "❌ Error al iniciar. Revisa el log con: cat logs/uvicorn.log"
    exit 1
fi
