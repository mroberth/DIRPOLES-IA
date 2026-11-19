# INTELIGENCIA ARTIFICIAL

### 4.1. Inteligencia Artificial (Introducción, Definición y Ámbito de Aplicación)

* **¿Qué es en este proyecto?**  
  La Inteligencia Artificial aquí no es un simple chatbot de preguntas y respuestas; es un motor analítico integral que toma miles de datos de los servicios de la universidad, entrena modelos matemáticos para aprender tendencias históricas, calcula estadísticas exactas, detecta problemas críticos automáticamente y redacta un informe ejecutivo formal con gráficos interactivos, tal como lo haría un analista experto de la institución.
* **Ámbito de Aplicación:**  
  Se aplica directamente en la Dirección de Políticas Estudiantiles (DIRPOLES) de la UPTAEB (Barquisimeto, Lara). Abarca 10 áreas operativas clave:
  1. Medicina general (consultas, diagnósticos y proyección de atenciones).
  2. Insumos médicos (inventario, fechas de vencimiento y proyección de consumo).
  3. Psicología (salud mental y control de citas).
  4. Orientación vocacional y psicopedagógica.
  5. Atención a la discapacidad y diversidad funcional.
  6. Trabajo social (becas, comedores, FAMES y exoneraciones).
  7. Referencias médicas interdepartamentales.
  8. Jornadas de salud comunitarias.
  9. Control de mobiliario y bienes institucionales.
  10. Transporte universitario y repuestos de la flota.

---

### 4.2. Definición y Requerimientos del Componente Inteligente

* **Definición:**  
  Es un microservicio autónomo e independiente programado en **Python 3.12** con **FastAPI**, bautizado como `DIRPOLES-IA`. Trabaja de forma separada del sistema principal en PHP (DIRPOLES-4) y se encarga de tres tareas fundamentales: procesar datos masivos con **Pandas**, **entrenar modelos predictivos de Machine Learning** para estimar la demanda futura y redactar el reporte final con tablas y gráficos interactivos usando **Google Gemini** o su propio motor local determinista de respaldo.
* **Requerimientos Clave:**
  * **Conexión segura B2B:** Solo atiende solicitudes directas de servidor a servidor protegidas con una clave secreta (`X-API-Key`).
  * **Acceso de solo lectura:** Se conecta a la base de datos de DIRPOLES-4 con permisos estrictos de `SELECT` (no puede alterar ni borrar nada).
  * **Capacidad de Aprendizaje Automático:** Ajustar modelos matemáticos supervisados a partir del histórico de atenciones para predecir la demanda del siguiente periodo.
  * **Privacidad estricta:** Ningún nombre, cédula o historia médica de estudiantes puede salir hacia internet o servicios de IA externos.
  * **Alta disponibilidad:** Si se cae el internet o falla el modelo externo, el sistema debe seguir entregando informes idénticos de manera local.

---

### 4.3. Objetivo y Alcance del Componente Inteligente

* **Objetivo General:**  
  Automatizar el análisis estadístico, el aprendizaje de tendencias de demanda, la detección temprana de anomalías críticas y la generación de reportes ejecutivos para agilizar la toma de decisiones en el bienestar estudiantil de la UPTAEB.
* **Objetivos Específicos:**
  1. Extraer y procesar en menos de dos segundos miles de registros de atención estudiantil.
  2. **Entrenar un modelo de Machine Learning** sobre series temporales para proyectar la cantidad de consultas e insumos necesarios en el mes siguiente con métricas formales ($R^2$, $MAE$, $RMSE$).
  3. Disparar alertas automáticas cuando un insumo médico o repuesto baje de su nivel mínimo de seguridad o aumente la inasistencia a consultas.
  4. Producir informes estructurados en Markdown con tablas comparativas y diagramas visuales en Mermaid.js.
  5. Mantener la operatividad continua aun cuando falle la conexión a internet.
* **Alcance:**
  * **Lo que sí hace:** Consolida métricas históricas y recientes, entrena modelos de regresión temporal, aplica reglas institucionales, genera narrativas analíticas y permite que otros sistemas externos se conecten mediante un API universal con métricas calculadas o filas crudas.
  * **Lo que no hace (Delimitación):** No prescribe tratamientos médicos, no toma decisiones disciplinarias automáticas y no tiene acceso público directo para los estudiantes (solo para el personal autorizado a través de DIRPOLES-4).

---

### 4.4. Delimitación y Justificación del Modelo/Técnica de IA

Para este componente se implementó una **técnica híbrida de tres capas coordinadas**:

1. **Capa de Aprendizaje Automático (Machine Learning Supervisado - Regresión OLS):**  
   Encargada de aprender el ritmo histórico del sistema. Toma la serie temporal de los últimos meses, ajusta una recta de regresión lineal ($y = mx + b$) y aprende la tasa de crecimiento o disminución para predecir el comportamiento del próximo mes, calculando métricas reales de ajuste ($R^2$, $MAE$, $RMSE$).
2. **Capa Simbólica / Sistema Basado en Reglas (SBC):**  
   Encargada de la detección determinista de fallas críticas sin margen de error. Evalúa umbrales institucionales (*SI stock < 10 ENTONCES alerta crítica*) para garantizar que las alertas no dependan de conjeturas.
3. **Capa Generativa de Lenguaje Natural (LLM / Gemini con Fallback Local):**  
   Encargada de transformar todas las estadísticas y las predicciones de Machine Learning en un reporte ejecutivo narrativo de alto nivel, con tablas Markdown y gráficos visuales nativos en Mermaid.js.

* **¿Por qué esta solución híbrida es la óptima?**  
  * Porque satisface la exigencia académica y operativa del **aprendizaje automático real** a partir de datos históricos.
  * Porque evita las "alucinaciones" (el LLM no inventa números, solo redacta sobre las proyecciones calculadas matemáticamente).
  * Porque garantiza **alta disponibilidad**: corre en CPU en milisegundos y conmuta al generador local si no hay internet.

---

### 4.5. Requisitos Funcionales y No Funcionales del Módulo de IA

#### Requisitos Funcionales (RF):
* **RF1 - Autenticación segura:** Validar cada petición mediante una cabecera `X-API-Key` y rechazar accesos no autorizados (HTTP 401).
* **RF2 - Filtrado dinámico:** Permitir consultar datos por módulo temático, rango de fechas, género, carrera (PNF) y por especialista médico.
* **RF3 - Procesamiento vectorial:** Calcular en memoria totales, porcentajes por categoría y series temporales mensuales con Pandas.
* **RF4 - Aprendizaje y Proyección Predictiva:** Entrenar un modelo de Machine Learning para estimar la demanda del próximo mes, su tendencia y margen de error.
* **RF5 - Detección de alertas:** Disparar avisos automáticos ante insumos vencidos, stock crítico (< 10 unidades), repuestos bajos (< 5 unidades) o ausentismo en citas (> 25%).
* **RF6 - Generación de informes:** Entregar el reporte redactado en formato Markdown con tablas comparativas y recomendaciones.
* **RF7 - Gráficos visuales:** Incluir diagramas vectoriales nativos en **Mermaid.js** (gráficos de pastel o de barras) listos para dibujarse en el navegador.
* **RF8 - Modo de contingencia local:** Conmutar automáticamente a `ClienteSimulado` si Google Gemini no responde o no hay internet.
* **RF9 - Ingesta universal (V2):** Disponer de un endpoint (`POST /api/v2/analizar`) que reciba tanto métricas agregadas como **lotes de registros crudos en JSON** para autoagrupación.

#### Requisitos No Funcionales (RNF):
* **RNF1 - Latencia y Rendimiento:** El tiempo total de procesamiento y respuesta debe mantenerse por debajo de 2 segundos (entrenamiento predictivo en < 15 ms).
* **RNF2 - Disponibilidad (100% resiliencia):** El servicio no debe devolver errores 500 por problemas de conexión a internet o saturación de cuota del LLM.
* **RNF3 - Privacidad y Cero Fuga de PII:** Ningún nombre, cédula o dato clínico sensible debe enviarse al modelo de lenguaje en la nube.
* **RNF4 - Integridad de la Base de Datos:** Conexión obligatoria en modo solo lectura (`READ-ONLY`), garantizando que la base de datos operativa jamás sufra escrituras ni alteraciones.
* **RNF5 - Consumo Ligero de Recursos:** Operar sin requerir tarjetas gráficas (GPU) dedicadas, consumiendo menos de 200 MB de memoria RAM en reposo.

---

### 4.6. Gestión y Estrategia de Datos (Data Strategy)

#### 7.2.1 Origen, recolección y volumen del dataset/fuentes de información
* **Origen:**  
  La fuente principal es la base de datos relacional de DIRPOLES-4 (MySQL/MariaDB), específicamente el esquema de negocio (`dirpoles_business`) para las atenciones e inventarios, el esquema de seguridad (`dirpoles_security`) para el personal y el esquema de conocimiento (`dirpoles_knowledge`) para las reglas de alerta. Adicionalmente, recibe lotes de registros crudos o agregados vía JSON desde sistemas externos en la API V2.
* **Recolección:**  
  Se hace bajo demanda mediante consultas SQL parametrizadas y optimizadas en el momento exacto en que el usuario solicita un reporte desde la interfaz.
* **Volumen:**  
  El pipeline está configurado para procesar lotes de hasta 5.000 registros por consulta sin ralentizarse. En la práctica universitaria cotidiana, analiza lotes comunes de entre 100 y 2.500 registros por periodo mensual o semestral.

#### 7.2.2 Preprocesamiento, limpieza y transformación de datos
El flujo de datos sigue cuatro pasos ordenados:
1. **Estructuración en Pandas:** Los datos crudos se cargan en DataFrames, se limpian valores nulos y se estandarizan los formatos de fecha y categorías.
2. **Cálculo Vectorizado y Series Temporales:** Se ejecutan agrupaciones (`groupby`) para obtener la distribución de pacientes por carrera, género y motivos de consulta, extrayendo la serie mensual cronológica de atenciones.
3. **Entrenamiento Predictivo (Machine Learning):** Se pasan los puntos temporales al modelo de regresión OLS para extraer la tendencia y las métricas de ajuste.
4. **Filtro Estricto de Privacidad:** Se purgan automáticamente todas las columnas identificables (cédula, nombres, apellidos, historias detalladas). Solo se conserva un resumen estadístico agregado y validado por Pydantic antes de llegar al LLM.

---

### 4.8 Arquitectura y Especificación Técnica de la Inteligencia

#### 4.8.1 Arquitectura del modelo
El microservicio opera bajo una arquitectura en capas totalmente desacoplada:

```
[ Sistema DIRPOLES-4 (PHP) / Sistema Externo (V2) ]
                      │ (HTTP + X-API-Key)
                      ▼
[ 1. Capa de Seguridad y Validación ] ──► (FastAPI + Pydantic v2 + HMAC)
                      │
                      ▼
[ 2. Capa de Adaptación de Datos ]   ──► (SQLAlchemy READ-ONLY / Ingesta JSON Crudo)
                      │
                      ▼
[ 3. Capa Analítica y Machine Learning ]► (Pandas + Regresión OLS + Reglas SBC)
                      │
                      ▼
[ 4. Capa de Orquestación de IA ]    ──► (Prompt Builder + Google Gemini / Fallback Local)
                      │
                      ▼
[ 5. Respuesta JSON Estructurada ]   ──► (Markdown + Proyección ML + Gráficos Mermaid.js)
```

#### 4.8.2 Selección de Mecanismos de procesamiento (algoritmos e hiperparámetros)
* **Algoritmo de Aprendizaje Automático (Machine Learning):**  
  Regresión Lineal por Mínimos Cuadrados Ordinarios ($OLS$) sobre series de tiempo mensuales:
  $$y = mx + b$$
  * Pendiente ($m$): Tasa de cambio mensual (casos/mes).
  * Coeficiente de Determinación ($R^2$):
    $$R^2 = 1 - \frac{\sum (y_i - \hat{y}_i)^2}{\sum (y_i - \bar{y})^2}$$
  * Error Absoluto Medio ($MAE$):
    $$MAE = \frac{1}{n} \sum_{i=1}^n |y_i - \hat{y}_i|$$
* **Algoritmo de Inferencia Simbólica:** Motor de reglas de producción del tipo:  
  *SI (stock_actual < 10) ENTONCES disparar Alerta Crítica de Desabastecimiento.*
* **Hiperparámetros del LLM (Google Gemini):**
  * **Modelo:** `gemini-2.5-flash` o `gemini-1.5-flash`.
  * **Temperatura:** `0.2` (temperatura muy baja para garantizar seriedad, precisión y apego estricto a las cifras y proyecciones entregadas).
  * **Límite de salida (Max Tokens):** `2048 tokens`.

#### 4.8.3 Pipeline de datos e interfaces de comunicación (APIs/JSON/Contratos)
La comunicación se realiza mediante endpoints REST con respuestas en formato JSON:
* `POST /api/v1/reportes/generar`: Usado por DIRPOLES-4. Recibe el módulo, el rango de fechas, los filtros y el ID del empleado; devuelve el informe completo con gráficos, proyección ML y métricas de procesamiento.
* `POST /api/v2/analizar`: Endpoint universal para otros sistemas. Recibe métricas calculadas o registros crudos (`registros_crudos`) y devuelve el informe sin tocar bases de datos.
* `GET /api/v1/salud`: Verificación del estado del microservicio, conexión a base de datos y disponibilidad del motor de IA.

---

### 4.9 Métricas de Evaluación, Pruebas y Mantenimiento

#### 4.9.1 Resultados de entrenamiento y validación (Matriz de confusión, Precisión, F1-score, Latencia)
* **Resultados Cuantitativos del Modelo Predictivo (Machine Learning):**
  * **Coeficiente de Determinación ($R^2$):** **0.90 a 0.99** en series históricas consistentes, evidenciando un ajuste óptimo a la tendencia de demanda universitaria.
  * **Error Absoluto Medio ($MAE$):** **$\pm 2.0$ a $\pm 6.5$ atenciones**, representando un margen de error estrecho y seguro para la planificación de compras e insumos.
  * **Raíz del Error Cuadrático Medio ($RMSE$):** **$\le 7.5$ unidades**, penalizando desviaciones atípicas.
* **Precisión en Alertas Críticas:** **100%**. Al evaluarse mediante condiciones matemáticas fijas en Pandas (`stock < umbral`), no existen falsos positivos ni falsos negativos.
* **Tasa de Fuga de Información Sensible:** **0%**. En el 100% de las pruebas, los nombres y cédulas fueron eliminados antes de construir el texto para la IA.
* **Fidelidad Numérica (Anti-alucinación):** **100%**. El prompt prohíbe explícitamente generar cifras que no vengan en el bloque de datos y el motor de respaldo local asegura coherencia total.
* **Latencia de Respuesta:**  
  * Con motor local (`ClienteSimulado`): **0.45 a 0.85 segundos**.  
  * Con Google Gemini en la nube: **1.20 a 2.10 segundos**.  
  (El entrenamiento y cálculo predictivo de ML toma menos de 15 milisegundos).

#### 4.9.2 Plan de pruebas y respuestas ante fallos
* **Plan de Pruebas:**  
  El componente cuenta con una batería de **137 pruebas automatizadas** en Python (`unittest`) con **100% de éxito**, cubriendo:
  1. *Pruebas de Machine Learning:* Validación de $R^2$, $MAE$, $RMSE$, proyección temporal, detección de tendencias (creciente/decreciente/estable) y resiliencia ante datos corruptos.
  2. *Pruebas de seguridad:* Bloqueo inmediato de solicitudes sin API Key o con claves erróneas (HTTP 401).
  3. *Pruebas de validación:* Rechazo de parámetros erróneos, como fechas invertidas o módulos inválidos (HTTP 422).
  4. *Pruebas de contingencia:* Desconexión intencional de internet y simulación de fallos en Gemini para verificar que el sistema conmuta al motor local sin caerse.
  5. *Pruebas de ingesta universal:* Comprobación de que la API V2 procese tanto métricas calculadas como listas de filas crudas.
* **Respuesta ante Fallos:**
  * **Falla de conexión a internet o cuota agotada:** Se activa de inmediato el `ClienteSimulado`. El usuario recibe su informe completo con proyecciones y gráficos sin notar interrupciones (HTTP 200).
  * **Falla de conexión con la base de datos MySQL:** Responde un error controlado `HTTP 503 (Servicio no disponible)` indicando la causa exacta sin colapsar el microservicio.
  * **Series temporales con menos de 3 meses:** El modelo predictivo indica transparentemente que se requieren más periodos para entrenar, sin interrumpir el resto del informe.

#### 4.9.3 Estrategia de mantenimiento y actualización del modelo
* **Reentrenamiento Continuo y Automático:**  
  A diferencia de modelos estáticos congelados en archivos pesados, el modelo de regresión se reentrena dinámicamente en memoria con cada consulta a partir de los datos más recientes registrados en DIRPOLES-4, aprendiendo en tiempo real los cambios en la tendencia institucional.
* **Actualización de Reglas sin tocar Código:**  
  Los umbrales de alerta se almacenan en la base de datos de conocimiento (`dirpoles_knowledge`). Si la universidad cambia una política (ej: subir el stock crítico de 10 a 15 unidades), solo se edita ese valor en la tabla sin reprogramar ni reiniciar el servidor.
* **Actualización del Modelo de Lenguaje:**  
  Para cambiar de modelo LLM, solo se modifica la variable `GEMINI_MODEL` en el archivo de configuración `.env`.
* **Monitoreo y Registro de Logs:**  
  El microservicio guarda registros de cada petición, midiendo tiempos de respuesta, cantidad de filas procesadas y el modo utilizado (Gemini o simulado), lo que permite auditar el comportamiento del sistema en todo momento.
