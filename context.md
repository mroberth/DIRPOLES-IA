# ESPECIFICACIÓN TÉCNICA Y ARQUITECTURA DE CONTEXTO: MICROSERVICIO DIRPOLES-IA

> **Documento de Contexto y Referencia de Arquitectura (`context.md`) — Versión 3**  
> **Proyecto:** Sistema de Control e Inventario de Beneficiarios de Bienestar Estudiantil (**DIRPOLES-4**)  
> **Componente:** Microservicio de Analítica de Datos e Inteligencia Artificial (**DIRPOLES-IA**)  
> **Institución:** Universidad Politécnica Territorial de Lara Andrés Eloy Blanco (UPTAEB) — PNF en Informática  

---

## 1. INFORMACIÓN GENERAL Y PROPÓSITO DEL SISTEMA

### 1.1. Contexto del Proyecto
El sistema **DIRPOLES-4** es un monolito desarrollado en PHP 8.3 diseñado para gestionar la atención, inventario y servicios de bienestar estudiantil de la UPTAEB. Como parte del requisito del trayecto final del PNF en Informática, se integra un componente de Inteligencia Artificial mediante una arquitectura de **microservicios orientada a la analítica de datos y generación de reportes narrativos inteligibles**.

### 1.2. Propósito de `DIRPOLES-IA`
`DIRPOLES-IA` es un microservicio autónomo en Python (FastAPI) que asume la responsabilidad de:
1. Conectarse de forma directa e independiente a la base de datos relacional del sistema.
2. Extraer, transformar y procesar los registros crudos de atenciones y servicios utilizando **Pandas**.
3. Detectar tendencias, patrones, picos de demanda y anomalías críticas.
4. Orquestar la ingeniería de prompts adaptada dinámicamente al módulo correspondiente y consultar la API de **Google AI Studio (Gemini API)**.
5. Devolver un informe técnico y narrativo formateado directamente en **Markdown** al monolito PHP.

### 1.3. Principio de Desacoplamiento y Resiliencia
* **Aislamiento Total:** Si el microservicio `DIRPOLES-IA` o la API remota de Gemini fallan, quedan fuera de línea o experimentan latencia, el monolito **DIRPOLES-4** continuará operando sus funciones administrativas, operativas y de consultas tradicionales al 100% sin ser bloqueado.
* **Cero Impacto en BD:** Las operaciones del microservicio son puramente de **Lectura (`READ-ONLY`)**, garantizando la integridad referencial y transaccional del sistema PHP.

---

## 2. ARQUITECTURA DE SISTEMAS Y FLUJO BACKEND-TO-BACKEND (B2B)

### 2.1. Diagrama de Flujo de Interacción
```text
  [ Usuario (Admin/Empleado) ]
                │
                │ 1. Selección de Módulo, Filtros e Intención
                ▼
      ┌──────────────────┐
      │  PHP MONOLITO    │  (Verifica RBAC y permisos de 'crear' en reportes)
      │   (DIRPOLES-4)   │
      └─────────┬────────┘
                │
                │ 2. Petición HTTP POST (Filtros + Header X-API-Key)
                ▼
      ┌──────────────────┐
      │  MICROSERVICIO   │  (Valida X-API-Key y DTO con Pydantic)
      │   DIRPOLES-IA    │
      └────┬─────────┬───┘
           │         │
 3. SQL    │         │ 5. Selección de Rol Especializado + Prompt + Inferencia
 Read-Only │         │
           ▼         ▼
    ┌──────────┐   ┌──────────────────────────┐
    │ MySQL /  │   │  Google AI Studio API    │
    │ MariaDB  │   │  (Modelo Gemini)         │
    └──────────┘   └──────────────────────────┘
```

### 2.2. Flujo Paso a Paso
1. **Invocación desde Monolito:** El usuario con permisos ingresa al módulo de reportes en PHP, selecciona los filtros deseados (rango de fechas, carrera, área) y la **intención del informe** (ej. Resumen Ejecutivo, Detección de Anomalías).
2. **Petición B2B:** PHP realiza una petición cURL/Guzzle asíncrona hacia FastAPI pasando un payload JSON liviano con los parámetros de la consulta.
3. **Extracción y Procesamiento Local:** Python recibe la petición, se conecta a la BD con un usuario `READ-ONLY`, ejecuta las consultas SQL correspondientes a los filtros y carga los datos crudos en un DataFrame de `Pandas`.
4. **Transformación y Análisis:** Python calcula agrupaciones, porcentajes, variaciones y alertas.
5. **Generación con LLM:** Python inyecta el **Rol Especializado según el Módulo** (`prompt_service.py`), ensambla el prompt estructurado, consulta a la API de Google Gemini mediante el SDK `google-genai` y recibe el informe narrativo.
6. **Respuesta en Markdown:** FastAPI responde con un JSON que contiene el informe formateado en Markdown.
7. **Renderizado en PHP:** Monolito PHP recibe el Markdown y lo muestra estilizado en el contenedor web del módulo de reportes.

---

## 3. ROLES Y RESPONSABILIDADES DE CADA COMPONENTE

| Componente | Tecnología | Responsabilidad Principal |
| :--- | :--- | :--- |
| **Monolito Web** | PHP 8.3 (Architecture DIRPOLES-4) | Autenticación, RBAC (Control de Acceso), Renderizado UI/UX, captura de filtros e intenciones del usuario, recepción y maquetado de Markdown. |
| **Base de Datos** | MySQL / MariaDB (Dual Schema) | Almacenamiento persistente (`dirpoles_business` y `dirpoles_security`). Proporciona acceso `READ-ONLY` al microservicio. |
| **Microservicio IA** | Python 3.12 + FastAPI | Endpoint B2B, extracción de datos crudos, pipeline ETL con `Pandas`, orquestación de Prompts Multidominio y comunicación con Gemini API. |
| **Proveedor LLM** | Google AI Studio (Gemini) | Inferencia de lenguaje natural y síntesis del análisis narrativo a partir del contexto provisto por Python. |

---

## 4. ALCANCE Y MÓDULOS DE REPORTES CUBIERTOS

El microservicio procesará datos de cualquiera de los **10 módulos de reportes** definidos en la estructura del Sidebar y respaldados por el modelo `ReportesModel.php` y las vistas de **DIRPOLES-4**:

1. **General:** Consolidado de las atenciones registradas en 7 servicios (Medicina, Psicología, Orientación, Discapacidad, Becas, Exoneración y FAMES) por beneficiario, fecha, género y PNF. Disponible solo para Administrador/Superusuario.
2. **Medicina:** Consultas médicas (motivo, diagnóstico, tratamiento) e inventario de insumos médicos con stock, fecha de vencimiento y estatus.
3. **Psicología:** Morbilidad psicológica (tipo de consulta y diagnóstico) y agenda de citas con su estado (pendiente, atendida, no asistió, etc.).
4. **Orientación:** Casos de orientación registrados: motivo de consulta, descripción del caso e indicaciones.
5. **Discapacidad:** Registros de discapacidad: tipo, grado, requerimiento de asistencia (Sí/No) y poseedores de carnet.
6. **Trabajo Social:** Registros de los 4 submódulos de Trabajo Social: Becas, Exoneraciones, FAMES y Gestión de Embarazo.
7. **Referencias:** Remisiones internas entre servicios/áreas del sistema, con estado (Pendiente, Aceptada, Rechazada) y motivo.
8. **Jornadas:** Jornadas médicas: cabecera (nombre, tipo, ubicación, fechas, estatus, aforo) con totales de asistentes y diagnósticos emitidos.
9. **Mobiliario:** Inventario actual de bienes: mobiliario y equipos con categoría, cantidad y estatus (Activo/Inactivo).
10. **Transporte:** Secciones del subsistema: vehículos, rutas, proveedores, repuestos, asignaciones de rutas y mantenimientos.

---

## 5. ESTRUCTURA DEL PROYECTO (CLEAN ARCHITECTURE EN FASTAPI)

El microservicio seguirá una arquitectura por capas para garantizar mantenibilidad y facilitar la evaluación académica:

```text
dirpoles-ia/
├── app/
│   ├── main.py                  # Punto de entrada FastAPI, Middlewares y CORS
│   ├── core/
│   │   ├── config.py            # Carga de variables de entorno con Pydantic Settings
│   │   └── security.py          # Validación de Seguridad B2B (X-API-Key)
│   ├── db/
│   │   ├── session.py           # Conexión SQLAlchemy (Engine READ-ONLY)
│   │   └── queries/             # Consultas SQL puras por módulo
│   │       ├── medicina_queries.py
│   │       ├── psicologia_queries.py
│   │       ├── trabajo_social_queries.py
│   │       ├── transporte_queries.py
│   │       └── general_queries.py
│   ├── schemas/                 # DTOs Pydantic (Contratos de Petición y Respuesta)
│   │   ├── request.py           # ReporteRequestDTO
│   │   └── response.py          # ReporteResponseDTO
│   ├── services/
│   │   ├── etl_service.py       # Procesamiento de DataFrames con Pandas
│   │   ├── prompt_service.py    # Selección de Rol Especializado y Generador de Prompts
│   │   └── gemini_service.py    # Cliente API Google AI Studio (google-genai)
│   └── api/
│       └── v1/
│           └── endpoints/
│               └── reportes.py  # Router principal HTTP POST /api/v1/reportes/generar
├── .env.example                 # Plantilla de variables de entorno
├── requirements.txt             # Dependencias del proyecto
└── README.md                    # Documentación de ejecución
```

---

## 6. ESPECIFICACIÓN DE SEGURIDAD Y CONTRATOS API (DTOs)

### 6.1. Seguridad Backend-to-Backend
Todas las peticiones entrantes a `DIRPOLES-IA` deben incluir la cabecera HTTP:
```http
X-API-Key: <LLAVE_SECRETA_COMPARTIDA_EN_ENV>
```
Si la cabecera es omitida o incorrecta, FastAPI responderá con código HTTP `401 Unauthorized`.

### 6.2. DTO de Entrada (`ReporteRequestDTO`)
JSON que PHP envía al microservicio:
```json
{
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "filtros": {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-09-30",
    "carrera_id": 3,
    "area_id": null
  },
  "observacion_usuario": "Enfocarse en insumos con bajo stock para las jornadas de octubre."
}
```

### 6.3. DTO de Salida (`ReporteResponseDTO`)
JSON que FastAPI responde a PHP:
```json
{
  "exito": true,
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "informe_markdown": "### 📊 Informe de Análisis Inteligente: Módulo Medicina\n\n**Periodo:** 01/01/2026 al 30/09/2026\n\n#### 1. Resumen Ejecutivo\nDurante el periodo analizado se registraron un total de **450 consultas médicas**...\n\n#### 2. Detección de Anomalías y Puntos Críticos\n* ⚠️ **Stock Crítico:** El insumo *Paracetamol 500mg* presenta solo 2 unidades disponibles.\n* 📈 **Incremento de Patologías:** Las afecciones respiratorias aumentaron un **35%** respecto al mes anterior.\n\n#### 3. Recomendaciones Operativas\n1. Priorizar la adquisición de analgésicos antes de las jornadas de octubre.\n...",
  "meta": {
    "registros_procesados": 450,
    "tiempo_procesamiento_seg": 2.15
  }
}
```

---

## 7. PIPELINE ETL Y ESTRATEGIA DE PROMPTS MULTIDOMINIO

### 7.1. Pipeline de Datos en Python (`etl_service.py`)
1. **Extracción:** Carga de resultados SQL a `pandas.DataFrame`.
2. **Limpieza:** Tratamiento de nulos, formateo de fechas y casting de tipos.
3. **Agregación:** `df.groupby()`, conteos, promedios y porcentajes de participación.
4. **Comparativa:** Cálculo de variaciones porcentuales ($((V_2 - V_1) / V_1) \times 100$).
5. **Detección de Umbrales:** Filtrado de insumos con stock $< \text{umbral\_critico}$ o patologías en top 20%.

### 7.2. Estrategia de Prompts Multidominio (`prompt_service.py`)

Para garantizar máxima precisión en el lenguaje técnico y evitar sesgos, la Dirección de Políticas Estudiantiles (**DIRPOLES**) no se trata como un dominio exclusivamente médico, sino como un organismo integral de bienestar universitario.

#### Inyección Dinámica del Rol Especializado por Módulo:

```python
ROLES_POR_MODULO = {
    # 1. Salud Médica y Eventos
    "medicina": "Especialista en gestión de servicios médicos universitarios, morbilidad clínica y administración de inventario de insumos de salud.",
    "jornadas": "Especialista en salud comunitaria, organización de jornadas asistenciales y prevención epidemiológica universitaria.",
    
    # 2. Salud Mental y Desarrollo Académico
    "psicologia": "Especialista en salud mental universitaria, morbilidad psicológica y gestión de agenda de atención clínica.",
    "orientacion": "Especialista en orientación educativa, psicopedagogía y desarrollo integral del estudiante universitario.",
    
    # 3. Inclusión y Protección Social
    "discapacidad": "Especialista en políticas de inclusión universitaria, accesibilidad y atención a la diversidad funcional.",
    "trabajo_social": "Especialista en trabajo social universitario, evaluación socioeconómica y programas de protección (Becas, Exoneraciones, FAMES y Gestión de Embarazo).",
    "referencias": "Coordinador de la red de remisiones e interconsultas internas entre servicios de bienestar estudiantil.",
    
    # 4. Logística e Infraestructura
    "mobiliario": "Analista de gestión de bienes públicos, mobiliario e inventario de equipamiento institucional.",
    "transporte": "Analista de gestión de flotas, logística de transporte universitario, rutas y mantenimiento vehicular.",
    
    # 5. Consolidado Ejecutivo
    "general": "Analista Ejecutivo de Datos de la Dirección de Políticas Estudiantiles, con visión integral de salud, desarrollo social y logística universitaria."
}
```

#### Plantilla del System Prompt Generado:
```text
[SYSTEM PROMPT]
Eres un {rol_especializado_modulo} para la UPTAEB.
Tu objetivo es redactar un informe claro, profesional, riguroso y formal basado EXCLUSIVAMENTE en los datos estadísticos procesados que te son suministrados por la capa analítica en Pandas.
Debes emplear la terminología técnica adecuada para la naturaleza de este módulo y responder en formato Markdown limpio usando encabezados, listas con viñetas y negritas para resaltar métricas clave.

[USER PROMPT]
Módulo Analizado: {modulo}
Intención del Informe: {intencion}
Periodo de Análisis: {fecha_inicio} a {fecha_fin}

DATOS PROCESADOS (Métricas, Agregaciones y Alertas detectadas por Pandas):
{resumen_estadistico_json}

INSTRUCCIONES ADICIONALES DEL USUARIO:
{observacion_usuario}

Estructura requerida para la respuesta en Markdown:
1. Resumen Ejecutivo
2. Hallazgos Clave y Puntos Críticos
3. Recomendaciones Operativas para la Toma de Decisiones
```

---

## 8. CONFIGURACIÓN TÉCNICA Y VARIABLES DE ENTORNO (`.env`)

### Dependencias Principales (`requirements.txt`):
```text
fastapi>=0.115.0
uvicorn[standard]>=0.30.0
pydantic>=2.8.0
pydantic-settings>=2.4.0
pandas>=2.2.0
sqlalchemy>=2.0.0
pymysql>=1.1.0
google-genai>=0.1.0
python-dotenv>=1.0.0
```

### Variables de Entorno (`.env`):
```env
# Servidor FastAPI
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Seguridad B2B
DIRPOLES_IA_API_KEY=tu_clave_secreta_b2b_compartida

# Conexión a Base de Datos (READ-ONLY)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=dirpoles_ia_reader
DB_PASSWORD=contraseña_segura_lectura
DB_NAME_BUSINESS=dirpoles_business
DB_NAME_SECURITY=dirpoles_security

# Proveedor de IA (Google AI Studio)
GEMINI_API_KEY=AIzaSy...Tu_ApiKey_Google_AI_Studio
GEMINI_MODEL=gemini-1.5-flash
```

---
*Este documento constituye la especificación oficial de arquitectura para el desarrollo y despliegue del microservicio `DIRPOLES-IA`.*
