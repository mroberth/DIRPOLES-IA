# REGLAS DE ARQUITECTURA Y CONSTITUCIÓN TÉCNICA: DIRPOLES-IA

> **Constitución Inmutable del Microservicio — Nivel 1**  
> **Proyecto:** Sistema DIRPOLES-4 (UPTAEB) — Componente de Inteligencia Artificial  
> **Repositorio:** `DIRPOLES-IA` | **Versión:** 1.0.0  
> **Satélite de Dominio:** [`docs/PIPELINES_IA.md`](docs/PIPELINES_IA.md) (consultar para especificaciones analíticas exhaustivas).

---

## 1. Propósito y Metadatos del Repositorio

`DIRPOLES-IA` es un microservicio autónomo en **Python 3.12+ (FastAPI)** dedicado exclusivamente a la extracción analítica, procesamiento vectorizado con **Pandas** e inferencia narrativa con modelos de lenguaje generativo (**Google Gemini** y motor determinista de respaldo). Atiende las solicitudes del monolito institucional **DIRPOLES-4** (PHP 8.3) para los 10 módulos de bienestar estudiantil de la UPTAEB.

* **Convención Lingüística:** Español técnico para nombres de variables de negocio, funciones de dominio, comentarios, commits y documentación. Inglés estándar reservado únicamente para sintaxis del lenguaje, protocolos HTTP, librerías y contratos de esquemas universales.
* **Documento Satélite de Dominio:** Toda regla analítica detallada, esquema de features, fórmulas vectoriales y especificación profunda de cada módulo reside en [`docs/PIPELINES_IA.md`](docs/PIPELINES_IA.md).

---

## 2. Las Reglas Innegociables (Mandatos de Diseño)

1. **Desacoplamiento Estricto Backend-to-Backend (B2B):** Solo atiende peticiones HTTP internas provenientes de DIRPOLES-4 vía `POST /api/v1/reportes/generar`. El navegador del usuario final **nunca** se conecta directamente a este microservicio.
2. **Acceso a Base de Datos Exclusivamente Solo Lectura (`READ-ONLY`):** El usuario MySQL (`dirpoles_ia_reader`) tiene permisos limitados a `SELECT`. **Queda terminantemente prohibido ejecutar sentencias `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER` o crear transacciones de escritura.**
3. **Manejo Dual de Esquemas Relacionales:** La base de datos de negocio (`dirpoles_business`) es el esquema por defecto; el esquema de seguridad (`dirpoles_security`) debe consultarse siempre con prefijo explícito `{seguridad}.empleado`.
4. **Resiliencia Absoluta y Patrón Fallback Determinista:** Si la API externa de Google Gemini falla (timeout, 429, 500 o falta de conexión), el servicio conmuta automáticamente a `ClienteSimulado` (modo `simulado_fallback`). **Jamás devolver error 500 por caída o latencia del LLM externo.**
5. **Privacidad de Datos y Cero Fuga de PII a la IA:** Nunca enviar datos crudos, historias clínicas, cédulas o nombres a Google Gemini. Solo se transmiten métricas agregadas precalculadas por Pandas en un JSON sintetizado.
6. **Tipado Estricto y Validación Pydantic v2:** Todas las funciones deben incluir type hints exhaustivos (`mypy` estricto sin tipos implícitos). Todo payload se valida con DTOs Pydantic antes de tocar la base de datos.
7. **Formato Visual Obligatorio (Markdown + Mermaid.js):** El informe devuelto debe incluir encabezados claros, tablas Markdown formateadas, citas de alertas (`> ⚠️ **Punto Crítico:**`) y al menos un diagrama visual nativo Mermaid (`pie` o `xychart-beta`).
8. **Inyección de Identidad y RBAC:** El microservicio no maneja sesiones. Recibe `id_empleado` (inyectado server-side por DIRPOLES-4 desde la sesión) para restringir registros por empleado cuando proceda. Si es `null`, visibilidad global.
9. **Aislamiento en Entorno Virtual:** Todo comando o script debe ejecutarse dentro del entorno virtual `.venv`.

---

## 3. Arquitectura de Respuesta y Manejo de Errores

### 3.1. Rutas Disponibles
* `POST /api/v1/reportes/generar` (Requiere `X-API-Key`, responde `ReporteResponseDTO`).
* `GET /api/v1/reportes/catalogos` (Requiere `X-API-Key`, catálogo de valores válidos).
* `GET /api/v1/salud` (Público / Sin API Key, health check del servicio, base de datos y modo LLM).

### 3.2. Contrato Único de Éxito (`ReporteResponseDTO`)
```json
{
  "exito": true,
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "informe_markdown": "### 📊 Informe...\n\n```mermaid\npie...",
  "meta": {
    "registros_procesados": 450,
    "tiempo_procesamiento_seg": 12.03,
    "modo_informe": "gemini | simulado | simulado_fallback"
  }
}
```

### 3.3. Códigos de Error HTTP
* `401 Unauthorized`: Cabecera `X-API-Key` ausente o no coincide con `DIRPOLES_IA_API_KEY`.
* `422 Unprocessable Entity`: Validación fallida de Pydantic (módulo o intención inválidos, rango de fechas incoherente o filtro de estado ajeno al catálogo permitido para ese módulo).
* `503 Service Unavailable`: Falla de conectividad o consulta SQL hacia MySQL (`{"exito": false, "detalle": "...", "error": "..."}`).

---

## 4. Anatomía del Estado Global, Autenticación y Entorno

* **Sin Sesiones Web (Stateless):** El microservicio no genera cookies ni sesiones PHP.
* **Seguridad B2B:** Cabecera HTTP `X-API-Key` validada con `hmac.compare_digest` en [`app/core/security.py`](app/core/security.py) para neutralizar ataques de tiempo (timing attacks).
* **Variables de Entorno Requeridas (`.env`):**
  - Servidor: `HOST`, `PORT`, `DEBUG`, `ALLOWED_ORIGINS`
  - Seguridad: `DIRPOLES_IA_API_KEY`
  - Base de Datos: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME_BUSINESS`, `DB_NAME_SECURITY`
  - Inteligencia Artificial: `GEMINI_API_KEY`, `GEMINI_MODEL` (ej. `gemini-3.5-flash`), `MOCK_LLM` (`True`/`False`)
  - Analítica: `UMBRAL_STOCK_CRITICO_INSUMOS` (10), `UMBRAL_STOCK_CRITICO_REPUESTOS` (5), `LIMITE_REGISTROS` (5000)

---

## 5. Mapeo de Datos, Entidades y Roles

### 5.1. Doble Esquema Relacional
* **`dirpoles_business`:** `consulta_medica`, `insumos`, `presentacion_insumo`, `solicitud_de_servicio`, `beneficiario`, `pnf`, `consulta_psicologica`, `cita`, `estado_cita`, `orientacion`, `discapacidad`, `becas`, `exoneracion`, `fames`, `gestion_emb`, `referencias`, `servicio`, `jornadas_medicas`, `jornada_beneficiarios`, `jornada_diagnosticos`, `mobiliario`, `tipo_mobiliario`, `equipos`, `tipo_equipo`, `vehiculos`, `rutas`, `proveedores`, `repuestos_vehiculos`, `asignaciones_rutas`, `mantenimiento_vehiculos`.
* **`dirpoles_security`:** Tabla `empleado` (accedida mediante `f"{seguridad}.empleado"`).

### 5.2. Los 10 Roles de Inferencia Especializada (`prompt_service.py`)
`general`, `medicina`, `psicologia`, `orientacion`, `discapacidad`, `trabajo_social`, `referencias`, `jornadas`, `mobiliario`, `transporte`.

### 5.3. Concurrencia y Motor SQLAlchemy
* Engine singleton con `pool_pre_ping=True` y `pool_recycle=1800` en [`app/db/session.py`](app/db/session.py). Conexión optimizada para lecturas concurrentes sin transacciones de bloqueo.

---

## 6. Cheat Sheet de Helpers Core

* **Configuración y Seguridad:**
  - `obtener_ajustes() -> Ajustes`: Singleton cacheado con validación de entorno.
  - `validar_api_key(x_api_key: str) -> str`: Dependencia FastAPI para verificación `X-API-Key`.
* **Capa de Datos (`app/db/session.py`):**
  - `consultar(sql: str, params: dict | None = None) -> list[dict]`: Ejecuta SQL `text()` y devuelve lista de diccionarios.
  - `contar(sql: str, params: dict | None = None) -> int`: Devuelve conteo escalar entero.
  - `consultar_dataframe(sql: str, params: dict | None = None) -> pd.DataFrame`: Carga directa a Pandas.
  - `ping() -> bool`: Verifica conectividad con MySQL (`SELECT 1`).
* **Constructores de Consultas (`app/db/queries/_comunes.py`):**
  - `Consulta(base: str, orden: str, params: dict)`: Dataclass inmutable de consulta.
  - `agregar_fechas(cond, params, col, filtros)`: Agrega cláusulas `DATE(col) >= :f_desde` y `<= :f_hasta`.
  - `agregar_igual(cond, params, col, param, valor)`: Agrega igualdad si el valor no es nulo.
  - `agregar_empleado(cond, params, col, id_empleado)`: Inyecta filtro de visibilidad por empleado.
* **Servicios Analíticos y LLM (`app/services/`):**
  - `etl_service.procesar(modulo, filtros, id_empleado, limit) -> Resumen`: Pipeline ETL completo.
  - `prompt_service.construir_prompts(modulo, intencion, resumen, obs) -> tuple[str, str]`
  - `gemini_service.obtener_cliente() -> ClienteIA`: Retorna `ClienteGemini` o `ClienteSimulado`.

---

## 7. Matriz Resumen de Módulos

| Clave (`Modulo`) | Tablas Base Principales | Filtros Admitidos | Alertas ETL Críticas |
| :--- | :--- | :--- | :--- |
| `general` | 7 atenciones (`UNION ALL`), `beneficiario`, `pnf` | fechas, genero, pnf, area | Concentración de área $\ge 40\%$ |
| `medicina` | `consulta_medica`, `insumos`, `presentacion_insumo` | fechas, genero, pnf | Stock crítico $< 10$, insumos vencidos |
| `psicologia` | `consulta_psicologica`, `cita`, `estado_cita` | fechas, pnf, tipo_consulta, estado | Inasistencia a citas $> 25\%$ |
| `orientacion` | `orientacion`, `solicitud_de_servicio`, `pnf` | fechas, genero, pnf | Concentración de motivos de consulta |
| `discapacidad` | `discapacidad`, `beneficiario`, `pnf` | fechas, genero, pnf, tipo, grado | Casos graves sin asistencia, carnetización |
| `trabajo_social` | `becas`, `exoneracion`, `fames`, `gestion_emb` | fechas, pnf, submodulo | Gestantes $\ge 34$ semanas |
| `referencias` | `referencias`, `servicio` (origen y destino) | fechas, estado, servicio_destino | Referencias pendientes $> 15$ días |
| `jornadas` | `jornadas_medicas`, beneficiarios, diagnósticos | fechas, estado | Aforo efectivo $< 40\%$ |
| `mobiliario` | `mobiliario`, `equipos`, tipos | fechas, tipo_bien, estado | Proporción de bienes inactivos |
| `transporte` | `vehiculos`, `rutas`, `proveedores`, `repuestos` | fechas, seccion, tipo_vehiculo, estado | Repuestos $< 5$ unidades, flota inactiva |

*Para la especificación exhaustiva de cada pipeline, consultar [`docs/PIPELINES_IA.md`](docs/PIPELINES_IA.md).*

---

## 8. Anti-Patrones Prohibidos (Negative Constraints)

* ❌ **NUNCA ejecutar sentencias de escritura en BD (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`).** El servicio es estrictamente de solo lectura.
* ❌ **NUNCA enviar datos personales (PII) a Google Gemini.** Cédulas, nombres completos e historias clínicas deben permanecer en el servidor local.
* ❌ **NUNCA omitir la degradación elegante a `ClienteSimulado`.** Ante cualquier fallo de Gemini o de red, responder con el informe determinista local (`simulado_fallback`).
* ❌ **NUNCA omitir la cabecera `X-API-Key` ni debilitar su validación.** No usar comparaciones directas de cadenas (`==`); usar siempre `hmac.compare_digest`.
* ❌ **NUNCA hacer cruces directos a tablas de seguridad sin prefijo de esquema.** Usar siempre `{seguridad}.empleado`.
* ❌ **NUNCA omitir el límite de filas (`LIMIT :limit`) en las consultas de extracción.** Evita saturación de memoria en DataFrames masivos.
* ❌ **NUNCA alterar la estructura del JSON devuelto a DIRPOLES-4.** La respuesta debe ajustarse estrictamente a `ReporteResponseDTO`.

---

## 9. Plantillas Canónicas (Boilerplates de Oro)

### 9.1. Definición de Consulta SQL (`Consulta`)
```python
def modulo_queries(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    cond: list[str] = ["1 = 1"]
    params: Parametros = {}
    agregar_fechas(cond, params, "alias.fecha_creacion", filtros)
    agregar_igual(cond, params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_empleado(cond, params, "ss.id_empleado", id_empleado)
    base = (
        "SELECT alias.id, alias.fecha_creacion AS fecha, b.nombres "
        "FROM tabla_entidad alias "
        "JOIN solicitud_de_servicio ss ON alias.id_solicitud_serv = ss.id_solicitud_serv "
        "JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        + clausula_where(cond)
    )
    return {"entidades": Consulta(base=base, orden="alias.fecha_creacion DESC", params=params)}
```

### 9.2. Transformación ETL y Alertas en Pandas
```python
def _transformar_modulo(extraccion: Extraccion, filtros: FiltrosDTO, alertas: list) -> Resumen:
    df = extraccion.datos.get("entidades", pd.DataFrame())
    serie = _serie_mensual(df, "fecha")
    por_categoria = _distribucion(df, "categoria")
    if len(df[df["cantidad"] < 5]):
        alertas.append(_alerta("critico", "Existencias en nivel de reserva crítica (< 5)."))
    return {
        "totales": extraccion.totales,
        "distribuciones": {"por_categoria": por_categoria},
        "comparativa": _comparativa(serie),
        "serie_mensual": serie,
    }
```

---

## 10. Protocolo de Trabajo y Verificación

### 10.1. Flujo para Construir o Modificar Módulos
1. **Contrato:** Registrar enumeraciones en [`app/schemas/enums.py`](app/schemas/enums.py) y DTOs en [`app/schemas/request.py`](app/schemas/request.py).
2. **Consultas:** Implementar SQL parametrizado en [`app/db/queries/{modulo}_queries.py`](app/db/queries/).
3. **ETL:** Crear transformador vectorizado en [`app/services/etl_service.py`](app/services/etl_service.py).
4. **Prompt:** Definir rol técnico y contextual en [`app/services/prompt_service.py`](app/services/prompt_service.py).
5. **Verificación:** Añadir o actualizar pruebas unitarias en [`tests/`](tests/).

### 10.2. Comandos de Verificación de Calidad
```bash
# 1. Comprobación de tipos estáticos
mypy app

# 2. Análisis estático y estilo
ruff check app tests

# 3. Formateo de código
ruff format --check app tests

# 4. Pruebas unitarias en modo offline (sin requerir MySQL)
pytest -m "not bd"
```
