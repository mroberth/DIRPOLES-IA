-- =============================================================================
-- ESQUEMA DE LA BASE DE DATOS DEL CONOCIMIENTO: dirpoles_knowledge
-- Sistema de Inteligencia Artificial para el Ecosistema DIRPOLES (UPTAEB)
-- Arquitectura: Sistema Basado en Conocimiento (SBC) Multitenant
-- Motor: MariaDB 10.4+ / MySQL 8.0+ | Juego de Caracteres: utf8mb4_unicode_ci
-- =============================================================================

CREATE DATABASE IF NOT EXISTS `dirpoles_knowledge`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `dirpoles_knowledge`;

-- -----------------------------------------------------------------------------
-- 1. TABLA MAESTRA DE SISTEMAS CONSUMIDORES (Tenants)
-- Identifica a qué sistema o cliente pertenece cada fragmento de conocimiento.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_sistemas` (
    `id` VARCHAR(50) NOT NULL COMMENT 'Identificador único del sistema (ej: dirpoles4, flota_go)',
    `nombre` VARCHAR(150) NOT NULL COMMENT 'Nombre legible del sistema consumidor',
    `api_key` VARCHAR(128) NOT NULL COMMENT 'Clave de autenticación B2B asignada al sistema',
    `modo_acceso` ENUM('sql_pull', 'push') NOT NULL DEFAULT 'push' COMMENT 'Modo de ingesta de datos',
    `activo` TINYINT(1) NOT NULL DEFAULT 1 COMMENT '1 = Activo, 0 = Inactivo',
    `creado_el` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `actualizado_el` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_sistemas_api_key` (`api_key`)
) ENGINE=InnoDB COMMENT='Sistemas consumidores autorizados en el ecosistema';

-- -----------------------------------------------------------------------------
-- 2. TABLA DE HECHOS / SÍNTOMAS (Variables Observables)
-- Define las variables métricas y cuantitativas que el motor de IA puede evaluar.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_hechos_sintomas` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `codigo_hecho` VARCHAR(60) NOT NULL COMMENT 'Código único del hecho (ej: STOCK_INSUMO, AUSENTISMO_CITA)',
    `dominio` VARCHAR(50) NOT NULL COMMENT 'Módulo o área temática (ej: medicina, psicologia, transporte)',
    `nombre` VARCHAR(150) NOT NULL COMMENT 'Nombre descriptivo del síntoma o variable',
    `descripcion` TEXT NULL COMMENT 'Explicación del significado clínico/operativo de la variable',
    `tipo_dato` ENUM('entero', 'decimal', 'porcentaje', 'texto') NOT NULL DEFAULT 'decimal',
    `unidad_medida` VARCHAR(30) NULL COMMENT 'Unidad: unidades, %, días, horas, km',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_hecho_sistema_codigo` (`sistema_id`, `codigo_hecho`),
    CONSTRAINT `fk_hechos_sistema` FOREIGN KEY (`sistema_id`) REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Catálogo de hechos observables y variables cuantitativas';

-- -----------------------------------------------------------------------------
-- 3. TABLA DE CONCLUSIONES / DIAGNÓSTICOS / ALERTAS
-- Catálogo de dictámenes, diagnósticos automáticos o recomendaciones que emite la IA.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_conclusiones` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `codigo_conclusion` VARCHAR(60) NOT NULL COMMENT 'Código único (ej: ALERTA_STOCK_CRITICO, RIESGO_DESERCION)',
    `dominio` VARCHAR(50) NOT NULL COMMENT 'Módulo o área funcional',
    `nivel_severidad` ENUM('info', 'advertencia', 'critico') NOT NULL DEFAULT 'advertencia',
    `titulo_diagnostico` VARCHAR(200) NOT NULL COMMENT 'Encabezado del dictamen diagnóstico',
    `plantilla_mensaje` TEXT NOT NULL COMMENT 'Texto explicativo con placeholders ({valor}, {umbral})',
    `recomendacion_sugerida` TEXT NOT NULL COMMENT 'Acción sugerida para el tomador de decisiones',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_conclusion_sistema_codigo` (`sistema_id`, `codigo_conclusion`),
    CONSTRAINT `fk_conclusiones_sistema` FOREIGN KEY (`sistema_id`) REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Catálogo de conclusiones, diagnósticos y alertas del SBC';

-- -----------------------------------------------------------------------------
-- 4. TABLA DE REGLAS DE INFERENCIA
-- Reglas lógicas de producción (IF Premisa THEN Conclusión).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_reglas_inferencia` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `codigo_regla` VARCHAR(60) NOT NULL COMMENT 'Código formal (ej: REG-MED-01, REG-PSI-02)',
    `dominio` VARCHAR(50) NOT NULL,
    `conclusion_id` INT NOT NULL COMMENT 'Conclusión o alerta que se dispara si la regla se cumple',
    `nombre_regla` VARCHAR(200) NOT NULL,
    `descripcion_logica` TEXT NOT NULL COMMENT 'Expresión formal en lenguaje natural de la regla',
    `prioridad` INT NOT NULL DEFAULT 1 COMMENT 'Orden de evaluación (mayor número = mayor prioridad)',
    `activa` TINYINT(1) NOT NULL DEFAULT 1,
    `creado_el` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_regla_sistema_codigo` (`sistema_id`, `codigo_regla`),
    CONSTRAINT `fk_reglas_sistema` FOREIGN KEY (`sistema_id`) REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_reglas_conclusion` FOREIGN KEY (`conclusion_id`) REFERENCES `conocimiento_conclusiones` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Reglas lógicas de inferencia del sistema experto';

-- -----------------------------------------------------------------------------
-- 5. TABLA PIVOTE / INTERMEDIA: REGLA <-> HECHOS (Condiciones Compuestas)
-- Permite que una regla de inferencia evalúe uno o varios hechos simultáneos
-- mediante operadores relacionales (ej: SI stock < 10 Y dias_vencimiento <= 30).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_regla_hecho_pivote` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `regla_id` INT NOT NULL,
    `hecho_id` INT NOT NULL,
    `operador_comparacion` ENUM('<', '<=', '>', '>=', '==', '!=') NOT NULL DEFAULT '<',
    `valor_umbral` DECIMAL(12,2) NOT NULL COMMENT 'Valor numérico del umbral que activa la condición',
    `operador_logico_siguiente` ENUM('AND', 'OR', 'FIN') NOT NULL DEFAULT 'FIN' COMMENT 'Conector con la siguiente condición',
    `orden` INT NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    CONSTRAINT `fk_pivote_regla` FOREIGN KEY (`regla_id`) REFERENCES `conocimiento_reglas_inferencia` (`id`) ON DELETE CASCADE,
    CONSTRAINT `fk_pivote_hecho` FOREIGN KEY (`hecho_id`) REFERENCES `conocimiento_hechos_sintomas` (`id`) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='Tabla pivote que vincula premisas de hechos con reglas de inferencia';

-- -----------------------------------------------------------------------------
-- 6. TABLA DE ROLES Y PROMPTS DEL AGENTE ESPECIALISTA
-- Define la identidad técnica, directrices deontológicas y enfoque de redacción de la IA.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_roles_prompts` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `dominio` VARCHAR(50) NOT NULL COMMENT 'Módulo específico (medicina, psicologia, etc.)',
    `nombre_rol` VARCHAR(150) NOT NULL COMMENT 'Ej: Médico Especialista en Epidemiología Comunitaria',
    `instrucciones_sistema` TEXT NOT NULL COMMENT 'Prompt de sistema base inyectado al LLM',
    `enfoque_por_defecto` VARCHAR(255) NOT NULL COMMENT 'Enfoque analítico prioritario',
    `directrices_privacidad` TEXT NOT NULL COMMENT 'Instrucciones explícitas de anonimización y secreto profesional',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_rol_sistema_dominio` (`sistema_id`, `dominio`),
    CONSTRAINT `fk_roles_sistema` FOREIGN KEY (`sistema_id`) REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Perfiles de agentes inteligentes y directrices de redacción';

-- -----------------------------------------------------------------------------
-- 7. TABLA DE CATÁLOGOS INSTITUCIONALES AUTORIZADOS
-- Listas cerradas de dominios válidos (evita alucinaciones y protege datos sensibles).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `conocimiento_catalogos_autorizados` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `tipo_catalogo` VARCHAR(60) NOT NULL COMMENT 'Tipo: pnf, estados_cita, tipos_insumo, rutas',
    `codigo` VARCHAR(60) NOT NULL COMMENT 'Identificador canónico (ej: 3, ASISTIDA, RUTA_NORTE)',
    `nombre_oficial` VARCHAR(150) NOT NULL COMMENT 'Denominación oficial institucional',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    KEY `idx_catalogos_busqueda` (`sistema_id`, `tipo_catalogo`, `codigo`),
    CONSTRAINT `fk_catalogos_sistema` FOREIGN KEY (`sistema_id`) REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Catálogos institucionales cerrados para validación de datos';


-- =============================================================================
-- DATOS INICIALES (SEEDS / SEMILLAS) DE CONOCIMIENTO INSTITUCIONAL
-- =============================================================================

-- -----------------------------------------------------------------------------
-- A. Registrar Sistemas Consumidores
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_sistemas` (`id`, `nombre`, `api_key`, `modo_acceso`) VALUES
('dirpoles4', 'DIRPOLES-4 Monolito Institucional (UPTAEB)', '7ddfa2b3de679f470ac9a193aa3405d2', 'sql_pull'),
('flota_go', 'Sistema de Gestión de Rutas y Autobuses (Go)', 'clave_secreta_go_flotas_2026', 'push')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`);

-- -----------------------------------------------------------------------------
-- B. Registrar Hechos / Síntomas Observables para DIRPOLES-4
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_hechos_sintomas` (`sistema_id`, `codigo_hecho`, `dominio`, `nombre`, `tipo_dato`, `unidad_medida`, `descripcion`) VALUES
('dirpoles4', 'STOCK_INSUMO_MEDICO', 'medicina', 'Nivel de Existencia de Insumo Médico', 'entero', 'unidades', 'Cantidad física disponible del insumo en el almacén de salud'),
('dirpoles4', 'TASA_AUSENTISMO_CITA_PSI', 'psicologia', 'Tasa de Inasistencia a Citas Psicológicas', 'porcentaje', '%', 'Porcentaje de citas programadas que terminan en inasistencia'),
('dirpoles4', 'AFORO_EFECTIVO_JORNADA', 'jornadas', 'Porcentaje de Asistencia a Jornada de Salud', 'porcentaje', '%', 'Beneficiarios atendidos respecto a la capacidad planificada'),
('dirpoles4', 'CONCENTRACION_SOLICITUD_BECA', 'trabajo_social', 'Concentración de Trámites en Submódulo Becas', 'porcentaje', '%', 'Proporción de solicitudes de becas respecto al total de bienestar'),
('dirpoles4', 'RECIEN_EGRESADO_PENDIENTE_REF', 'referencias', 'Días de Demora en Referencia Médica Externa', 'entero', 'días', 'Días transcurridos desde que se emitió una referencia sin ser atendida'),
('dirpoles4', 'STOCK_REPUESTOS_TRANSPORTE', 'transporte', 'Existencia de Repuestos Automotrices Críticos', 'entero', 'unidades', 'Cantidad en inventario de repuestos para unidades de transporte')
ON DUPLICATE KEY UPDATE `nombre`=VALUES(`nombre`);

-- -----------------------------------------------------------------------------
-- C. Registrar Conclusiones / Diagnósticos para DIRPOLES-4
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_conclusiones` (`sistema_id`, `codigo_conclusion`, `dominio`, `nivel_severidad`, `titulo_diagnostico`, `plantilla_mensaje`, `recomendacion_sugerida`) VALUES
('dirpoles4', 'DIAG_MED_STOCK_CRITICO', 'medicina', 'critico', 'Riesgo de Desabastecimiento de Insumos Médicos', 'Se detectaron insumos médicos con existencias inferiores a {umbral} unidades.', 'Tramitar solicitud prioritaria de reabastecimiento ante almacén central.'),
('dirpoles4', 'DIAG_PSI_ALTO_AUSENTISMO', 'psicologia', 'advertencia', 'Deserción Significativa en Consultas de Psicología', 'La tasa de inasistencia a citas superó el {umbral}% en el periodo.', 'Implementar recordatorio de citas vía mensajería y revisar turnos vespertinos.'),
('dirpoles4', 'DIAG_JOR_BAJO_AFORO', 'jornadas', 'advertencia', 'Baja Convocatoria en Jornada de Salud Preventiva', 'El aforo efectivo de la jornada fue inferior al {umbral}% de lo proyectado.', 'Reforzar la difusión en vocerías de aula y coordinaciones de PNF.'),
('dirpoles4', 'DIAG_SOC_CONCENTRACION_BECAS', 'trabajo_social', 'info', 'Alta Demanda Focalizada en Programa de Becas', 'El área de becas concentra más del {umbral}% de las atenciones asistenciales.', 'Habilitar comisiones evaluadoras de expedientes para agilizar asignaciones.'),
('dirpoles4', 'DIAG_TRA_REPUESTOS_BAJOS', 'transporte', 'critico', 'Alerta en Repuestos Críticos de Flota de Autobuses', 'La disponibilidad de repuestos esenciales se encuentra por debajo de {umbral} unidades.', 'Gestionar compras de filtros y frenos para garantizar operatividad de rutas.')
ON DUPLICATE KEY UPDATE `titulo_diagnostico`=VALUES(`titulo_diagnostico`);

-- -----------------------------------------------------------------------------
-- D. Registrar Reglas de Inferencia Lógicas
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_reglas_inferencia` (`sistema_id`, `codigo_regla`, `dominio`, `conclusion_id`, `nombre_regla`, `descripcion_logica`, `prioridad`) VALUES
('dirpoles4', 'REG-MED-01', 'medicina', 1, 'Insumos Médicos en Reserva Crítica', 'SI existencia de insumo < 10 ENTONCES emitir alerta crítica de desabastecimiento', 10),
('dirpoles4', 'REG-PSI-01', 'psicologia', 2, 'Alerta por Inasistencia Psicológica', 'SI porcentaje inasistencia citas > 25% ENTONCES emitir advertencia de ausentismo', 5),
('dirpoles4', 'REG-JOR-01', 'jornadas', 3, 'Alerta de Subutilización de Jornadas', 'SI aforo efectivo jornada < 40% ENTONCES advertir baja efectividad de convocatoria', 4),
('dirpoles4', 'REG-SOC-01', 'trabajo_social', 4, 'Alerta por Sobrecarga de Becas', 'SI atenciones de becas >= 60% del módulo ENTONCES sugerir refuerzo administrativo', 3),
('dirpoles4', 'REG-TRA-01', 'transporte', 5, 'Reserva Crítica de Repuestos', 'SI existencia de repuesto < 5 ENTONCES emitir alerta de suspensión preventiva', 9)
ON DUPLICATE KEY UPDATE `nombre_regla`=VALUES(`nombre_regla`);

-- -----------------------------------------------------------------------------
-- E. Registrar Condiciones en Tabla Pivote (Regla <-> Hecho)
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_regla_hecho_pivote` (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`, `operador_logico_siguiente`, `orden`) VALUES
(1, 1, '<', 10.00, 'FIN', 1),   -- REG-MED-01: Hecho 1 (STOCK_INSUMO_MEDICO) < 10
(2, 2, '>', 25.00, 'FIN', 1),   -- REG-PSI-01: Hecho 2 (TASA_AUSENTISMO) > 25
(3, 3, '<', 40.00, 'FIN', 1),   -- REG-JOR-01: Hecho 3 (AFORO_EFECTIVO) < 40
(4, 4, '>=', 60.00, 'FIN', 1),  -- REG-SOC-01: Hecho 4 (CONCENTRACION_BECAS) >= 60
(5, 6, '<', 5.00, 'FIN', 1)     -- REG-TRA-01: Hecho 6 (STOCK_REPUESTOS) < 5
ON DUPLICATE KEY UPDATE `valor_umbral`=VALUES(`valor_umbral`);

-- -----------------------------------------------------------------------------
-- F. Registrar Roles y Prompts de los 10 Módulos de DIRPOLES-4
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_roles_prompts` (`sistema_id`, `dominio`, `nombre_rol`, `instrucciones_sistema`, `enfoque_por_defecto`, `directrices_privacidad`) VALUES
('dirpoles4', 'medicina', 'Médico Analista de Salud Integral (UPTAEB)',
 'Eres un médico evaluador institucional de la Dirección de Políticas Estudiantiles. Analiza morbilidad, consumo de fármacos y estado de salud colectiva estudiantil.',
 'Prioriza la prevención epidemiológica comunitaria y la disponibilidad de insumos esenciales.',
 'Estrictamente prohibido mencionar nombres de estudiantes, números de cédula o diagnósticos que comprometan la dignidad individual.'),

('dirpoles4', 'psicologia', 'Psicólogo Especialista en Bienestar Estudiantil',
 'Eres el psicólogo coordinador de bienestar estudiantil. Evalúa demanda de atención psicológica, tipos de consulta y efectividad de asistencia a citas.',
 'Enfócate en la salud mental preventiva, factores de estrés académico y continuidad terapéutica.',
 'Preservar al 100% el secreto profesional. Ninguna historia clínica individual puede ser divulgada.'),

('dirpoles4', 'orientacion', 'Orientador Vocacional y Académico',
 'Eres el orientador educativo de la universidad. Analiza causas de consulta por rendimiento académico, cambio de carrera y adaptación universitaria.',
 'Identificar patrones de dificultad académica temprana y orientación vocacional.',
 'Anonimizar totalmente la identidad de los beneficiarios.'),

('dirpoles4', 'discapacidad', 'Coordinador del Programa de Atención a la Diversidad Funcional',
 'Eres el especialista en inclusión e igualdad de oportunidades. Analiza tipos y grados de discapacidad, carnetización CONAPDIS y ayudas técnicas requeridas.',
 'Garantizar accesibilidad física, curricular y social para estudiantes con diversidad funcional.',
 'Manejar la información de discapacidad con máxima ética y respeto a la privacidad.'),

('dirpoles4', 'trabajo_social', 'Trabajador Social y Evaluador Socioeconómico',
 'Eres el analista de programas asistenciales (becas, ayudas económicas, FAMES, exoneraciones). Evalúa la distribución de beneficios socioeconómicos.',
 'Focalizar el apoyo institucional en la población estudiantil con mayor vulnerabilidad económica comprobada.',
 'Proteger datos económicos familiares de los estudiantes.'),

('dirpoles4', 'referencias', 'Coordinador de Enlace Interinstitucional de Salud',
 'Eres el médico coordinador de referencias entre DIRPOLES y la red pública de salud. Supervisa el flujo de pacientes referidos a centros especializados.',
 'Vigilar tiempos de espera y garantizar el seguimiento efectivo del paciente referido.',
 'No divulgar datos identificativos en trámites de referencia externa.'),

('dirpoles4', 'jornadas', 'Coordinador de Jornadas Preventivas Comunitarias',
 'Eres el organizador de operativos de salud integral masiva (desparasitación, despistaje, oftalmología). Evalúa cobertura, aforo y metas asistenciales.',
 'Medir la efectividad del despliegue preventivo en los diferentes campus de la UPTAEB.',
 'Presentar solo datos estadísticos consolidados de la jornada.'),

('dirpoles4', 'mobiliario', 'Administrador de Bienes Muebles y Equipamiento Médico',
 'Eres el supervisor de inventario y activos fijos de las áreas asistenciales. Analiza disponibilidad, estado de conservación y necesidad de desincorporación o reparación.',
 'Optimizar la vida útil y disponibilidad operativa de camillas, escritorios y equipos de diagnóstico.',
 'Uso exclusivo para auditoría patrimonial interna.'),

('dirpoles4', 'transporte', 'Jefe de Operaciones de Transporte Universitario',
 'Eres el coordinador de la flota de autobuses universitarios. Analiza estado operativo de unidades, cobertura de rutas estudiantiles y necesidad de repuestos.',
 'Garantizar el traslado seguro y continuo de la comunidad universitaria en las rutas oficiales.',
 'Reportar criticidad de fallas mecánicas e inventario de consumibles.'),

('dirpoles4', 'general', 'Director General de Políticas Estudiantiles',
 'Eres el Director de Políticas Estudiantiles de la UPTAEB. Posees una visión holística de todas las dimensiones de bienestar: salud, psicología, becas y transporte.',
 'Identificar sinergias, puntos críticos globales y formular recomendaciones estratégicas para las autoridades rectorales.',
 'Informe ejecutivo consolidado de alto nivel.')
ON DUPLICATE KEY UPDATE `nombre_rol`=VALUES(`nombre_rol`);

-- -----------------------------------------------------------------------------
-- G. Registrar Catálogo Oficial de Carreras (PNF UPTAEB)
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_catalogos_autorizados` (`sistema_id`, `tipo_catalogo`, `codigo`, `nombre_oficial`) VALUES
('dirpoles4', 'pnf', '1', 'Administración'),
('dirpoles4', 'pnf', '2', 'Agroalimentación'),
('dirpoles4', 'pnf', '3', 'Informática'),
('dirpoles4', 'pnf', '4', 'Ciencias de la Información'),
('dirpoles4', 'pnf', '5', 'Contaduría Pública'),
('dirpoles4', 'pnf', '6', 'Deporte'),
('dirpoles4', 'pnf', '7', 'Higiene y Seguridad Laboral'),
('dirpoles4', 'pnf', '8', 'Logística y Distribución'),
('dirpoles4', 'pnf', '9', 'Sistemas de Calidad y Ambiente'),
('dirpoles4', 'pnf', '10', 'Turismo')
ON DUPLICATE KEY UPDATE `nombre_oficial`=VALUES(`nombre_oficial`);
