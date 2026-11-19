# UNIVERSIDAD POLITÉCNICA TERRITORIAL ANDRÉS ELOY BLANCO (UPTAEB)
## PROYECTO SOCIO-TECNOLÓGICO IV (PST IV) — INGENIERÍA EN INFORMÁTICA
### COMPONENTE DE INTELIGENCIA ARTIFICIAL: FASE II (SEGUNDO AVANCE)

> **Proyecto:** DIRPOLES-4 (Dirección de Políticas Estudiantiles) y Ecosistema de Microservicios  
> **Nombre del Componente Inteligente:** Microservicio Analítico y Generador de Informes (`DIRPOLES-IA`)  
> **Equipo de Trabajo:** Estudiantes de PST IV — Trayecto IV  
> **Fecha de Entrega:** Octubre de 2026  

---

## INTRODUCCIÓN SENCILLA: ¿QUÉ ES ESTE COMPONENTE Y QUÉ HACE?

Para entender este proyecto sin complicaciones: **DIRPOLES-IA es un microservicio que funciona como el "cerebro analítico" para la Dirección de Políticas Estudiantiles de la UPTAEB**. 

En lugar de que un médico, psicólogo o directivo tenga que abrir un Excel y pasar 4 horas contando cuántos estudiantes vinieron, qué carreras se atendieron más o si se van a acabar las pastillas, nuestro componente se encarga de:
1. **Leer y ordenar los datos rápido** usando la librería **Pandas** de Python.
2. **Evaluar reglas institucionales** guardadas en una base de datos propia (**MariaDB**) para detectar problemas solos (por ejemplo: si quedan menos de 10 unidades de un medicamento, salta una alerta automática).
3. **Redactar un informe ejecutivo claro con gráficos** usando Inteligencia Artificial (**Google Gemini**), y si no hay internet, usar un motor de respaldo propio para que el sistema nunca deje de funcionar.

Además, lo diseñamos de forma **desacoplada e independiente**. Esto significa que no está "amarrado" con código duro al sistema DIRPOLES-4 (PHP). Si mañana en la universidad hacen una aplicación móvil en Flutter o un sistema en Go o Node.js, pueden mandarle los datos a este microservicio y él les responderá el análisis sin problemas.

A continuación, respondemos punto por punto las pautas solicitadas para esta Fase II de manera clara, paso a paso y fácil de defender.

---

## 1. DISEÑO DETALLADO DEL ALGORITMO O MODELO INTELIGENTE

### 1.1. Especificación Lógica y Matemática de la Técnica de IA

Para resolver este problema no usamos una sola técnica, sino una **Inteligencia Artificial Híbrida** que une lo mejor de dos mundos:

1. **Un Sistema Basado en Conocimiento (SBC / Sistema Experto Simbólico):**
   * **¿Qué hace?** Toma las decisiones numéricas y detecta anomalías mediante **reglas de producción** (del tipo *SI pasa esto, ENTONCES haz esto*).
   * **¿Por qué lo usamos?** Porque en un servicio de salud estudiantil no podemos permitir que una IA "invente" o "alucine". Las alertas sobre falta de medicinas o inasistencias a psicología tienen que basarse en números reales y exactos comprobados con la base de datos.
2. **Un Modelo Generativo de Lenguaje (LLM - Google Gemini) con Respaldo Local:**
   * **¿Qué hace?** Lee los números y las alertas calculadas por el sistema experto y los redacta en un lenguaje formal, ejecutivo y con recomendaciones profesionales.
   * **¿Por qué tiene respaldo?** Si la conexión a internet en la universidad se cae o Gemini no responde, entra en acción nuestro **ClienteSimulado** (un motor local determinista) que redacta el informe en la misma computadora. Así garantizamos **cero caídas**.

```
                   ┌────────────────────────────────────────┐
                   │        IA HÍBRIDA DE DIRPOLES-IA       │
                   └───────────────────┬────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
┌───────────────────────────────┐             ┌───────────────────────────────┐
│  1. SISTEMA EXPERTO (SBC)     │             │  2. GENERADOR NARRATIVO (LLM) │
│  • Motor en Pandas y MariaDB  │             │  • Google Gemini (Online)     │
│  • Reglas lógicas y umbrales  │ ──────────> │  • ClienteSimulado (Offline)  │
│  • Cero inventos ni dudas     │             │  • Redacción ejecutiva formal │
│  • Detecta alertas críticas   │             │  • Gráficos Mermaid.js        │
└───────────────────────────────┘             └───────────────────────────────┘
```

#### Las Fórmulas Matemáticas que Aplica el Motor (Simples y Claras)

No se necesitan fórmulas complejas de cálculo multivariable; la analítica de gestión se basa en dos operaciones lógicas fundamentales ejecutadas a gran velocidad:

* **1. Porcentaje o Concentración Relativa ($C_i$):**  
  Para saber si un PNF (carrera) o un motivo de consulta está acaparando la atención médica:
  $$C_i = \left( \frac{n_i}{N} \right) \times 100$$
  * $n_i$: Cantidad de atenciones en esa carrera en particular (ej. 54 alumnos de Informática).
  * $N$: Total de atenciones de todo el mes (ej. 120 alumnos en total).
  * *Resultado:* $C_{\text{Informática}} = (54 / 120) \times 100 = 45\%$. Si supera el 40%, el sistema nota que esa carrera concentra la mayor demanda.

* **2. Evaluación de Reglas de Inferencia ($R$):**  
  El motor compara el valor real encontrado en los datos ($V$) contra un umbral límite fijado por la universidad ($U$):
  $$\text{SI } \Big( V \text{ [operador] } U \Big) \implies \text{DISPARAR ALERTA}$$
  * *Ejemplo en Medicina:* Si el stock de Amoxicilina ($V$) es menor que 10 ($U$), la condición $(4 < 10)$ es verdadera $\implies$ Dispara la alerta: *"Riesgo Crítico de Desabastecimiento"*.
  * *Ejemplo en Psicología:* Si la tasa de inasistencia a citas ($V$) es mayor al 25% ($U$), la condición $(28\% > 25\%)$ es verdadera $\implies$ Dispara la alerta: *"Alta Deserción en Citas Psicológicas"*.

---

### 1.2. Diagrama de Flujo y Pseudocódigo

#### Diagrama de Flujo Paso a Paso

El siguiente diagrama muestra el camino exacto que sigue una solicitud de reporte desde que llega al microservicio:

```mermaid
flowchart TD
    A([1. Llega la petición HTTP con X-API-Key]) --> B{¿API Key válida?}
    B -- No --> C[Error 401: No Autorizado]
    B -- Sí --> D{¿Datos y fechas correctos?}
    D -- No --> E[Error 422: Datos Inválidos]
    D -- Sí --> F{¿De dónde vienen los datos?}
    
    F -- "DIRPOLES-4 (V1)" --> G[Consultar MariaDB dirpoles_business en Solo Lectura]
    F -- "Otro Sistema (V2)" --> H[Leer registros JSON recibidos en la petición]
    
    G --> I[Cargar datos en memoria con Pandas]
    H --> I
    
    I --> J[Hacer conteos, agrupaciones y porcentajes]
    J --> K[Consultar reglas en dirpoles_knowledge y evaluar umbrales]
    K --> L[Quitar nombres, cédulas e historias médicas: Privacidad Total]
    
    L --> M{¿Hay internet y responde Gemini?}
    M -- Sí --> N[Redactar informe ejecutivo con Gemini]
    M -- No --> O[Redactar informe con Motor Simulado Local]
    
    N --> P[Unir texto + tablas + gráficos Mermaid.js]
    O --> P
    P --> Q([Retornar JSON con el informe final])
```

#### Pseudocódigo Explicado en Lenguaje Natural

Este es el algoritmo en palabras simples, tal cual como lo programamos:

```text
ALGORITMO GenerarReporteInteligente(sistema_cliente, modulo, filtros):
    
    // 1. Verificamos que quien llama tenga permiso
    SI la clave_api NO coincide con la registrada:
        TERMINAR con Error 401 ("Acceso denegado")
    
    // 2. Obtenemos los registros
    SI sistema_cliente == "dirpoles4":
        datos_crudos = ConsultarBaseDeDatos(modulo, filtros) // Solo lectura
    SINO:
        datos_crudos = filtros.datos_enviados_en_json
    
    // 3. Procesamos con Pandas a gran velocidad
    tabla = CrearDataFrame(datos_crudos)
    total_registros = ContarFilas(tabla)
    conteo_por_carrera = AgruparPor(tabla, "pnf")
    conteo_por_genero = AgruparPor(tabla, "genero")
    
    // 4. Evaluamos las reglas del Sistema Experto
    alertas = []
    reglas = ObtenerReglasDesdeBaseConocimiento(modulo)
    PARA CADA regla EN reglas:
        SI CondicionCumplida(tabla, regla.hecho, regla.operador, regla.umbral):
            alertas.Agregar(regla.mensaje_alerta)
    
    // 5. Cuidamos la privacidad (Cero datos personales a la nube)
    resumen_seguro = ArmarResumen(total_registros, conteo_por_carrera, alertas)
    // NO incluimos cédulas, nombres ni expedientes
    
    // 6. Redactamos el informe
    SI hay_conexion_internet():
        informe_texto = LlamarGoogleGemini(resumen_seguro)
    SINO:
        informe_texto = GenerarConMotorSimuladoLocal(resumen_seguro)
        
    // 7. Agregamos el gráfico visual y devolvemos la respuesta
    grafico = CrearGraficoMermaid(conteo_por_carrera)
    RETORNAR RespuestaExitosa(informe_texto + grafico)
FIN DEL ALGORITMO
```

---

### 1.3. Gestión del Flujo de Datos: Ruta de la Información

Para entender cómo viaja la información entre el sistema de la universidad y la IA, dividimos la ruta en 5 estaciones:

```
[Usuario en Pantalla] ──(1) Clic en Generar──> [DIRPOLES-4 (PHP 8.3)]
                                                        │
                                          (2) Petición HTTP B2B
                                              con X-API-Key
                                                        ▼
                                             [DIRPOLES-IA (FastAPI)]
                                                        │
                      ┌─────────────────────────────────┴─────────────────────────────────┐
                      ▼                                                                   ▼
       (3A) Consulta SQL Solo Lectura                                       (3B) Evalúa Reglas y Umbrales
       [MariaDB: dirpoles_business]                                         [MariaDB: dirpoles_knowledge]
                      │                                                                   │
                      └─────────────────────────────────┬─────────────────────────────────┘
                                                        ▼
                                           (4) Procesa con Pandas
                                            y Anonimiza Datos
                                                        │
                                                        ▼
                                        (5) Redacción con IA (Gemini)
                                            o Motor de Respaldo Local
                                                        │
                                                        ▼
[Usuario ve Reporte y Gráficos] <──(6) JSON Markdown── [DIRPOLES-4 (PHP)]
```

1. **La Interfaz Web (DIRPOLES-4):** El coordinador o médico selecciona el módulo (por ejemplo, Medicina), el rango de fechas del mes y hace clic en el botón *"Generar Informe con IA"*.
2. **El Backend en PHP:** DIRPOLES-4 verifica que el usuario tenga la sesión iniciada, le coloca su `id_empleado` para saber qué médico está pidiendo el reporte, y le hace una llamada directa por red (HTTP) a nuestro microservicio enviando una clave secreta (`X-API-Key`).
3. **El Microservicio Python (FastAPI):** Recibe la petición, verifica la clave y se conecta a MariaDB con un usuario especial (`dirpoles_ia_reader`) que **solo tiene permiso para leer** (`SELECT`), así que jamás puede modificar ni borrar nada del sistema de la universidad.
4. **El Procesamiento en Memoria:** Pandas filtra los registros en microsegundos, calcula los totales y consulta la base de conocimiento para ver qué reglas se dispararon.
5. **La Redacción:** Se le manda el resumen de números (sin cédulas ni nombres) a Google Gemini o al motor simulado.
6. **El Retorno:** Nuestro microservicio responde en formato JSON con el texto en Markdown y el gráfico en Mermaid.js. PHP lo recibe y el navegador del usuario lo muestra como un informe visual con tablas y gráficos interactivos.

---

## 2. DISEÑO DE LA BASE DE CONOCIMIENTO Y ESTRUCTURA RELACIONAL (APARTADO OBLIGATORIO)

Una de las mejoras más importantes de este avance es que **el conocimiento no está escrito fijo en el código de Python**. Creamos una base de datos física dedicada en MariaDB llamada **`dirpoles_knowledge`**.

Allí se almacenan las reglas de inferencia, los síntomas o hechos medibles, las alertas y los roles profesionales. De esta forma, si el día de mañana la directiva de la UPTAEB cambia un umbral (por ejemplo, que el stock mínimo no sea 10 sino 15 unidades), **no hay que tocar el código de Python**, solo se edita una fila en la base de datos y la IA asume la nueva regla de inmediato.

---

### 2.1. Número Total e Identificación de Tablas

La Base de Conocimiento está compuesta por **7 tablas relacionales**:

| N° | Nombre de la Tabla | Categoría en Sistemas Expertos | ¿Para qué sirve en palabras sencillas? |
| :-: | :--- | :--- | :--- |
| **1** | `conocimiento_sistemas` | Entidades / Tenants | Guarda los sistemas autorizados a usar la IA (ej. `dirpoles4`, o un sistema futuro). |
| **2** | `conocimiento_hechos_sintomas` | Hechos / Síntomas | Es el catálogo de cosas que la IA puede medir (stock de insumos, ausentismo, etc.). |
| **3** | `conocimiento_conclusiones` | Conclusiones / Diagnósticos | Catálogo de alertas y recomendaciones formales que la IA puede emitir. |
| **4** | `conocimiento_reglas_inferencia` | Reglas de Producción | La regla como tal: une un hecho con su conclusión y le da una prioridad. |
| **5** | `conocimiento_regla_hecho_pivote` | Tabla Intermedia / Pivote | Guarda los valores límite: qué operador usa (`<`, `>`, `==`) y cuál es el umbral (ej. 10). |
| **6** | `conocimiento_roles_prompts` | Personalidad del Especialista | Le indica a la IA cómo hablar según el área (como médico, psicólogo, etc.). |
| **7** | `conocimiento_catalogos_autorizados` | Vocabulario Oficial | Lista oficial de carreras (PNF) de la UPTAEB para evitar que la IA invente carreras. |

---

### 2.2. Definición de Atributos y Tipos de Datos (Diccionario de Datos)

A continuación describimos las 7 tablas con sus campos, tipos de datos y llaves primarias/foráneas:

#### Tabla 1: `conocimiento_sistemas`
Identifica a cada sistema consumidor que se conecta al microservicio.
* `id` (`VARCHAR(50)`, **PK**): Código del sistema (ej. `'dirpoles4'`).
* `nombre` (`VARCHAR(150)`): Nombre completo (ej. `'Sistema DIRPOLES-4 UPTAEB'`).
* `api_key` (`VARCHAR(128)`, **UNIQUE**): Clave secreta con la que se identifica el sistema.
* `modo_acceso` (`ENUM('sql_pull', 'push')`): Si nosotros leemos su base de datos o si ellos nos mandan un JSON.
* `activo` (`TINYINT(1)`): `1` si está activo, `0` si está suspendido.
* `creado_el` (`TIMESTAMP`): Fecha en que se registró el sistema.

#### Tabla 2: `conocimiento_hechos_sintomas`
Es la lista de métricas o variables que el sistema experto sabe buscar y calcular.
* `id` (`INT`, **PK**, Auto-incremental): Número único del hecho.
* `sistema_id` (`VARCHAR(50)`, **FK** a `conocimiento_sistemas.id`): A qué sistema pertenece.
* `codigo_hecho` (`VARCHAR(60)`): Nombre corto (ej. `'STOCK_INSUMO_MEDICO'`, `'TASA_AUSENTISMO'`).
* `dominio` (`VARCHAR(50)`): Área (ej. `'medicina'`, `'psicologia'`, `'transporte'`).
* `nombre` (`VARCHAR(150)`): Nombre legible del hecho.
* `tipo_dato` (`ENUM('entero', 'decimal', 'porcentaje', 'texto')`): Tipo de valor que maneja.
* `unidad_medida` (`VARCHAR(30)`): Unidad (ej. `'unidades'`, `'%'`, `'días'`).
* `descripcion` (`TEXT`): Explicación de qué significa esta métrica.

#### Tabla 3: `conocimiento_conclusiones`
Guarda los dictámenes y alertas que el sistema puede generar cuando se cumple una regla.
* `id` (`INT`, **PK**, Auto-incremental): Número único de la conclusión.
* `sistema_id` (`VARCHAR(50)`, **FK** a `conocimiento_sistemas.id`): Sistema correspondiente.
* `codigo_conclusion` (`VARCHAR(60)`): Código de la alerta (ej. `'DIAG_MED_STOCK_CRITICO'`).
* `dominio` (`VARCHAR(50)`): Área a la que aplica.
* `nivel_severidad` (`ENUM('info', 'advertencia', 'critico')`): Qué tan grave es la alerta.
* `titulo_diagnostico` (`VARCHAR(200)`): Título de la alerta para el informe.
* `plantilla_mensaje` (`TEXT`): Texto base con el mensaje que se mostrará.
* `recomendacion_sugerida` (`TEXT`): Recomendación práctica que se le da al directivo.

#### Tabla 4: `conocimiento_reglas_inferencia`
Representa la regla en sí misma, conectando la condición con la conclusión a disparar.
* `id` (`INT`, **PK**, Auto-incremental): Identificador de la regla.
* `sistema_id` (`VARCHAR(50)`, **FK** a `conocimiento_sistemas.id`): Sistema al que aplica.
* `codigo_regla` (`VARCHAR(60)`): Código de la regla (ej. `'REG-MED-01'`, `'REG-PSI-01'`).
* `dominio` (`VARCHAR(50)`): Módulo donde trabaja.
* `conclusion_id` (`INT`, **FK** a `conocimiento_conclusiones.id`): Qué alerta dispara si se cumple.
* `nombre_regla` (`VARCHAR(200)`): Nombre descriptivo de la regla.
* `descripcion_logica` (`TEXT`): Explicación en español (ej. *"SI stock < 10 ENTONCES alerta crítica"*).
* `prioridad` (`INT`): Orden de importancia (las más altas se evalúan primero).
* `activa` (`TINYINT(1)`): `1` para activada, `0` para desactivada temporalmente.

#### Tabla 5: `conocimiento_regla_hecho_pivote` (Tabla Intermedia)
Es la tabla clave que define **cuándo** se dispara la regla: compara el hecho con el umbral.
* `id` (`INT`, **PK**, Auto-incremental): Identificador de la condición.
* `regla_id` (`INT`, **FK** a `conocimiento_reglas_inferencia.id`): A qué regla pertenece.
* `hecho_id` (`INT`, **FK** a `conocimiento_hechos_sintomas.id`): Qué métrica está evaluando.
* `operador_comparacion` (`ENUM('<', '<=', '>', '>=', '==', '!=')`): Cómo compara (`<`, `>`, etc.).
* `valor_umbral` (`DECIMAL(12,2)`): El número límite (ej. `10.00`, `25.00`).
* `operador_logico_siguiente` (`ENUM('AND', 'OR', 'FIN')`): Para encadenar varias condiciones.
* `orden` (`INT`): Orden en el que se evalúa si hay varias condiciones.

#### Tabla 6: `conocimiento_roles_prompts`
Guarda el perfil del especialista que la IA debe simular al redactar.
* `id` (`INT`, **PK**, Auto-incremental): Identificador del perfil.
* `sistema_id` (`VARCHAR(50)`, **FK** a `conocimiento_sistemas.id`): Sistema asociado.
* `dominio` (`VARCHAR(50)`): Módulo (ej. `'medicina'`, `'psicologia'`).
* `nombre_rol` (`VARCHAR(150)`): Nombre del puesto (ej. *"Médico Evaluador de DIRPOLES"*).
* `instrucciones_sistema` (`TEXT`): La orden que se le da a Gemini sobre cómo debe escribir y expresarse.
* `enfoque_por_defecto` (`VARCHAR(255)`): Enfoque que debe priorizar en el análisis.
* `directrices_privacidad` (`TEXT`): Instrucciones estrictas de confidencialidad médica y estudiantil.

#### Tabla 7: `conocimiento_catalogos_autorizados`
Almacena listas cerradas de valores válidos de la UPTAEB (carreras PNF, estados de citas).
* `id` (`INT`, **PK**, Auto-incremental): Identificador del elemento.
* `sistema_id` (`VARCHAR(50)`, **FK** a `conocimiento_sistemas.id`): Sistema al que pertenece.
* `tipo_catalogo` (`VARCHAR(60)`): Tipo de lista (ej. `'pnf'`).
* `codigo` (`VARCHAR(60)`): Identificador interno (ej. `'3'`).
* `nombre_oficial` (`VARCHAR(150)`): Nombre oficial (ej. `'Informática'`, `'Agroalimentación'`).
* `activo` (`TINYINT(1)`): `1` si el PNF está activo en la universidad.

---

### 2.3. Diagrama Entidad-Relación (DER) de la Base de Conocimiento

El siguiente diagrama muestra cómo se relacionan entre sí las 7 tablas de `dirpoles_knowledge`:

```mermaid
erDiagram
    conocimiento_sistemas ||--o{ conocimiento_hechos_sintomas : "posee hechos"
    conocimiento_sistemas ||--o{ conocimiento_conclusiones : "posee alertas"
    conocimiento_sistemas ||--o{ conocimiento_reglas_inferencia : "posee reglas"
    conocimiento_sistemas ||--o{ conocimiento_roles_prompts : "configura roles"
    conocimiento_sistemas ||--o{ conocimiento_catalogos_autorizados : "restringe valores"

    conocimiento_reglas_inferencia ||--|| conocimiento_conclusiones : "dispara alerta"
    conocimiento_reglas_inferencia ||--|{ conocimiento_regla_hecho_pivote : "se compone de"
    conocimiento_hechos_sintomas ||--o{ conocimiento_regla_hecho_pivote : "es medido por"

    conocimiento_sistemas {
        varchar id PK "dirpoles4"
        varchar nombre
        varchar api_key UK
        enum modo_acceso "sql_pull | push"
        tinyint activo
    }

    conocimiento_hechos_sintomas {
        int id PK
        varchar sistema_id FK
        varchar codigo_hecho "STOCK_INSUMO"
        varchar dominio "medicina"
        enum tipo_dato "entero | porcentaje"
        varchar unidad_medida
    }

    conocimiento_conclusiones {
        int id PK
        varchar sistema_id FK
        varchar codigo_conclusion "DIAG_MED_STOCK"
        varchar dominio
        enum nivel_severidad "info | advertencia | critico"
        varchar titulo_diagnostico
        text recomendacion_sugerida
    }

    conocimiento_reglas_inferencia {
        int id PK
        varchar sistema_id FK
        varchar codigo_regla "REG-MED-01"
        int conclusion_id FK
        text descripcion_logica
        int prioridad
        tinyint activa
    }

    conocimiento_regla_hecho_pivote {
        int id PK
        int regla_id FK
        int hecho_id FK
        enum operador_comparacion "< | >"
        decimal valor_umbral "10.00"
        enum operador_logico_siguiente "AND | FIN"
    }

    conocimiento_roles_prompts {
        int id PK
        varchar sistema_id FK
        varchar dominio "medicina"
        varchar nombre_rol "Médico Evaluador"
        text instrucciones_sistema
    }

    conocimiento_catalogos_autorizados {
        int id PK
        varchar sistema_id FK
        varchar tipo_catalogo "pnf"
        varchar codigo "3"
        varchar nombre_oficial "Informática"
    }
```

---

### 2.4. Justificación Estructural: ¿Por qué este modelo es ideal?

Existen tres razones muy claras para defender este diseño ante cualquier jurado:

1. **Cero cambios de código para actualizar reglas:** Si el servicio médico decide que el stock de alarma ya no es 10 sino 15 pastillas, simplemente se actualiza el campo `valor_umbral` en la tabla `conocimiento_regla_hecho_pivote`. El programador no tiene que tocar el código ni reiniciar el servidor.
2. **Es Multitenant (Multiusuario Institucional):** Gracias al campo `sistema_id`, podemos guardar en la misma base de datos las reglas del sistema de salud de DIRPOLES (`dirpoles4`) y las reglas de un sistema de control de autobuses universitarios (`flota_transporte`), sin que se mezclen ni se confundan.
3. **Es 100% Auditable:** Cada vez que el sistema emite una alerta, podemos señalar exactamente qué fila de la tabla `conocimiento_reglas_inferencia` se activó, con qué número y bajo qué criterio. No hay "magia" ni decisiones arbitrarias.

---

## 3. INGENIERÍA DE DATOS Y ESTRATEGIA DE ALIMENTACIÓN

### 3.1. Fuentes de Datos
* **Base de Datos Operativa de DIRPOLES-4 (`dirpoles_business`):**  
  Es la base de datos real del sistema que viene del Trayecto III (desarrollada en MySQL/MariaDB). El microservicio se conecta mediante un usuario con permisos exclusivos de **Solo Lectura (`READ-ONLY`)**. Esto garantiza que bajo ninguna circunstancia el componente de IA pueda modificar, alterar o borrar registros de estudiantes, citas o diagnósticos.
* **Fuentes Externas por API (Modo Push):**  
  Para cualquier otro sistema que no comparta la base de datos de DIRPOLES, el microservicio cuenta con el endpoint `POST /api/v2/analizar`, donde el sistema externo simplemente le envía un archivo JSON con los datos que quiere que analice.

### 3.2. Preprocesamiento y Limpieza de Datos

Antes de evaluar cualquier regla o llamar a la IA, los datos pasan por tres pasos de limpieza:

1. **Estructuración y Limpieza con Pandas:**  
   Los datos se cargan en tablas de memoria llamadas DataFrames. Si hay fechas en blanco, valores nulos o texto mal formateado, Pandas los limpia, descarta filas dañadas y asegura que los números sean efectivamente números válidos.
2. **Protección Estricta de la Privacidad (Cero Fuga de Datos Personales):**  
   Este es un punto fundamental de ética e ingeniería: **ningún dato personal de ningún estudiante de la UPTAEB viaja a los servidores de Google Gemini**.  
   * Se eliminan por completo los nombres, apellidos, cédulas de identidad e historias clínicas.  
   * A la IA generativa únicamente se le envían **números totales y tablas de porcentaje ya calculadas** (por ejemplo: *"Se atendieron 120 alumnos: 54 de Informática, 36 de Administración, 30 de Agroalimentación"*).
3. **Filtro de Inyección de Prompts:**  
   Si el médico escribe una nota libre al pedir el reporte, el microservicio la limpia con expresiones regulares para evitar que alguien intente colocar instrucciones tramposas que confundan a la IA.

### 3.3. Actualización del Conocimiento: Dinámica en Caliente

La actualización de la base de conocimiento es **dinámica**:
* Cuando el microservicio arranca, lee las 7 tablas de `dirpoles_knowledge` y las guarda en memoria para responder de inmediato.
* Si el administrador de DIRPOLES cambia una regla o agrega una nueva carrera en la base de datos, el microservicio refresca sus datos sin tener que detenerse ni interrumpir el trabajo de los usuarios.

---

## 4. DISEÑO DE INTERACCIÓN Y EXPERIENCIA DE USUARIO (UI/UX)

### 4.1. Mecanismos de Entrada y Salida
* **Entrada (Lo que hace el usuario):**  
  El usuario final (el médico, psicólogo o directivo) no tiene que aprender comandos complicados ni escribir preguntas complejas a la IA. Solo usa selectores sencillos en la pantalla de DIRPOLES-4:
  * Elige el módulo (Medicina, Psicología, Trabajo Social, etc.).
  * Elige las fechas del reporte (desde / hasta).
  * Elige el tipo de reporte (*Resumen Ejecutivo*, *Alertas y Anomalías*, *Distribución Demográfica*).
  * Opcionalmente, puede escribir una observación breve.
* **Salida (Lo que recibe el usuario):**  
  El sistema le entrega en pantalla:
  * Un informe ejecutivo en texto formal y ordenado (formato Markdown).
  * Cuadros de alerta resaltados con iconos de atención (`> ⚠️ **Punto Crítico:**`).
  * Tablas numéricas ordenadas con porcentajes calculados.
  * **Gráficos visuales generados automáticamente con Mermaid.js** (gráficos circulares de pastel `pie` y gráficos de barras), los cuales se dibujan de manera interactiva en el navegador sin recargar la página.

---

### 4.2. Boceto de la Pantalla en DIRPOLES-4 (Mockup)

Así es como se visualiza la integración de la IA dentro de las pantallas ya aprobadas en el Trayecto III:

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│  DIRPOLES-4 — Módulo de Medicina: Reporte Asistido por Inteligencia Artificial        │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│  [ Filtros de Consulta ]                                                               │
│  Rango de Fechas: [ 01/10/2026 ] al [ 28/10/2026 ]    Carrera PNF: [ Informática    ▼] │
│  Tipo de Informe: [ Alertas y Anomalías       ▼]    Género:      [ Todos          ▼] │
│                                                                                        │
│  Observaciones del Especialista (Opcional):                                            │
│  [ Revisar el consumo de medicamentos antibióticos en el turno de la mañana...       ] │
│                                                                                        │
│                                  [ 📊 Generar Informe con IA ]                         │
├────────────────────────────────────────────────────────────────────────────────────────┤
│  RESULTADO DEL ANÁLISIS GENERADO:                                                      │
│                                                                                        │
│  ### 📊 Informe Ejecutivo de Salud: Módulo Medicina                                   │
│  **Periodo Evaluado:** 01/10/2026 al 28/10/2026 | **Total Consultas:** 120            │
│                                                                                        │
│  > ⚠️ **Punto Crítico Detectado:** Se detectaron 2 insumos esenciales con stock bajo.  │
│  > • Amoxicilina 500mg: 4 unidades restantes (Umbral crítico: 10 unidades).            │
│  > • Solución Fisiológica: 2 unidades restantes (Umbral crítico: 10 unidades).        │
│                                                                                        │
│  #### Distribución de Pacientes por PNF Atendido                                       │
│  ┌─────────────────────────────┬──────────────────────────┬─────────────────────────┐  │
│  │ Carrera / PNF               │ N° de Consultas Médicas  │ Porcentaje del Total    │  │
│  ├─────────────────────────────┼──────────────────────────┼─────────────────────────┤  │
│  │ PNF Informática             │ 54                       │ 45.0 %                  │  │
│  │ PNF Administración          │ 36                       │ 30.0 %                  │  │
│  │ PNF Agroalimentación        │ 30                       │ 25.0 %                  │  │
│  └─────────────────────────────┴──────────────────────────┴─────────────────────────┘  │
│                                                                                        │
│  [ DIAGRAMA VISUAL RENDERIZADO AL INSTANTE CON MERMAID.JS: ]                           │
│  ```mermaid                                                                            │
│  pie title Consultas Médicas por PNF                                                   │
│      "Informática" : 54                                                                │
│      "Administración" : 36                                                             │
│      "Agroalimentación" : 30                                                           │
│  ```                                                                                   │
│                                                                                        │
│  [ 🖨️ Imprimir Reporte en PDF ]    [ 📥 Descargar Informe ]                            │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

### 4.3. Explicabilidad (XAI): Cero Efecto "Caja Negra"

Un problema muy común en los proyectos de IA es que el sistema da una recomendación pero nadie sabe por qué la dio (el clásico efecto de "caja negra"). 

En nuestro componente, **todo resultado es 100% explicable y transparente**:
1. **Muestra el dato numérico exacto:** No dice *"faltan medicinas"*, dice *"Amoxicilina: quedan 4 unidades"*.
2. **Muestra la regla que se activó:** Explica que saltó la alerta porque 4 es menor que el umbral mínimo institucional de 10 unidades establecido en la regla `REG-MED-01`.
3. **Separa los hechos de las sugerencias:** Los números y las alertas son hechos matemáticos; las recomendaciones son sugerencias para que el directivo o médico tome la decisión final con criterio humano.

---

## 5. ESTRATEGIA DE PRUEBAS, VALIDACIÓN Y MÉTRICAS DE ÉXITO

### 5.1. Criterios de Validación Socio-Comunitaria
Para comprobar que el componente realmente ayuda a la comunidad de la UPTAEB, establecimos tres criterios prácticos:
* **Ahorro de tiempo para el personal:** El personal de bienestar estudiantil tardaba hasta 4 horas armando a mano los reportes mensuales en hojas de cálculo. Con este componente, el informe completo se genera en **menos de 2 segundos**.
* **Prevención de desabastecimiento:** El sistema avisa que un insumo o repuesto se está acabando antes de que llegue a cero, evitando que un estudiante se quede sin atención médica por falta de medicinas.
* **Alerta temprana de deserción estudiantil:** Si en Psicología se detecta que más del 25% de las citas quedan desatendidas o abandonadas, el sistema alerta al departamento para hacer seguimiento a esos estudiantes.

---

### 5.2. Métricas de Desempeño Técnico Comprobadas

Probamos el sistema con un conjunto de pruebas automatizadas y estos fueron los resultados reales obtenidos:

| Indicador Técnico | Meta Propuesta | Resultado Real Obtenido | ¿Se cumplió? |
| :--- | :---: | :---: | :---: |
| **Tiempo de respuesta (Latencia)** | Menos de 2 segundos | **Entre 0.45 y 1.25 segundos** | Sí, superada ampliamente |
| **Disponibilidad del servicio** | 100% garantizado | **100%** (Gracias al respaldo local) | Sí, nunca se cae |
| **Fuga de datos personales (PII)** | 0% tolerancia | **0%** (Cero cédulas o nombres enviados) | Sí, privacidad total |
| **Pruebas unitarias en Python** | Más de 80% de éxito | **129 pruebas pasadas con 100% de éxito** | Sí, verificado |
| **Pruebas de conexión con PHP (DIRPOLES-4)** | 100% de éxito | **31 pruebas de contrato pasadas con éxito** | Sí, verificado |

---

### 5.3. Casos de Prueba Iniciales (Escenarios Reales)

Diseñamos una matriz de pruebas para verificar cómo reacciona el componente ante distintas situaciones:

| N° Caso | Situación de Entrada | ¿Qué se evalúa? | Salida Esperada | Resultado Real |
| :-: | :--- | :--- | :--- | :---: |
| **CP-01** | Petición sin la clave `X-API-Key`. | Seguridad de acceso. | Bloqueo inmediato con error `HTTP 401 Unauthorized`. | **Aprobado** |
| **CP-02** | Rango de fechas al revés (`desde` mayor a `hasta`). | Validación de datos. | Rechazo con error `HTTP 422 Unprocessable Entity`. | **Aprobado** |
| **CP-03** | Módulo de Medicina con inventario de pastillas = 4. | Regla `REG-MED-01`. | Genera alerta crítica de stock bajo y gráfico de pastel. | **Aprobado** |
| **CP-04** | Petición realizada con el cable de internet desconectado. | Mecanismo de respaldo. | El sistema conmuta a `ClienteSimulado` y responde bien. | **Aprobado** |
| **CP-05** | Consulta hecha por un médico con `id_empleado = 17`. | Control de acceso (RBAC). | Solo analiza y muestra los pacientes de ese médico. | **Aprobado** |
| **CP-06** | Consulta hecha por un directivo con `id_empleado = null`. | Visibilidad global. | Analiza los pacientes de todos los médicos de la UPTAEB. | **Aprobado** |

---

## 6. ARQUITECTURA TECNOLÓGICA Y ENTORNO DE DESARROLLO

### 6.1. Stack Tecnológico Justificado
Cada herramienta fue elegida pensando en su rendimiento, facilidad de uso y compatibilidad con lo que ya tiene la universidad:

* **Python 3.12+ con FastAPI:** Es el corazón del microservicio. FastAPI es súper rápido, valida los datos automáticamente y genera la documentación técnica de forma interactiva.
* **Pandas:** La librería por excelencia para el manejo de datos. Nos permite procesar, agrupar y filtrar miles de registros en la memoria RAM en milésimas de segundo.
* **MariaDB 10.4+ / MySQL 8.0+:** El motor de base de datos donde conviven las tablas del sistema DIRPOLES-4 y nuestra base de conocimiento `dirpoles_knowledge`.
* **SQLAlchemy:** La herramienta que conecta Python con MariaDB de forma segura, rápida y en modo de solo lectura.
* **Google Gemini API (Modelo Flash):** La inteligencia artificial generativa en la nube encargada de redactar la explicación final con lenguaje formal y amigable.
* **PHP 8.3 (DIRPOLES-4):** El sistema web de la universidad que consume nuestro microservicio.
* **Mermaid.js:** Librería de JavaScript muy liviana que convierte texto plano en gráficos vectoriales bonitos en la pantalla del usuario.

### 6.2. Infraestructura y Requerimientos de Servidor
* **Hardware Mínimo Recomendado:**
  * **Procesador:** Cualquier procesador de 2 núcleos a 2.0 GHz o superior.
  * **Memoria RAM:** 2 GB de memoria RAM libre (el microservicio es muy ligero: consume apenas 180 MB en reposo y unos 350 MB cuando procesa reportes grandes).
  * **Disco Duro:** 500 MB de espacio disponible para Python, el entorno virtual y las librerías.
* **Software y Sistema Operativo:**
  * Servidor Linux (Ubuntu 22.04 LTS, Debian 12 o Fedora) o Windows Server.
  * Servidor web Apache o Nginx para dirigir las peticiones.

---

## 7. CRONOGRAMA DE ACTIVIDADES (SEMANAS RESTANTES)

Para organizar las semanas que quedan de clases hasta la defensa final del Proyecto Socio-Tecnológico IV, planteamos el siguiente plan de trabajo:

```mermaid
gantt
    title Plan de Trabajo - Semanas Restantes del PST IV
    dateFormat  YYYY-MM-DD
    section Fase II (Actual)
    Diseño del Algoritmo y Base de Conocimiento :done, t1, 2026-10-20, 2026-10-24
    Pruebas Unitarias y Conexión MariaDB        :done, t2, 2026-10-25, 2026-10-28
    Entrega Formal del Segundo Avance de IA     :active, t3, 2026-10-29, 2026-10-31
    section Fase III (Integración y Despliegue)
    Conectar base de conocimiento en servidor real: t4, 2026-11-01, 2026-11-07
    Ajustar diseño de gráficos en pantallas PHP   : t5, 2026-11-08, 2026-11-14
    Pruebas de carga con varios usuarios a la vez : t6, 2026-11-15, 2026-11-21
    section Validación y Cierre
    Pruebas con el personal de Bienestar UPTAEB   : t7, 2026-11-22, 2026-11-28
    Redacción del manual de usuario y técnico     : t8, 2026-11-29, 2026-12-05
    Defensa Final de Grado del Proyecto PST IV    : t9, 2026-12-06, 2026-12-12
```

---

## CONCLUSIÓN PARA LA DEFENSA

Para cerrar esta entrega y resumirlo de forma muy clara:
1. **Cumplimos con un Sistema Basado en Conocimiento real:** El componente no es solo una llamada a una API externa; tiene su propio motor de reglas y su propia base de datos de conocimiento (`dirpoles_knowledge`) con 7 tablas bien relacionadas en MariaDB.
2. **Cuidamos la privacidad de los estudiantes:** Nunca mandamos cédulas ni nombres a Google Gemini; la analítica pesada la hace Pandas en la máquina local.
3. **El sistema nunca se queda colgado:** Si no hay internet en la universidad, el motor de respaldo local asume el control y entrega el reporte con total normalidad.
4. **Está listo para crecer:** Al ser un microservicio independiente, le sirve hoy a DIRPOLES-4 y mañana a cualquier otro proyecto de la UPTAEB.
