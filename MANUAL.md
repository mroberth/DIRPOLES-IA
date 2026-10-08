# Manual de Arranque — DIRPOLES-IA (uso local)

Guía paso a paso para encender, verificar y apagar el microservicio en esta máquina.

---

## 1. ¿Cómo funciona? (léelo primero)

* El sistema es un servidor **Uvicorn/FastAPI** que corre como un **proceso normal**, no como un servicio del sistema operativo.
* **Mientras esté encendido, se mantiene encendido** aunque cierres la terminal (se lanza con `nohup` y guarda su PID en `logs/uvicorn.pid`).
* **NO arranca solo** al prender la computadora ni tras un reinicio: después de cada reinicio hay que encenderlo con el paso 2.
* Requisitos que deben estar activos en paralelo:
  1. **MySQL/MariaDB** (esquemas `dirpoles_business` y `dirpoles_security`).
  2. El archivo **`.env`** con las credenciales (ya configurado).

### Estado actual

| Componente | Estado |
| :--- | :--- |
| Servidor DIRPOLES-IA | Encendido en `http://127.0.0.1:8000` (PID en `logs/uvicorn.pid`) |
| MySQL/MariaDB | Activo |
| Modo de IA | `gemini` (Google AI Studio con `gemini-3.5-flash`) |

---

## 2. Encender el sistema

Abre una terminal y ejecuta estos 3 comandos:

```bash
cd /home/roberth/Proyectos/DIRPOLES-IA
source .venv/bin/activate
mkdir -p logs
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > logs/uvicorn.log 2>&1 &
echo $! > logs/uvicorn.pid
```

Espera ~4 segundos y verifica (paso 3).

> **Nota sobre el host:** `--host 127.0.0.1` solo acepta conexiones de esta misma máquina
> (ideal si el monolito PHP corre aquí). Si otro equipo de la red necesita conectarse,
> usa `--host 0.0.0.0` en lugar de `127.0.0.1`.

---

## 3. Verificar que encendió

**Opción A — terminal:**

```bash
curl http://127.0.0.1:8000/api/v1/salud
```

Debe responder:

```json
{"estado":"ok","servicio":"DIRPOLES-IA","base_datos":"ok","modo_llm":"gemini"}
```

Si `base_datos` dice `"error"`, MySQL está apagado (ver paso 6).

**Opción B — navegador:** abre <http://localhost:8000/docs> — ahí tienes la interfaz
interactiva de la API para probar los endpoints a mano.

---

## 4. Apagar el sistema

```bash
cd /home/roberth/Proyectos/DIRPOLES-IA
kill "$(cat logs/uvicorn.pid)"
```

Comprueba que se apagó:

```bash
cat logs/uvicorn.pid   # debe dar "process not found" al matarlo
curl http://127.0.0.1:8000/api/v1/salud   # debe fallar/conexión rechazada
```

---

## 5. Ver los logs en vivo

```bash
cd /home/roberth/Proyectos/DIRPOLES-IA
tail -f logs/uvicorn.log
```

Ahí ves cada petición recibida (método, ruta, código HTTP). `Ctrl+C` sale del `tail`
**sin apagar el servidor**.

---

## 6. Problemas comunes

| Síntoma | Causa | Solución |
| :--- | :--- | :--- |
| `curl: (7) Failed to connect` | El servidor no está encendido | Repite el paso 2 |
| `Address already use` / puerto ocupado | Ya hay una instancia corriendo | Apágala (paso 4) o usa otro `--port` |
| `base_datos: "error"` en `/salud` | MySQL apagado | `sudo systemctl start mysql` (o `mariadb`) |
| `/generar` responde `503` | Caido MySQL o error de consulta | Revisa MySQL y `logs/uvicorn.log` |
| `/generar` responde `401` | Falta o falla la cabecera `X-API-Key` | Envía la clave de `.env` (`DIRPOLES_IA_API_KEY`) |
| Informe sale en `modo_informe: "simulado"` | API key de Gemini vacía/inválida o `MOCK_LLM=True` | Revisa `GEMINI_API_KEY` en `.env` y reinicia |
| Tras reiniciar la PC no responde | El sistema no autoarranca | Vuelve a ejecutar el paso 2 (o monta el servicio del paso 7) |

---

## 7. (Opcional) Autoarranque con systemd — que encienda solo

Si quieres que el sistema arranque automáticamente al iniciar sesión (y se reinicie si cae):

```bash
mkdir -p ~/.config/systemd/user
```

Crea el archivo `~/.config/systemd/user/dirpoles-ia.service` con este contenido:

```ini
[Unit]
Description=DIRPOLES-IA (FastAPI)
After=network.target mysql.service

[Service]
WorkingDirectory=/home/roberth/Proyectos/DIRPOLES-IA
ExecStart=/home/roberth/Proyectos/DIRPOLES-IA/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
```

Actívalo:

```bash
systemctl --user daemon-reload
systemctl --user enable --now dirpoles-ia
loginctl enable-linger roberth    # permite que siga vivo tras cerrar sesión
```

Comandos útiles:

```bash
systemctl --user status dirpoles-ia    # ver estado
systemctl --user restart dirpoles-ia   # reiniciar
systemctl --user stop dirpoles-ia      # apagar
journalctl --user -u dirpoles-ia -f    # ver logs
```

> Si tu MySQL se llama `mariadb.service`, ajusta `After=` en el archivo.

---

## Resumen rápido (chuleta)

```bash
# ENCENDER
cd /home/roberth/Proyectos/DIRPOLES-IA && source .venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > logs/uvicorn.log 2>&1 &
echo $! > logs/uvicorn.pid

# VERIFICAR
curl http://127.0.0.1:8000/api/v1/salud

# VER LOGS
tail -f logs/uvicorn.log

# APAGAR
kill "$(cat logs/uvicorn.pid)"
```
