# DIRPOLES-IA

Microservicio de **analítica de datos e inteligencia artificial** del sistema **DIRPOLES-4** (Sistema de Control e Inventario de Beneficiarios de Bienestar Estudiantil) de la Universidad Politécnica Territorial de Lara Andrés Eloy Blanco (UPTAEB) — PNF en Informática.

Se encarga de extraer datos de los 10 módulos de reportes del monolito PHP, procesarlos con **Pandas**, generar un informe narrativo en **Markdown** mediante el modelo **Gemini** de Google AI Studio y devolverlo al monolito por una API B2B protegida por `X-API-Key`.

> Especificación de arquitectura: [`context.md`](./context.md).

---

## Características

* **Lectura exclusiva (READ-ONLY):** usuario de base de datos con privilegios `SELECT` únicamente; cero riesgo de alterar la operación del monolito.
* **10 módulos de reportes:** general, medicina, psicología, orientación, trabajo social, discapacidad, referencias, jornadas, mobiliario y transporte.
* **Pipeline ETL en Pandas:** distribuciones, series mensuales, variaciones porcentuales y detección de umbrales críticos (stock, vencimientos, aforo, citas no asistidas, referencias pendientes…).
* **Prompts multidominio:** rol especializado inyectado dinámicamente según el módulo y enfoque según la intención del informe.
* **Resiliencia LLM:** si `GEMINI_API_KEY` está vacía, `MOCK_LLM=True` o el proveedor falla, se genera un informe con el cliente simulado local y se marca en `meta.modo_informe`.
* **Contratos tipados:** DTOs de entrada/salida con Pydantic y catálogos de validación idénticos a los del monolito PHP.
* **Calidad verificada:** `ruff` (lint + formato), `mypy` y `pytest` (62 pruebas, incluidas de integración contra la BD local).

---

## Requisitos

| Componente | Versión |
| :--- | :--- |
| Python | 3.12+ |
| MySQL / MariaDB | 10.x (esquemas `dirpoles_business` y `dirpoles_security`) |
| Google AI Studio | API key (opcional; si no, modo simulado) |

---

## Instalación

```bash
# 1. Entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# 2. Dependencias
pip install -r requirements.txt
pip install -r requirements-dev.txt   # solo desarrollo (pytest, ruff, mypy)

# 3. Variables de entorno
cp .env.example .env
# Edita .env con tus credenciales reales
```

### Usuario de base de datos READ-ONLY

El microservicio **no** debe usar un usuario con privilegios de escritura. Ejecuta en MySQL/MariaDB:

```sql
CREATE USER 'dirpoles_ia_reader'@'localhost' IDENTIFIED BY 'contraseña_segura_lectura';
GRANT SELECT ON dirpoles_business.* TO 'dirpoles_ia_reader'@'localhost';
GRANT SELECT ON dirpoles_security.* TO 'dirpoles_ia_reader'@'localhost';
FLUSH PRIVILEGES;
```

> El esquema `dirpoles_security` es necesario: dos consultas (citas de psicología y asignaciones de transporte) cruzan a la tabla `empleado`.

---

## Configuración (`.env`)

| Variable | Descripción |
| :--- | :--- |
| `HOST` / `PORT` | Dirección y puerto del servidor Uvicorn. |
| `DEBUG` | Modo desarrollo. |
| `DIRPOLES_IA_API_KEY` | Clave B2B compartida con el monolito PHP (cabecera `X-API-Key`). |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` | Conexión a la base de datos (usuario solo lectura). |
| `DB_NAME_BUSINESS` / `DB_NAME_SECURITY` | Nombres de los dos esquemas. |
| `GEMINI_API_KEY` | API key de Google AI Studio. Vacía ⇒ modo simulado. |
| `GEMINI_MODEL` | Modelo a usar (por defecto `gemini-3.5-flash`). |
| `MOCK_LLM` | `True` fuerza el generador simulado sin importar la key. |
| `UMBRAL_STOCK_CRITICO_INSUMOS` | Umbral de stock crítico para insumos médicos. |
| `UMBRAL_STOCK_CRITICO_REPUESTOS` | Umbral de bajo stock para repuestos vehiculares. |
| `LIMITE_REGISTROS` | Máximo de filas por colección (1–20000, por defecto 5000). |
| `ALLOWED_ORIGINS` | Orígenes CORS permitidos, separados por coma. |

---

## Ejecución

```bash
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Documentación interactiva (Swagger UI): <http://localhost:8000/docs>

Comprobación rápida:

```bash
curl http://localhost:8000/api/v1/salud
```

```json
{ "estado": "ok", "servicio": "DIRPOLES-IA", "base_datos": "ok", "modo_llm": "simulado" }
```

---

## API

### Seguridad

Toda petición a los endpoints de reportes debe incluir:

```http
X-API-Key: <DIRPOLES_IA_API_KEY>
```

Sin la cabecera o con un valor incorrecto la respuesta es `401 Unauthorized`.

### `POST /api/v1/reportes/generar`

Genera un informe narrativo en Markdown.

**Cuerpo de petición:**

```json
{
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "filtros": {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-09-30",
    "genero": "F",
    "pnf": 3,
    "estado": null,
    "limit": 5000
  },
  "observacion_usuario": "Enfocarse en insumos con bajo stock para las jornadas de octubre.",
  "id_empleado": null
}
```

| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `modulo` | enum | Uno de los 10 módulos (ver `GET /catalogos`). |
| `intencion` | enum | `resumen_ejecutivo`, `alertas_y_anomalias`, `tendencias_y_patrones`, `recomendaciones`. |
| `filtros` | objeto | Ver tabla siguiente. Todos opcionales. |
| `observacion_usuario` | string ≤ 1000 | Instrucción libre que se inyecta en el prompt. |
| `id_empleado` | entero ≥ 1 | Si se envía, restringe los registros a los registrados por ese empleado (equivale al filtro del monolito para usuarios no administradores). `null` = visibilidad total. |

**Filtros disponibles** (se aplican según el módulo; los no aplicables se ignoran):

| Filtro | Tipo | Valores |
| :--- | :--- | :--- |
| `fecha_inicio`, `fecha_fin` | fecha `YYYY-MM-DD` | Inclusivos a nivel día. `fecha_inicio ≤ fecha_fin`. |
| `genero` | enum | `M`, `F`. |
| `pnf` | entero ≥ 1 | ID del PNF. |
| `area` | enum | `Becas`, `Exoneración`, `FAMES`, `Medicina`, `Orientación`, `Discapacidad`, `Psicología`. |
| `estado` | string ≤ 60 | Validado por catálogo en psicología, referencias, jornadas y mobiliario; libre en el resto. |
| `tipo_consulta` | enum | `Diagnóstico`, `Retiro temporal`, `Cambio de carrera`. |
| `submodulo` | enum | `Becas`, `Exoneración`, `FAMES`, `Gestión Embarazo`. |
| `grado` | enum | `Leve`, `Moderado`, `Grave`. |
| `tipo_discapacidad` | enum | `Física`, `Sensorial`, `Intelectual`, `Múltiple`, `Otro`. |
| `tipo_bien` | enum | `Mobiliario`, `Equipo`. |
| `tipo_vehiculo` | enum | `Autobús`, `Camioneta`, `Automóvil`. |
| `seccion_transporte` | enum | `Vehículos`, `Rutas`, `Proveedores`, `Repuestos`, `Asignaciones`, `Mantenimientos`. |
| `servicio_destino` | entero ≥ 1 | ID del servicio de destino (referencias). |
| `limit` | entero 1–20000 | Filas máximas por colección; por defecto `LIMITE_REGISTROS`. |

**Cuerpo de respuesta (200):**

```json
{
  "exito": true,
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "informe_markdown": "### 📊 Informe de Análisis Inteligente: Módulo Medicina\n\n...",
  "meta": {
    "registros_procesados": 450,
    "tiempo_procesamiento_seg": 2.15,
    "modo_informe": "gemini"
  }
}
```

`meta.modo_informe` puede ser:

| Valor | Significado |
| :--- | :--- |
| `gemini` | Informe generado por el modelo real de Google AI Studio. |
| `simulado` | Generado por el cliente local (sin key o `MOCK_LLM=True`). |
| `simulado_fallback` | Se intentó Gemini pero falló; se usó el simulado como respaldo. |

**Errores:**

| Código | Causa |
| :--- | :--- |
| `401` | `X-API-Key` ausente o incorrecta. |
| `422` | Payload inválido (módulo/intención desconocidos, fechas invertidas, filtro fuera de catálogo…). |
| `503` | Error de conexión o consulta a la base de datos. |

### `GET /api/v1/reportes/catalogos`

Devuelve todos los catálogos/enum válidos para poblar los selectores del monolito. Requiere `X-API-Key`.

### `GET /api/v1/salud`

Health check público: estado del servicio, de la base de datos y del modo de LLM.

---

## Módulos de reportes

| Módulo | Colecciones | Filtros principales | Alertas del ETL |
| :--- | :--- | :--- | :--- |
| `general` | Atenciones (unión de 7 servicios) | fechas, genero, pnf, area | Concentración de atenciones por área |
| `medicina` | Consultas, Insumos | fechas, genero, pnf | Insumos vencidos, por vencer ≤ 30 días, stock crítico |
| `psicologia` | Morbilidad, Citas | fechas, pnf, tipo_consulta, estado | Citas pendientes, alto % de "No asistió", diagnóstico dominante |
| `orientacion` | Casos | fechas, genero, pnf | — |
| `trabajo_social` | Registros (unión de 4 submódulos) | fechas, pnf, submodulo | — |
| `discapacidad` | Registros | fechas, genero, pnf, tipo, grado | Casos graves, registros sin carnet |
| `referencias` | Remisiones | fechas, estado, servicio_destino | Referencias pendientes de resolución |
| `jornadas` | Jornadas (con asistentes y diagnósticos) | fechas, estado | Aforo alcanzado/superado, jornadas sin finalizar |
| `mobiliario` | Bienes (mobiliario + equipos) | fechas, tipo_bien, estado | Bienes inactivos |
| `transporte` | Vehículos, Rutas, Proveedores, Repuestos, Asignaciones, Mantenimientos | fechas, estado, tipo_vehiculo, seccion_transporte | Vehículos en mantenimiento, repuestos con bajo stock |

---

## Estructura del proyecto

```text
dirpoles-ia/
├── app/
│   ├── main.py                  # Punto de entrada FastAPI, CORS, ciclo de vida
│   ├── core/
│   │   ├── config.py            # Ajustes con Pydantic Settings (.env)
│   │   └── security.py          # Validación X-API-Key (comparación constante)
│   ├── db/
│   │   ├── session.py           # Engine SQLAlchemy READ-ONLY
│   │   └── queries/             # Consultas SQL parametrizadas por módulo
│   ├── schemas/                 # Enums y DTOs Pydantic (contratos)
│   │   ├── enums.py
│   │   ├── request.py           # ReporteRequestDTO
│   │   └── response.py          # ReporteResponseDTO
│   ├── services/
│   │   ├── etl_service.py       # Extracción + pipeline ETL con Pandas
│   │   ├── prompt_service.py    # Roles especializados y generador de prompts
│   │   └── gemini_service.py    # Cliente google-genai + simulado local
│   └── api/v1/endpoints/
│       └── reportes.py          # POST /generar y GET /catalogos
├── tests/                       # pytest: unitarios, integración BD y E2E
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── pyproject.toml               # Configuración de ruff, mypy y pytest
└── README.md
```

---

## Desarrollo y verificación

```bash
source .venv/bin/activate

ruff check app tests            # lint
ruff format app tests --check   # formato
mypy app                        # tipado estático
pytest                          # toda la suite (62 pruebas)
pytest -m "not bd"              # solo pruebas sin base de datos
```

Las pruebas de integración (`@pytest.mark.bd`) requieren la base de datos local accesible; se excluyen con `-m "not bd"`.

---

## Integración con el monolito PHP

Ejemplo mínimo con cURL desde PHP:

```php
$ch = curl_init('http://localhost:8000/api/v1/reportes/generar');
curl_setopt_array($ch, [
    CURLOPT_POST           => true,
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_HTTPHEADER     => [
        'Content-Type: application/json',
        'X-API-Key: ' . getenv('DIRPOLES_IA_API_KEY'),
    ],
    CURLOPT_POSTFIELDS => json_encode([
        'modulo'       => 'medicina',
        'intencion'    => 'alertas_y_anomalias',
        'filtros'      => ['fecha_inicio' => '2026-01-01', 'fecha_fin' => '2026-09-30'],
        'observacion_usuario' => 'Enfocarse en insumos con bajo stock.',
    ]),
]);
$respuesta = json_decode(curl_exec($ch), true);
curl_close($ch);

if ($respuesta['exito'] === true) {
    $markdown = $respuesta['informe_markdown']; // renderizar en la vista
}
```

**Principio de resiliencia:** el monolito debe tratar cualquier error (`401`, `422`, `503`, timeout) como una caída del servicio de analítica y seguir operando con sus vistas tradicionales. La base de datos nunca se escribe desde este microservicio.

---

## Seguridad

* Autenticación B2B por cabecera `X-API-Key` con comparación en tiempo constante (`hmac.compare_digest`).
* Credenciales únicamente en `.env` (incluido en `.gitignore`).
* Usuario de BD con privilegios `SELECT` exclusivamente.
* Sin endpoints de escritura; FastAPI no expone rutas que modifiquen datos.
