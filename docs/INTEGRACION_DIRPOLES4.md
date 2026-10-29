# Guía de Integración: DIRPOLES-4 (PHP) → DIRPOLES-IA (Microservicio)

> **Audiencia:** agente/desarrollador que implementará la llamada al microservicio
> de IA desde el monolito PHP. Este documento es el **contrato fuente de verdad**:
> todos los valores, rutas y códigos aquí están verificados contra el código
> implementado y probados en vivo contra el microservicio corriendo.
> El `context.md` (spec v3) describe la arquitectura general; para los DTOs usa
> este archivo.

---

## 1. Qué ya existe

| Componente | Estado |
| :--- | :--- |
| Microservicio DIRPOLES-IA | Implementado, probado y funcional (FastAPI + Pandas + Gemini) |
| URL local | `http://127.0.0.1:8000` (ver `MANUAL.md` del repo DIRPOLES-IA para encenderlo) |
| Los 10 reportes en PHP | Ya operativos en `app/Views/reportes/*.php` con filtros y Chart.js |
| Verificación de vida | `GET http://127.0.0.1:8000/api/v1/salud` → `{"estado":"ok",...}` (sin API key) |
| Interactiva | `http://localhost:8000/docs` (Swagger) para probar a mano |

**Seguridad B2B:** toda petición a los endpoints de reportes lleva la cabecera
`X-API-Key` con el valor de la variable `DIRPOLES_IA_API_KEY` (la misma que
tiene el microservicio en su `.env`; el monolito debe leerla de **su** `.env`,
nunca tenerla hardcodeada).

---

## 2. Arquitectura de la integración (2 reglas de oro)

```text
  [ Usuario en la vista reportes/{modulo} ]
        │  elige intención + observación (los filtros ya están en la vista)
        ▼
  [ Navegador: JS fetch() ]
        │  POST api/reportes/ia/informe   (solo JSON, SIN API key)
        ▼
  [ PHP: puerta JSON en reportesController ]
        │  verifica permiso 'reportes.leer' + RBAC
        │  inyecta id_empleado desde $_SESSION  (nunca desde el navegador)
        │  inyecta X-API-Key desde .env         (nunca expuesta al navegador)
        │  curl POST → http://127.0.0.1:8000/api/v1/reportes/generar  (timeout 60s)
        ▼
  [ DIRPOLES-IA ] → BD (READ-ONLY) → Pandas → Gemini → Markdown
        │
        ▼
  [ PHP responde {exito:true, datos:{informe_markdown, meta}} ] → JS renderiza Markdown
```

**Regla 1 — El navegador NUNCA habla con DIRPOLES-IA directamente.**
La `X-API-Key` y el `id_empleado` se inyectan **server-side** en PHP. Si el
navegador enviara `id_empleado`, PHP debe **sobrescribirlo** con la sesión
(jamás confiar en el valor del cliente).

**Regla 2 — DIRPOLES-IA NO consume los `GET api/reportes/*` del monolito.**
El microservicio se conecta **directamente a MySQL** con usuario
`dirpoles_ia_reader` (solo `SELECT`). La única comunicación PHP → IA es el
`POST /api/v1/reportes/generar`. (Esto corrige la nota histórica del
`AGENTS.md` de DIRPOLES-4 que asumía lo contrario.)

**Nota:** como el navegador solo llama a PHP, **no hay problemas de CORS**;
la variable `ALLOWED_ORIGINS` del microservicio es irrelevante para este flujo.

---

## 3. A nivel visual y de usuario (qué implementar)

En **cada** vista `app/Views/reportes/{modulo}.php`, junto a los filtros
existentes, una sección **"Informe inteligente con IA"**:

1. **Select de intención** (4 opciones — valores exactos en §6.3):
   * Resumen ejecutivo · Alertas y anomalías · Tendencias y patrones · Recomendaciones
2. **Textarea "Observación del usuario"** (opcional, máx. 1000 caracteres),
   placeholder sugerido: *"Instrucciones adicionales para la IA (opcional)…"*
3. **Botón "Generar informe con IA"**:
   * Al pulsarlo: spinner + botón deshabilitado + texto
     *"Generando informe… puede tardar hasta 30 segundos"*.
   * La generación real tarda **~12 s** (tiempo de respuesta de Gemini); usar
     timeout de **60 s** en el curl.
4. **Área de resultado**: render del Markdown + línea de meta
   (`N registros · X.Xs` + **badge** si `meta.modo_informe` ≠ `gemini`).
5. **Banner de error amigable** si falla (tabla en §8). La vista tradicional
   (gráficos/tabla) **siempre debe seguir funcionando** — principio de
   resiliencia: si la IA falla, el usuario ni siquiera se entera salvo por el banner.
6. **Comprobación opcional de disponibilidad** al cargar la vista:
   `GET /api/v1/salud` (sin key). Si `estado ≠ "ok"` o no responde,
   ocultar/deshabilitar la sección IA.

**Permisos (RBAC existente):**
* La puerta PHP debe llamar `Autorizacion::verificar('reportes', 'leer')`.
* `general` sigue siendo **solo administrador** (usar la validación existente
  `verificarAccesoReporte('…', true)` / `esAdmin()`).

---

## 4. RBAC y `id_empleado` (visibilidad de datos) — CRÍTICO

El microservicio no conoce sesiones. PHP debe enviar **server-side**:

| Sesión del usuario | `id_empleado` en el payload |
| :--- | :--- |
| Administrador / Superusuario (`esAdmin()` true) | `null` (ve **todos** los registros) |
| Cualquier otro empleado | `$_SESSION['id_empleado']` (ve **solo lo que registró él**) |

Esto replica exactamente el `filtroEmpleado()` de `ReportesModel.php`.

* **Aplica en 6 módulos:** `general`, `medicina`, `psicologia`, `orientacion`,
  `discapacidad`, `trabajo_social`.
* **Se ignora en 4 módulos** (igual que el monolito): `referencias`,
  `jornadas`, `mobiliario`, `transporte` — enviarlo o no da igual.

---

## 5. Los 3 endpoints

| Método | Ruta | Auth | Uso en PHP |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/reportes/generar` | `X-API-Key` | Genera el informe (el flujo principal) |
| `GET` | `/api/v1/reportes/catalogos` | `X-API-Key` | Catálogos/valores válidos (opcional: las vistas ya tienen sus selects) |
| `GET` | `/api/v1/salud` | sin key | Comprobar que el servicio está vivo |

---

## 6. `POST /api/v1/reportes/generar` — contrato exacto

### 6.1 Cuerpo de la petición

```json
{
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "filtros": {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-09-30",
    "genero": "F",
    "pnf": 3,
    "limit": 5000
  },
  "observacion_usuario": "Enfocarse en insumos con bajo stock para octubre.",
  "id_empleado": 17
}
```

| Campo | Tipo | Obligatorio | Descripción |
| :--- | :--- | :--- | :--- |
| `modulo` | enum (§6.2) | sí | Módulo de reporte |
| `intencion` | enum (§6.3) | sí | Enfoque del informe |
| `filtros` | objeto (§6.4) | no | Mismos filtros que ya usa la vista; los no aplicables al módulo se ignoran |
| `observacion_usuario` | string ≤ 1000 | no | Instrucción libre que se inyecta en el prompt de la IA |
| `id_empleado` | entero ≥ 1 | no | Visibilidad (§4); `null`/omitido = todo |

### 6.2 Valores de `modulo` (enum exacto)

```text
general · medicina · psicologia · orientacion · discapacidad
trabajo_social · referencias · jornadas · mobiliario · transporte
```

Mapeo desde las rutas de vistas (ojo al guion): `reportes/trabajo-social`
→ `"trabajo_social"`, `reportes/orientacion` → `"orientacion"`, etc.
Un valor fuera de enum → **422**.

### 6.3 Valores de `intencion` (enum exacto) y etiqueta sugerida en la UI

| Valor | Etiqueta en el select | Qué produce |
| :--- | :--- | :--- |
| `resumen_ejecutivo` | Resumen ejecutivo | Qué pasó en el periodo |
| `alertas_y_anomalias` | Alertas y anomalías | Qué está mal (stock, pendientes, aforo…) |
| `tendencias_y_patrones` | Tendencias y patrones | Evolución temporal y patrones |
| `recomendaciones` | Recomendaciones | Qué acción tomar |

### 6.4 Campos de `filtros` y qué módulo los usa

Todos opcionales. Formato de fecha `YYYY-MM-DD` (inclusivo a nivel día;
`fecha_inicio > fecha_fin` → **422**).

| Filtro | Tipo / valores exactos | Módulos que lo aplican |
| :--- | :--- | :--- |
| `fecha_inicio`, `fecha_fin` | fecha `YYYY-MM-DD` | los 10 |
| `genero` | `"M"` \| `"F"` | general, medicina, orientacion, discapacidad |
| `pnf` | entero ≥ 1 (ID del PNF) | general, medicina, psicologia, orientacion, discapacidad, trabajo_social |
| `area` | `Becas`, `Exoneración`, `FAMES`, `Medicina`, `Orientación`, `Discapacidad`, `Psicología` | general |
| `estado` | ver catálogos abajo (≤ 60 chars) | psicologia, referencias, jornadas, mobiliario, transporte |
| `tipo_consulta` | `Diagnóstico`, `Retiro temporal`, `Cambio de carrera` | psicologia |
| `submodulo` | `Becas`, `Exoneración`, `FAMES`, `Gestión Embarazo` | trabajo_social |
| `grado` | `Leve`, `Moderado`, `Grave` | discapacidad |
| `tipo_discapacidad` | `Física`, `Sensorial`, `Intelectual`, `Múltiple`, `Otro` | discapacidad |
| `tipo_bien` | `Mobiliario`, `Equipo` | mobiliario |
| `tipo_vehiculo` | `Autobús`, `Camioneta`, `Automóvil` | transporte |
| `seccion_transporte` | `Vehículos`, `Rutas`, `Proveedores`, `Repuestos`, `Asignaciones`, `Mantenimientos` | transporte |
| `servicio_destino` | entero ≥ 1 (ID de servicio) | referencias |
| `limit` | entero 1–20000 (defecto 5000) | los 10 |

**Catálogos de `estado` (validados — valor fuera de lista → 422):**

| Módulo | Valores permitidos |
| :--- | :--- |
| `psicologia` | `Pendiente`, `Confirmada`, `Atendida`, `Cancelada`, `No asistió` |
| `referencias` | `Pendiente`, `Aceptada`, `Rechazada` |
| `jornadas` | `Activa`, `Cancelada`, `Finalizada` |
| `mobiliario` | `Activo`, `Inactivo` |
| `transporte` | texto libre ≤ 60 (no validado por catálogo) |

> **UI:** muestra en cada vista **solo los filtros aplicables a su módulo**
> (la fila "Módulos que lo aplican" de la tabla). Los valores van **con
> acentos y tal cual** (`Exoneración`, `No asistió`); usar
> `JSON_UNESCAPED_UNICODE` al codificar.

### 6.5 Ejemplo completo de lo que debe enviar PHP (usuario no admin)

```json
{
  "modulo": "psicologia",
  "intencion": "resumen_ejecutivo",
  "filtros": { "fecha_inicio": "2026-01-01", "fecha_fin": "2026-12-31", "pnf": 3 },
  "observacion_usuario": null,
  "id_empleado": 17
}
```

---

## 7. Respuesta exitosa (200)

```json
{
  "exito": true,
  "modulo": "medicina",
  "intencion": "alertas_y_anomalias",
  "informe_markdown": "# INFORME DE ALERTAS Y ANOMALÍAS...\n\n### 1. Resumen Ejecutivo\n...",
  "meta": {
    "registros_procesados": 450,
    "tiempo_procesamiento_seg": 12.03,
    "modo_informe": "gemini"
  }
}
```

| Campo | Uso en la UI |
| :--- | :--- |
| `informe_markdown` | Renderizar como Markdown (§10) |
| `meta.registros_procesados` | Mostrar: *"450 registros analizados"* |
| `meta.tiempo_procesamiento_seg` | Mostrar junto a los registros |
| `meta.modo_informe` | `gemini` = informe real de la IA. `simulado` / `simulado_fallback` = generador local de respaldo → mostrar **badge** *"modo simulado"* para no atribuir a la IA un texto genérico |

---

## 8. Manejo de errores (tabla completa)

| Código | Causa | `detail` | Acción en UI |
| :--- | :--- | :--- | :--- |
| `401` | Falta o falla `X-API-Key` | string: `"Cabecera X-API-Key ausente o inválida."` | Banner *"Servicio de IA no configurado"* (error de config, solo admins) |
| `422` | Payload inválido (módulo/intención desconocidos, fechas invertidas, `estado` fuera de catálogo…) | array FastAPI: `[{"loc":[...],"msg":"..."}]` | Mostrar el `msg` del primer elemento (van en español) |
| `503` | MySQL caído o error de consulta | `{"exito":false,"detalle":"No fue posible extraer los datos de la base de datos.","error":"..."}` | Banner *"Datos no disponibles temporalmente"* |
| timeout / sin conexión | Microservicio apagado | (curl falla) | Banner *"Servicio de IA apagado"* + ocultar sección |

**Regla:** cualquier error **nunca** debe romper la vista tradicional de
reportes; el usuario sigue viendo gráficos y tablas normalmente.

---

## 9. Implementación PHP (patrón recomendado)

Convenciones del proyecto (ver `AGENTS.md` de DIRPOLES-4): funciones públicas,
cero clases en controladores, **regla de las dos puertas** (este endpoint va en
la puerta JSON `api/*`), `Respuesta::exito()`, `ExcepcionApi`, curl nativo
(**no** hay Guzzle en composer).

### 9.1 `.env` del monolito (ya existe `vlucas/phpdotenv`)

```env
# --- Microservicio de IA (DIRPOLES-IA) ---
DIRPOLES_IA_URL=http://127.0.0.1:8000
DIRPOLES_IA_API_KEY=7ddfa2b3de679f470ac9a193aa3405d2
```

> La clave es la misma que está en `DIRPOLES-IA/.env → DIRPOLES_IA_API_KEY`.
> Mantenerla solo en `.env` (que ya está en `.gitignore`).

### 9.2 Función de llamada (en `reportesController.php`)

```php
/**
 * Llama al microservicio DIRPOLES-IA y devuelve ['informe_markdown' => ..., 'meta' => ...].
 * La X-API-Key y el id_empleado se inyectan AQUÍ (server-side): el navegador
 * nunca ve la clave ni decide la visibilidad de datos.
 */
function reportesIaGenerar(string $modulo, string $intencion, array $filtros, ?string $observacion): array
{
    $url = rtrim(getenv('DIRPOLES_IA_URL') ?: 'http://127.0.0.1:8000', '/');
    $clave = getenv('DIRPOLES_IA_API_KEY') ?: '';
    if ($clave === '') {
        throw App\Core\ExcepcionApi::errorInterno('Servicio de IA no configurado (falta DIRPOLES_IA_API_KEY).');
    }

    // Visibilidad: admin ve todo; el resto solo SUS registros (espejo de filtroEmpleado).
    $esAdmin = isset($_SESSION['tipo_empleado']) &&
        (stripos($_SESSION['tipo_empleado'], 'administrador') !== false ||
         stripos($_SESSION['tipo_empleado'], 'superusuario') !== false);

    $payload = [
        'modulo' => $modulo,
        'intencion' => $intencion,
        'filtros' => $filtros,
        'observacion_usuario' => $observacion ?: null,
        'id_empleado' => $esAdmin ? null : (int) ($_SESSION['id_empleado'] ?? 0),
    ];

    $ch = curl_init($url . '/api/v1/reportes/generar');
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_CONNECTTIMEOUT => 5,
        CURLOPT_TIMEOUT => 60,
        CURLOPT_HTTPHEADER => [
            'Content-Type: application/json',
            'X-API-Key: ' . $clave,
        ],
        CURLOPT_POSTFIELDS => json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES),
    ]);
    $cuerpo = curl_exec($ch);
    $codigo = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $fallo = curl_error($ch);
    curl_close($ch);

    if ($cuerpo === false) {
        throw App\Core\ExcepcionApi::errorInterno('Servicio de IA no disponible: ' . $fallo);
    }
    $datos = json_decode($cuerpo, true);
    if ($codigo === 200 && ($datos['exito'] ?? false) === true) {
        return [
            'informe_markdown' => $datos['informe_markdown'],
            'meta' => $datos['meta'],
        ];
    }

    // Mapear los códigos del microservicio a mensajes del monolito (§8).
    $detalle = $datos['detail'] ?? null;
    if ($codigo === 401) {
        throw App\Core\ExcepcionApi::errorInterno('Servicio de IA no configurado.');
    }
    if ($codigo === 422 && is_array($detalle)) {
        $msg = $detalle[0]['msg'] ?? 'Datos inválidos para el informe.';
        throw App\Core\ExcepcionApi::validacion('El informe no pudo generarse: ' . $msg);
    }
    throw App\Core\ExcepcionApi::errorInterno('El servicio de IA respondió un error (' . $codigo . ').');
}
```

### 9.3 Ruta JSON (en `app/routes/reportes.php`)

```php
// Puerta JSON: informe de IA para el módulo de reportes (integración DIRPOLES-IA)
Router::post('api/reportes/ia/informe', function () {
    load_controller('reportesController.php');
    apiReportesIaInforme();
});
```

### 9.4 Endpoint (puerta JSON)

```php
/**
 * POST api/reportes/ia/informe
 * Body del navegador: { modulo, intencion, filtros, observacion_usuario }
 * (id_empleado e X-API-Key NO vienen del navegador: los agrega reportesIaGenerar).
 */
function apiReportesIaInforme(): void
{
    Autorizacion::verificar('reportes', 'leer');

    $entrada = json_decode(file_get_contents('php://input'), true);
    if (!is_array($entrada)) {
        throw App\Core\ExcepcionApi::jsonInvalido();
    }

    $modulo = (string) ($entrada['modulo'] ?? '');
    // 'general' es solo administrador (misma regla que la vista tradicional).
    if ($modulo === 'general') {
        verificarAccesoReporte('', true);
    }

    $resultado = reportesIaGenerar(
        $modulo,
        (string) ($entrada['intencion'] ?? ''),
        is_array($entrada['filtros'] ?? null) ? $entrada['filtros'] : [],
        isset($entrada['observacion_usuario']) ? (string) $entrada['observacion_usuario'] : null
    );

    // Auditoría: misma acción 'Lectura' que los endpoints de reportes.
    Bitacora::registrar('Reportes', 'Lectura', 'Generó informe de IA: ' . $modulo);

    App\Core\Respuesta::exito($resultado);
}
```

### 9.5 Llamada desde el JS de la vista

```js
async function generarInformeIA() {
    const boton = document.getElementById('btn-informe-ia');
    const zona = document.getElementById('zona-informe-ia');
    boton.disabled = true;
    zona.innerHTML = '<div class="text-muted">Generando informe… puede tardar hasta 30 segundos.</div>';

    try {
        const resp = await fetch('api/reportes/ia/informe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                modulo: 'medicina',            // el de ESTA vista
                intencion: document.getElementById('ia-intencion').value,
                filtros: { /* los MISMOS valores del formulario de filtros */ },
                observacion_usuario: document.getElementById('ia-observacion').value || null
            })
        });
        const json = await resp.json();
        if (!json.exito) {
            throw new Error(json.error?.mensaje || 'No se pudo generar el informe.');
        }
        renderizarInformeIA(json.datos);   // §10
    } catch (e) {
        zona.innerHTML = '<div class="alert alert-warning">' +
            'El servicio de IA no está disponible. Los reportes tradicionales funcionan con normalidad.' +
            '</div>';
    } finally {
        boton.disabled = false;
    }
}
```

---

## 10. Renderizado del Markdown

El proyecto **no tiene librería de Markdown en composer** y la regla del repo
es *no agregar dependencias sin justificar*; además Chart.js se usa **local**
(`dist/js/…`, sin CDN). Recomendación: **`marked` + `dompurify` locales**.

1. Descargar `marked.min.js` (marked v12+) y `purify.min.js` (DOMPurify) y
   colocarlos en `dist/js/lib/` (o `plugins/`).
2. En la vista:

```html
<div id="zona-informe-ia" class="mt-3"></div>
```

```js
function renderizarInformeIA(datos) {
    const html = DOMPurify.sanitize(marked.parse(datos.informe_markdown));
    const badge = datos.meta.modo_informe === 'gemini'
        ? '' : '<span class="badge bg-secondary">modo simulado</span>';
    document.getElementById('zona-informe-ia').innerHTML =
        '<div class="card"><div class="card-body">' + html +
        '<hr><small class="text-muted">' + datos.meta.registros_procesados +
        ' registros · ' + datos.meta.tiempo_procesamiento_seg + 's ' + badge + '</small>' +
        '</div></div>';
}
```

> **Seguridad:** siempre pasar por `DOMPurify.sanitize()` antes de insertar
> con `innerHTML`. Alternativa sin JS: `composer require league/commonmark`
> (justificar ante la regla de dependencias del repo).

---

## 11. Checklist de implementación

- [ ] `.env` con `DIRPOLES_IA_URL` y `DIRPOLES_IA_API_KEY` (leídos con `getenv`).
- [ ] Función `reportesIaGenerar()` en `reportesController.php` (curl, timeout 60 s).
- [ ] Endpoint puerta JSON `POST api/reportes/ia/informe` con `Autorizacion::verificar('reportes','leer')`.
- [ ] Regla `general` = solo admin (reutilizar `verificarAccesoReporte`).
- [ ] `id_empleado` inyectado server-side desde sesión (`null` si admin).
- [ ] En las 10 vistas: sección IA (select intención, textarea observación, botón, zona de resultado).
- [ ] Solo mostrar los filtros aplicables al módulo (tabla §6.4) y reutilizar sus valores.
- [ ] Spinner + botón deshabilitado durante la petición.
- [ ] Manejo de 401/422/503/timeout con banner (nunca romper la vista).
- [ ] Badge *"modo simulado"* cuando `meta.modo_informe ≠ gemini`.
- [ ] Render Markdown con `marked` local + `DOMPurify.sanitize`.
- [ ] Bitácora acción `'Lectura'` en el endpoint.
- [ ] Verificación manual (§12).

---

## 12. Comandos de verificación manual (ejecutarlos tú, no el agente)

```bash
# 1. Microservicio encendido (ver MANUAL.md de DIRPOLES-IA)
cd /home/roberth/Proyectos/DIRPOLES-IA
source .venv/bin/activate
nohup uvicorn app.main:app --host 127.0.0.1 --port 8000 > logs/uvicorn.log 2>&1 &
echo $! > logs/uvicorn.pid
sleep 3

# 2. Vida
curl http://127.0.0.1:8000/api/v1/salud

# 3. Petición real (debe tardar ~12 s y dar "modo_informe":"gemini")
curl -s -X POST http://127.0.0.1:8000/api/v1/reportes/generar \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: <DIRPOLES_IA_API_KEY>' \
  -d '{"modulo":"medicina","intencion":"alertas_y_anomalias","filtros":{"fecha_inicio":"2026-01-01","fecha_fin":"2026-12-31"}}'

# 4. Sin la clave (debe dar 401)
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/reportes/generar \
  -H 'Content-Type: application/json' -d '{}'

# 5. En el navegador: la vista de reportes con la nueva sección IA
```

---

## Apéndice A — Respuesta de `GET /api/v1/salud` (sin key)

```json
{"estado":"ok","servicio":"DIRPOLES-IA","base_datos":"ok","modo_llm":"gemini"}
```

* `base_datos`: `"ok"` \| `"no_disponible"` (MySQL caído → el `POST /generar` dará 503).
* `modo_llm`: `"gemini"` (IA real) \| `"simulado"` (sin key / `MOCK_LLM=True`).

## Apéndice B — Catálogos de `GET /api/v1/reportes/catalogos` (con key)

Devuelve listas de strings para poblar/validar selects:
`modulos`, `intenciones`, `areas`, `submodulos_trabajo_social`, `tipos_consulta`,
`tipos_discapacidad`, `grados_discapacidad`, `estados_cita`, `estados_referencia`,
`estados_jornada`, `estados_inventario`, `tipos_bien`, `tipos_vehiculo`,
`secciones_transporte`. **Opcional**: las vistas de reportes ya cargan sus
catálogos desde PHP; úsalo solo si quieres validar contra el microservicio.

## Apéndice C — Errores típicos de implementación

| Error | Causa probable |
| :--- | :--- |
| `422` desde el primer intento | Enviando `carrera_id`/`area_id` (nombres viejos del `context.md` v3) — usar los de §6.4 |
| La IA ve todos los registros de un no-admin | Falta inyectar `id_empleado` server-side (§4) |
| `401` con clave "correcta" | Cabecera mal escrita: es exactamente `X-API-Key` |
| El navegador falla con CORS | Está llamando directo a `:8000` — debe pasar por PHP (§2) |
| Respuesta lenta percibida | Normal: ~12 s reales; usar spinner y timeout 60 s |
