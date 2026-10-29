# REGLAS DE ARQUITECTURA Y CONSTITUCIÓN TÉCNICA: DIRPOLES-IA

> **Constitución Inmutable del Microservicio — Nivel 1**  
> **Proyecto:** Sistema DIRPOLES-4 (UPTAEB) & Ecosistema de Microservicios — Componente de Inteligencia Artificial  
> **Repositorio:** `DIRPOLES-IA` | **Versión:** 2.0.0 (Arquitectura Desacoplada Multitenant)  
> **Documentos Satélites:** [`docs/PIPELINES_IA.md`](docs/PIPELINES_IA.md) (analítica de dominio), [`docs/Documentacion_componenteIA.md`](docs/Documentacion_componenteIA.md) (guía conceptual) y [`docs/ENTREGA_FASE_II_COMPONENTE_IA.md`](docs/ENTREGA_FASE_II_COMPONENTE_IA.md) (documento formal de Fase II).

---

## 1. Propósito y Metadatos del Repositorio

`DIRPOLES-IA` es un microservicio autónomo en **Python 3.12+ (FastAPI)** dedicado a la extracción analítica, procesamiento vectorizado con **Pandas**, detección automática de anomalías e inferencia narrativa con modelos de lenguaje generativo (**Google Gemini** y motor determinista de respaldo). 

Opera bajo una arquitectura desacoplada en dos modalidades:
1. **Modo Pull (API V1):** Extracción de datos en solo lectura (`READ-ONLY`) desde la base de datos del monolito **DIRPOLES-4** (PHP 8.3) a través de un adaptador relacional.
2. **Modo Push Universal (API V2):** Ingesta analítica en memoria sin base de datos (`POST /api/v2/analizar`) para cualquier consumidor externo (Node.js, Python, Laravel, Go).

* **Convención Lingüística:** Español técnico para nombres de variables de negocio, funciones de dominio, comentarios, commits y documentación. Inglés reservado para protocolos HTTP, librerías y contratos OpenAPI.
* **Aislamiento en Entorno Virtual:** Todo comando o script debe ejecutarse dentro de `.venv`.

---

## 2. Las Reglas Innegociables (Mandatos de Diseño)

1. **Desacoplamiento Estricto B2B:** Solo atiende peticiones backend-to-backend autenticadas con `X-API-Key`. El navegador del usuario final **nunca** se conecta directamente a este microservicio.
2. **Acceso a Base de Datos Exclusivamente Solo Lectura (`READ-ONLY`):** El usuario MySQL (`dirpoles_ia_reader`) tiene permisos limitados a `SELECT`. **Queda terminantemente prohibido ejecutar sentencias `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` o transacciones de escritura.**
3. **Manejo Dual de Esquemas Relacionales (V1):** La base de negocio (`dirpoles_business`) es el esquema por defecto; el esquema de seguridad (`dirpoles_security`) debe consultarse siempre con prefijo explícito `{seguridad}.empleado`.
4. **Resiliencia Absoluta y Patrón Fallback Determinista:** Si la API externa de Google Gemini falla (timeout, 429, 500 o falta de conexión), el servicio conmuta automáticamente a `ClienteSimulado` (modo `simulado_fallback`). **Jamás devolver error 500 por caída o latencia del LLM externo.**
5. **Privacidad de Datos y Cero Fuga de PII a la IA:** Nunca enviar datos crudos, historias clínicas, cédulas o nombres a Google Gemini. Solo se transmiten métricas agregadas precalculadas por Pandas en un JSON sintetizado y validado.
6. **Tipado Estricto y Validación Pydantic v2:** Todas las funciones deben incluir type hints exhaustivos (`mypy` estricto sin tipos implícitos). Todo payload se valida con DTOs Pydantic antes de procesar.
7. **Formato Visual Obligatorio (Markdown + Mermaid.js):** El informe devuelto debe incluir encabezados claros, tablas Markdown formateadas, citas de alertas (`> ⚠️ **Punto Crítico:**`) y al menos un diagrama visual nativo Mermaid (`pie` o `xychart-beta`).
8. **Inyección de Identidad y RBAC (V1):** Recibe `id_empleado` (inyectado server-side por DIRPOLES-4 desde la sesión) para restringir registros por especialista. Si es `null`, visibilidad global de administrador. Si es inválido ($\le 0$), el monolito debe rechazarlo antes de llamar a la IA.
9. **Arquitectura Desacoplada por Adaptadores y Conocimiento:** Las consultas SQL residen exclusivamente en [`app/adapters/`](app/adapters/) y la base de conocimiento institucional reside en [`app/knowledge/`](app/knowledge/). El núcleo analítico no debe codificar nombres de tablas o carreras universitarias directamente.

---

## 3. Arquitectura de Respuesta y Manejo de Errores

### 3.1. Rutas Disponibles
* `POST /api/v1/reportes/generar` (Requiere `X-API-Key`, modo Pull relacional para DIRPOLES-4, responde `ReporteResponseDTO`).
* `GET /api/v1/reportes/catalogos` (Requiere `X-API-Key`, catálogo de valores válidos de la V1).
* `POST /api/v2/analizar` (Requiere `X-API-Key`, modo Push universal sin base de datos, responde `AnalisisResponseV2DTO`).
* `GET /api/v1/salud` (Público / Sin API Key, health check del servicio, conectividad de base de datos y modo LLM).

### 3.2. Contrato de Éxito V1 (`ReporteResponseDTO`)
```json
{
  "exito": true,
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "informe_markdown": "### 📊 Informe...\n\n```mermaid\npie...",
  "meta": {
    "registros_procesados": 450,
    "tiempo_procesamiento_seg": 1.25,
    "modo_informe": "gemini | simulado | simulado_fallback"
  }
}
```

### 3.3. Contrato de Éxito V2 (`AnalisisResponseV2DTO`)
```json
{
  "exito": true,
  "dominio": "logistica_flotas",
  "intencion": "resumen_ejecutivo",
  "informe_markdown": "### 📊 Informe de Análisis...\n\n```mermaid\npie...",
  "meta": {
    "registros_procesados": 1200,
    "tiempo_procesamiento_seg": 0.45,
    "modo_informe": "simulado | gemini | simulado_fallback"
  }
}
```

### 3.4. Códigos de Error HTTP
* `401 Unauthorized`: Cabecera `X-API-Key` ausente o no registrada en el sistema multitenant.
* `422 Unprocessable Entity`: Validación fallida de Pydantic (dominio o intención inválidos, rango de fechas incoherente o totales negativos).
* `503 Service Unavailable`: Falla de conectividad hacia MySQL en la V1 (`{"exito": false, "detalle": "...", "error": "..."}`).

---

## 4. Anatomía del Estado Global, Autenticación y Multitenancy

* **Sin Sesiones Web (Stateless):** El microservicio no genera cookies ni sesiones web.
* **Seguridad B2B Multitenant ([`app/core/consumers.py`](app/core/consumers.py)):**
  - Mapeo de `api_key -> PerfilConsumidor` validado en tiempo constante (`hmac.compare_digest`).
  - Soporta múltiples clientes activos (`dirpoles4`, clientes externos).
  - Carga opcional declarativa desde `config/consumidores.json` con fallback a `.env`.
* **Variables de Entorno Requeridas (`.env`):**
  - Servidor: `HOST`, `PORT`, `DEBUG`, `ALLOWED_ORIGINS`
  - Seguridad: `DIRPOLES_IA_API_KEY`
  - Base de Datos (V1): `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME_BUSINESS`, `DB_NAME_SECURITY`
  - Inteligencia Artificial: `GEMINI_API_KEY`, `GEMINI_MODEL` (ej. `gemini-3.5-flash`), `MOCK_LLM` (`True`/`False`)
  - Analítica: `UMBRAL_STOCK_CRITICO_INSUMOS` (10), `UMBRAL_STOCK_CRITICO_REPUESTOS` (5), `LIMITE_REGISTROS` (5000)

---

## 5. Mapeo de Componentes, Adaptadores y Conocimiento

```
app/
├── adapters/                  # Capa de extracción de datos
│   ├── base.py                # AdaptadorFuenteDatos (Protocol) y Extraccion
│   └── dirpoles4/             # AdaptadorDirpoles4SQL y consultas MySQL
├── knowledge/                 # Base de conocimiento (en memoria o BD SQLite/MySQL)
│   ├── base.py                # BaseConocimiento (Protocol desacoplado)
│   └── dirpoles4/             # Roles, PNF oficial, alertas canónicas y directrices
├── core/
├── config.py              # Ajustes singleton Pydantic
│   ├── consumers.py           # PerfilConsumidor y RegistroConsumidores multitenant
│   └── security.py            # Dependencia validar_api_key (timing-safe)
├── services/
│   ├── etl_service.py         # Motor analítico vectorial Pandas (V1)
│   ├── analisis_v2_service.py # Motor analítico universal en memoria (V2)
│   ├── prompt_service.py      # Generador de prompts y filtro de privacidad
│   └── gemini_service.py      # ClienteGemini y ClienteSimulado
└── api/
    ├── v1/endpoints/reportes.py # API V1 (Pull DIRPOLES-4)
    └── v2/endpoints/analisis.py # API V2 (Push Universal)
```

> **Persistencia de Conocimiento:** La base de conocimiento puede ser estática (`ConocimientoDirpoles4`) o estar respaldada por una base de datos física (SQLite local o tabla relacional `dirpoles_knowledge`) implementando la interfaz `BaseConocimiento` sin modificar los servicios centrales.

---

## 6. Cheat Sheet de Helpers Core

* **Seguridad y Consumidores (`app/core/`):**
  - `validar_api_key(x_api_key) -> PerfilConsumidor`: Dependencia FastAPI para autenticación multitenant.
  - `obtener_registro_consumidores() -> RegistroConsumidores`: Singleton de consumidores activos.
* **Capa de Adaptadores (`app/adapters/`):**
  - `AdaptadorFuenteDatos`: Protocolo con método `extraer(modulo, filtros, id_empleado, limit) -> Extraccion`.
  - `AdaptadorDirpoles4SQL`: Implementación relacional para DIRPOLES-4 con SQLAlchemy singleton.
* **Capa de Conocimiento (`app/knowledge/`):**
  - `BaseConocimiento`: Protocolo con `obtener_rol()`, `obtener_enfoque()`, `es_alerta_autorizada()`, `resolver_directriz()`.
  - `ConocimientoDirpoles4`: Especificación institucional para la UPTAEB.
* **Servicios Analíticos y LLM (`app/services/`):**
  - `etl_service.procesar(modulo, filtros, id_empleado, limit, adaptador=...) -> Resumen`
  - `analisis_v2_service.ejecutar_analisis_v2(peticion) -> AnalisisResponseV2DTO`
  - `prompt_service.construir_prompts(modulo, intencion, resumen, obs, conocimiento=...) -> tuple[str, str]`
  - `gemini_service.obtener_cliente() -> ClienteIA`: Retorna `ClienteGemini` o `ClienteSimulado`.

---

## 7. Matriz Resumen de Módulos (V1 DIRPOLES-4)

| Clave (`Modulo`) | Tablas Base Principales | Filtros Admitidos | Alertas ETL Críticas |
| :--- | :--- | :--- | :--- |
| `general` | 7 atenciones (`UNION ALL`), `beneficiario`, `pnf` | fechas, genero, pnf, area | Concentración de área $\ge 40\%$ |
| `medicina` | `consulta_medica`, `insumos`, `presentacion_insumo` | fechas, genero, pnf | Stock crítico $< 10$, insumos vencidos |
| `psicologia` | `consulta_psicologica`, `cita`, `estado_cita` | fechas, pnf, tipo_consulta, estado | Inasistencia a citas $> 25\%$ |
| `orientacion` | `orientacion`, `solicitud_de_servicio`, `pnf` | fechas, genero, pnf | Concentración de motivos de consulta |
| `discapacidad` | `discapacidad`, `beneficiario`, `pnf` | fechas, genero, pnf, tipo, grado | Casos graves sin asistencia, carnetización |
| `trabajo_social` | `becas`, `exoneracion`, `fames`, `gestion_emb` | fechas, pnf, submodulo | Concentración de área $\ge 60\%$ |
| `referencias` | `referencias`, `servicio` (origen y destino) | fechas, estado, servicio_destino | Referencias pendientes $> 15$ días |
| `jornadas` | `jornadas_medicas`, beneficiarios, diagnósticos | fechas, estado | Aforo efectivo $< 40\%$ |
| `mobiliario` | `mobiliario`, `equipos`, tipos | fechas, tipo_bien, estado | Proporción de bienes inactivos |
| `transporte` | `vehiculos`, `rutas`, `proveedores`, `repuestos` | fechas, seccion, tipo_vehiculo, estado | Repuestos $< 5$ unidades, flota inactiva |

---

## 8. Anti-Patrones Prohibidos (Negative Constraints)

* ❌ **NUNCA ejecutar sentencias de escritura en BD (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).** El servicio es estrictamente de solo lectura.
* ❌ **NUNCA enviar datos personales (PII) a Google Gemini.** Cédulas, nombres completos e historias clínicas deben permanecer en el servidor local.
* ❌ **NUNCA omitir la degradación elegante a `ClienteSimulado`.** Ante cualquier fallo de Gemini o de red, responder con el informe determinista local (`simulado_fallback`).
* ❌ **NUNCA omitir la cabecera `X-API-Key` ni debilitar su validación.** No usar comparaciones directas de cadenas (`==`); usar siempre `hmac.compare_digest`.
* ❌ **NUNCA acoplar el núcleo analítico a esquemas de base de datos específicos.** Nuevas fuentes de datos deben implementarse mediante `AdaptadorFuenteDatos`.
* ❌ **NUNCA alterar la estructura del JSON devuelto a DIRPOLES-4.** La respuesta V1 debe ajustarse estrictamente a `ReporteResponseDTO`.

---

## 9. Plantillas Canónicas (Boilerplates de Oro)

### 9.1. Invocación Desacoplada de ETL con Adaptador
```python
from app.adapters.base import AdaptadorFuenteDatos
from app.services import etl_service

def analizar_con_fuente_personalizada(adaptador: AdaptadorFuenteDatos) -> dict:
    return etl_service.procesar(
        modulo=Modulo.MEDICINA,
        filtros=FiltrosDTO(),
        id_empleado=None,
        adaptador=adaptador,
    )
```

### 9.2. Ingesta Universal V2 en Modo Push
```python
from app.schemas.v2 import AnalisisRequestV2DTO, MetricasEntradaV2DTO
from app.services.analisis_v2_service import ejecutar_analisis_v2

peticion = AnalisisRequestV2DTO(
    dominio="urgencias",
    metricas=MetricasEntradaV2DTO(totales={"atenciones": 150}),
)
respuesta = ejecutar_analisis_v2(peticion)
```

---

## 10. Protocolo de Trabajo y Verificación

### 10.1. Flujo de Desarrollo
1. **Contrato:** Definir DTOs en [`app/schemas/`](app/schemas/).
2. **Adaptador / Conocimiento:** Si aplica a un nuevo consumidor, extender `AdaptadorFuenteDatos` o `BaseConocimiento`.
3. **Servicio:** Implementar transformaciones vectorizadas en Pandas con tipado estricto.
4. **Verificación:** Ejecutar suite completa con `unittest` antes de dar por cerrada cualquier tarea.

### 10.2. Comandos de Verificación de Calidad
```bash
# 1. Suite completa de pruebas unitarias y de integración
.venv/bin/python3 -m unittest discover tests/ -v

# 2. Pruebas específicas de contrato DIRPOLES-4
.venv/bin/python3 -m unittest tests/test_contrato_dirpoles4.py -v

# 3. Pruebas de la API Universal V2
.venv/bin/python3 -m unittest tests/test_api_v2_universal.py -v
```
