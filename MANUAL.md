# Manual de Operación y Despliegue — DIRPOLES-IA

Guía completa y práctica para poner en marcha, verificar, monitorear y mantener encendido en segundo plano el microservicio analítico de **DIRPOLES-4** en entornos Linux (**Fedora 44 / KDE Plasma** o distribuciones similares).

---

## 📌 1. ¿Cómo funciona el microservicio?

* **Tecnología:** Servidor ASGI **FastAPI** ejecutado sobre **Uvicorn** con pipeline analítico en **Pandas** y conexión a **Google Gemini API** (con modo simulado automático si no hay internet o clave).
* **Seguridad B2B:** Todas las peticiones del monolito PHP requieren la cabecera `X-API-Key` definida en `.env`.
* **Base de Datos:** Se conecta en modo **Solo Lectura (`READ-ONLY`)** a MySQL / MariaDB (`dirpoles_business` y `dirpoles_security`).
* **Puertos por defecto:** `http://127.0.0.1:8000` (o `0.0.0.0:8000` para red local).

---

## ⚠️ 2. Paso Previo Fundamental en Fedora 44: Preparar el Entorno Virtual

> [!IMPORTANT]
> Si clonaste o moviste este repositorio desde otra máquina o usuario (por ejemplo, con rutas antiguas como `/home/roberth/...` o empaquetado para Python 3.12), las librerías binarias compiladas y los scripts de `.venv` fallarán con el error:  
> `intérprete erróneo: No existe el fichero o el directorio` o errores al importar `pydantic_core`.

En Fedora 44 (donde el sistema cuenta con Python 3.14+ y tu usuario es `$USER`), genera un entorno virtual limpio ejecutando:

```bash
# 1. Posicionarse en la raíz del proyecto
cd ~/Proyectos/DIRPOLES-IA

# 2. Eliminar el entorno anterior si venía de otra instalación
rm -rf .venv

# 3. Crear el nuevo entorno virtual nativo
python3 -m venv .venv

# 4. Activar e instalar dependencias
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

> [!TIP]
> Si deseas ejecutar la suite completa de pruebas unitarias y linters, instala también:
> ```bash
> pip install -r requirements-dev.txt
> pytest
> ```

---

## 🚀 3. Formas de Encender el Microservicio

Elige el método que mejor se adapte a tu necesidad:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FORMAS DE EJECUCIÓN                             │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Scripts Rápidos  → Ideal para el uso diario (segundo plano fácil).  │
│ 2. Modo Desarrollo  → Para ver logs en vivo y recarga automática.      │
│ 3. Servicio Systemd → Para dejarlo SIEMPRE ENCENDIDO (autoarranque).   │
└────────────────────────────────────────────────────────────────────────┘
```

---

### Opción A: Mediante Scripts de Control Rápido (Recomendado para uso diario)

El proyecto incluye scripts en la raíz para gestionar el proceso en segundo plano fácilmente:

#### 1. Encender en segundo plano:
```bash
./iniciar.sh
```
*Inicia Uvicorn desacoplado de la terminal, guarda el identificador en `logs/uvicorn.pid` y redirige la salida a `logs/uvicorn.log`.*

#### 2. Consultar el estado del servicio:
```bash
./estado.sh
```
*Indica si el proceso está activo y hace una petición de diagnóstico a `/api/v1/salud`.*

#### 3. Ver los logs en vivo:
```bash
./logs.sh
```
*Muestra las peticiones HTTP en tiempo real. Presiona `Ctrl + C` para salir del visor **sin apagar el servidor**.*

#### 4. Apagar el servicio:
```bash
./detener.sh
```
*Detiene el proceso de forma limpia y elimina el archivo de PID.*

---

### Opción B: Modo Interactivo / Desarrollo (Ver logs en pantalla)

Úsalo cuando estés programando, haciendo pruebas o buscando errores:

```bash
cd ~/Proyectos/DIRPOLES-IA
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

* **`--reload`**: Reinicia el servidor automáticamente cada vez que guardas cambios en el código Python.
* Para detenerlo, simplemente presiona `Ctrl + C` en la terminal.

---

### Opción C: Dejarlo SIEMPRE ENCENDIDO con Systemd (Nivel Servicio / Autoarranque)

Si quieres que DIRPOLES-IA:
1. Encienda automáticamente al arrancar la computadora (sin necesidad de abrir la terminal).
2. Se reinicie solo si ocurre algún error imprevisto.
3. Se ejecute como servicio de usuario de Linux sin pedir contraseña de `root`.

Sigue estos 3 pasos:

#### Paso C.1: Crear la unidad de servicio systemd
Crea la carpeta de configuración y el archivo de servicio:

```bash
mkdir -p ~/.config/systemd/user
```

Crea el archivo `~/.config/systemd/user/dirpoles-ia.service` con tu editor (o usa el siguiente comando):

```bash
cat << 'EOF' > ~/.config/systemd/user/dirpoles-ia.service
[Unit]
Description=Microservicio DIRPOLES-IA (FastAPI + Gemini)
After=network.target mariadb.service mysql.service

[Service]
Type=simple
WorkingDirectory=%h/Proyectos/DIRPOLES-IA
ExecStart=%h/Proyectos/DIRPOLES-IA/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=default.target
EOF
```

> [!NOTE]
> `%h` es un comodín nativo de systemd que apunta automáticamente a tu carpeta personal (`/home/mroberth`), por lo que no requiere rutas fijas.

#### Paso C.2: Habilitar y arrancar el servicio
Ejecuta:

```bash
systemctl --user daemon-reload
systemctl --user enable --now dirpoles-ia
```

#### Paso C.3: Permitir que siga corriendo sin login gráfico activo (Linger)
Para que el servicio inicie junto con el sistema y permanezca encendido aunque cierres sesión:

```bash
loginctl enable-linger $USER
```

#### Comandos útiles para gestionar el servicio Systemd:
| Acción | Comando |
| :--- | :--- |
| **Ver estado y si está activo** | `systemctl --user status dirpoles-ia` |
| **Reiniciar el microservicio** | `systemctl --user restart dirpoles-ia` |
| **Apagar el microservicio** | `systemctl --user stop dirpoles-ia` |
| **Desactivar el autoarranque** | `systemctl --user disable dirpoles-ia` |
| **Ver logs del sistema en vivo** | `journalctl --user -u dirpoles-ia -f` |

---

## 🔍 4. Verificación del Funcionamiento

Una vez encendido el microservicio (por cualquiera de los métodos), realiza las siguientes comprobaciones:

### 1. Comprobación de Salud (Healthcheck)
Ejecuta en una terminal:

```bash
curl -s http://127.0.0.1:8000/api/v1/salud
```

**Respuesta esperada:**
```json
{
  "estado": "ok",
  "servicio": "DIRPOLES-IA",
  "base_datos": "ok",
  "modo_llm": "gemini"
}
```

* Si `"base_datos": "no_disponible"`: Revisa que MariaDB esté encendido (`sudo systemctl status mariadb`).
* Si `"modo_llm": "simulado"`: Funciona sin problemas con el motor analítico local (ocurre si `GEMINI_API_KEY` está vacía o `MOCK_LLM=True`).

### 2. Documentación Interactiva Swagger
Abre tu navegador web en:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

Desde allí puedes probar todos los endpoints (`/api/v1/reportes/generar`, `/api/v1/reportes/catalogos`, etc.) ingresando la `X-API-Key` en el botón superior **Authorize**.

### 3. Prueba de Generación de Reporte por Terminal
Puedes lanzar una petición de prueba simulada para el módulo de medicina:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/reportes/generar \
  -H "Content-Type: application/json" \
  -H "X-API-Key: 7ddfa2b3de679f470ac9a193aa3405d2" \
  -d '{
    "modulo": "medicina",
    "intencion": "alertas_y_anomalias",
    "filtros": {
      "fecha_inicio": "2026-01-01",
      "fecha_fin": "2026-12-31"
    }
  }'
```

---

## 🛠️ 5. Solución de Problemas Frecuentes en Fedora 44

| Síntoma | Causa Probable | Solución |
| :--- | :--- | :--- |
| **`intérprete erróneo: No existe el fichero o el directorio`** | El entorno virtual `.venv` tiene rutas duras de otro usuario/distro. | Recrea el entorno virtual siguiendo la **Sección 2**. |
| **`curl: (7) Failed to connect to 127.0.0.1 port 8000`** | El servidor no está encendido. | Ejecuta `./iniciar.sh` o revisa con `./estado.sh`. |
| **`base_datos: "no_disponible"`** | El servicio MariaDB / MySQL está apagado. | En Fedora ejecuta: `sudo systemctl start mariadb`. |
| **`[Errno 98] Address already in use`** | El puerto 8000 ya está ocupado por otra instancia. | Ejecuta `./detener.sh` o busca el proceso con `fuser -k 8000/tcp`. |
| **`401 Unauthorized`** | Cabecera `X-API-Key` faltante o no coincide. | Revisa el valor de `DIRPOLES_IA_API_KEY` en tu archivo `.env`. |
| **Conexión rechazada desde otra PC de la red** | Uvicorn escucha solo en `127.0.0.1` o el firewall bloquea. | 1. Cambia en `.env` o en el comando `HOST=0.0.0.0`.<br>2. Abre el puerto en el firewall de Fedora:<br>`sudo firewall-cmd --add-port=8000/tcp --permanent`<br>`sudo firewall-cmd --reload` |

---

## 📋 Chuleta Rápida (Cheatsheet)

```bash
# Encender en 2do plano
./iniciar.sh

# Ver si está encendido y su salud
./estado.sh

# Ver logs en vivo
./logs.sh

# Apagar
./detener.sh

# Encender como servicio fijo en Fedora (systemd)
systemctl --user start dirpoles-ia
systemctl --user status dirpoles-ia
```
