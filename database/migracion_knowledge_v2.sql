-- =============================================================================
-- MIGRACIÓN DE LA BASE DE CONOCIMIENTO: dirpoles_knowledge (v2)
-- Sistema DIRPOLES-IA — Arquitectura SBC multitenant
-- Motor: MariaDB 10.4+ / MySQL 8.0+
--
-- Objetivo:
--   1. Completar el conocimiento declarativo que el motor ETL consume:
--      roles, instrucciones, privacidad, catálogos, hechos, umbrales y mensajes.
--   2. Alinear los umbrales de la BD con el comportamiento real del motor.
--   3. Añadir las tablas de enfoques, directrices y plantillas de alertas.
--
-- Ejecución (usuario administrador, NO el usuario READ-ONLY del servicio):
--   mysql -u root -p < database/migracion_knowledge_v2.sql
--
-- El microservicio sigue siendo estrictamente READ-ONLY en tiempo de ejecución.
-- =============================================================================

USE `dirpoles_knowledge`;

-- -----------------------------------------------------------------------------
-- 0. Asegurar el tenant institucional (sin sobrescribir su API Key real)
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_sistemas` (`id`, `nombre`, `api_key`, `modo_acceso`, `activo`)
VALUES ('dirpoles4', 'DIRPOLES-4 Monolito Institucional (UPTAEB)',
        'CAMBIAR_EN_PRODUCCION', 'sql_pull', 1)
ON DUPLICATE KEY UPDATE
    `nombre` = VALUES(`nombre`),
    `modo_acceso` = VALUES(`modo_acceso`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 1. NUEVAS TABLAS DECLARATIVAS
-- -----------------------------------------------------------------------------

-- 1.1. Enfoque analítico por intención del informe.
CREATE TABLE IF NOT EXISTS `conocimiento_enfoques_intencion` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `intencion` VARCHAR(50) NOT NULL COMMENT 'resumen_ejecutivo, alertas_y_anomalias, ...',
    `enfoque` TEXT NOT NULL COMMENT 'Directriz de enfoque inyectada al prompt',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_enfoque_sistema_intencion` (`sistema_id`, `intencion`),
    CONSTRAINT `fk_enfoques_sistema` FOREIGN KEY (`sistema_id`)
        REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Enfoque analítico declarativo por intención';

-- 1.2. Directrices canónicas autorizadas para observaciones del usuario.
CREATE TABLE IF NOT EXISTS `conocimiento_directrices` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `clave` VARCHAR(120) NOT NULL COMMENT 'Clave canónica que puede enviar el consumidor',
    `directriz` TEXT NOT NULL COMMENT 'Texto autorizado que reemplaza la clave',
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_directriz_sistema_clave` (`sistema_id`, `clave`),
    CONSTRAINT `fk_directrices_sistema` FOREIGN KEY (`sistema_id`)
        REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Directrices canónicas autorizadas (sin texto libre)';

-- 1.3. Plantillas regex de alertas canónicas.
CREATE TABLE IF NOT EXISTS `conocimiento_plantillas_alertas` (
    `id` INT AUTO_INCREMENT NOT NULL,
    `sistema_id` VARCHAR(50) NOT NULL,
    `nivel` ENUM('info', 'advertencia', 'critico') NOT NULL,
    `patron_regex` VARCHAR(500) NOT NULL COMMENT 'Expresión regular anclada (^...$)',
    `descripcion` VARCHAR(200) NULL,
    `activo` TINYINT(1) NOT NULL DEFAULT 1,
    PRIMARY KEY (`id`),
    UNIQUE KEY `uk_plantilla_sistema_nivel_patron` (`sistema_id`, `nivel`, `patron_regex`),
    CONSTRAINT `fk_plantillas_sistema` FOREIGN KEY (`sistema_id`)
        REFERENCES `conocimiento_sistemas` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='Plantillas canónicas de validación de alertas';

-- -----------------------------------------------------------------------------
-- 2. ROLES, INSTRUCCIONES Y PRIVACIDAD (10 módulos)
--    Se alinean con el texto canónico del fallback para no cambiar el tono.
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_roles_prompts`
    (`sistema_id`, `dominio`, `nombre_rol`, `instrucciones_sistema`,
     `enfoque_por_defecto`, `directrices_privacidad`, `activo`)
VALUES
('dirpoles4', 'medicina',
 'Especialista en gestión de servicios médicos universitarios, morbilidad clínica y administración de inventario de insumos de salud.',
 'Eres un médico evaluador institucional de la Dirección de Políticas Estudiantiles. Analiza morbilidad, consumo de fármacos y estado de salud colectiva estudiantil.',
 'Prioriza la prevención epidemiológica comunitaria y la disponibilidad de insumos esenciales.',
 'Estrictamente prohibido mencionar nombres de estudiantes, números de cédula o diagnósticos que comprometan la dignidad individual.', 1),

('dirpoles4', 'psicologia',
 'Especialista en salud mental universitaria, morbilidad psicológica y gestión de agenda de atención clínica.',
 'Eres el psicólogo coordinador de bienestar estudiantil. Evalúa demanda de atención psicológica, tipos de consulta y efectividad de asistencia a citas.',
 'Enfócate en la salud mental preventiva, factores de estrés académico y continuidad terapéutica.',
 'Preservar al 100% el secreto profesional. Ninguna historia clínica individual puede ser divulgada.', 1),

('dirpoles4', 'orientacion',
 'Especialista en orientación educativa, psicopedagogía y desarrollo integral del estudiante universitario.',
 'Eres el orientador educativo de la universidad. Analiza causas de consulta por rendimiento académico, cambio de carrera y adaptación universitaria.',
 'Identificar patrones de dificultad académica temprana y orientación vocacional.',
 'Anonimizar totalmente la identidad de los beneficiarios.', 1),

('dirpoles4', 'discapacidad',
 'Especialista en políticas de inclusión universitaria, accesibilidad y atención a la diversidad funcional.',
 'Eres el especialista en inclusión e igualdad de oportunidades. Analiza tipos y grados de discapacidad, carnetización CONAPDIS y ayudas técnicas requeridas.',
 'Garantizar accesibilidad física, curricular y social para estudiantes con diversidad funcional.',
 'Manejar la información de discapacidad con máxima ética y respeto a la privacidad.', 1),

('dirpoles4', 'trabajo_social',
 'Especialista en trabajo social universitario, evaluación socioeconómica y programas de protección (Becas, Exoneraciones, FAMES y Gestión de Embarazo).',
 'Eres el analista de programas asistenciales (becas, ayudas económicas, FAMES, exoneraciones). Evalúa la distribución de beneficios socioeconómicos.',
 'Focalizar el apoyo institucional en la población estudiantil con mayor vulnerabilidad económica comprobada.',
 'Proteger datos económicos familiares de los estudiantes.', 1),

('dirpoles4', 'referencias',
 'Coordinador de la red de remisiones e interconsultas internas entre servicios de bienestar estudiantil.',
 'Eres el médico coordinador de referencias entre DIRPOLES y la red pública de salud. Supervisa el flujo de pacientes referidos a centros especializados.',
 'Vigilar tiempos de espera y garantizar el seguimiento efectivo del paciente referido.',
 'No divulgar datos identificativos en trámites de referencia externa.', 1),

('dirpoles4', 'jornadas',
 'Especialista en salud comunitaria, organización de jornadas asistenciales y prevención epidemiológica universitaria.',
 'Eres el organizador de operativos de salud integral masiva (desparasitación, despistaje, oftalmología). Evalúa cobertura, aforo y metas asistenciales.',
 'Medir la efectividad del despliegue preventivo en los diferentes campus de la UPTAEB.',
 'Presentar solo datos estadísticos consolidados de la jornada.', 1),

('dirpoles4', 'mobiliario',
 'Analista de gestión de bienes públicos, mobiliario e inventario de equipamiento institucional.',
 'Eres el supervisor de inventario y activos fijos de las áreas asistenciales. Analiza disponibilidad, estado de conservación y necesidad de desincorporación o reparación.',
 'Optimizar la vida útil y disponibilidad operativa de camillas, escritorios y equipos de diagnóstico.',
 'Uso exclusivo para auditoría patrimonial interna.', 1),

('dirpoles4', 'transporte',
 'Analista de gestión de flotas, logística de transporte universitario, rutas y mantenimiento vehicular.',
 'Eres el coordinador de la flota de autobuses universitarios. Analiza estado operativo de unidades, cobertura de rutas estudiantiles y necesidad de repuestos.',
 'Garantizar el traslado seguro y continuo de la comunidad universitaria en las rutas oficiales.',
 'Reportar criticidad de fallas mecánicas e inventario de consumibles.', 1),

('dirpoles4', 'general',
 'Analista Ejecutivo de Datos de la Dirección de Políticas Estudiantiles, con visión integral de salud, desarrollo social y logística universitaria.',
 'Eres el Director de Políticas Estudiantiles de la UPTAEB. Posees una visión holística de todas las dimensiones de bienestar: salud, psicología, becas y transporte.',
 'Identificar sinergias, puntos críticos globales y formular recomendaciones estratégicas para las autoridades rectorales.',
 'Informe ejecutivo consolidado de alto nivel.', 1)
ON DUPLICATE KEY UPDATE
    `nombre_rol` = VALUES(`nombre_rol`),
    `instrucciones_sistema` = VALUES(`instrucciones_sistema`),
    `enfoque_por_defecto` = VALUES(`enfoque_por_defecto`),
    `directrices_privacidad` = VALUES(`directrices_privacidad`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 3. ENFOQUES POR INTENCIÓN
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_enfoques_intencion` (`sistema_id`, `intencion`, `enfoque`, `activo`)
VALUES
('dirpoles4', 'resumen_ejecutivo',
 'Prioriza una visión panorámica: totales del periodo, distribuciones porcentuales y comparativas entre periodos.', 1),
('dirpoles4', 'alertas_y_anomalias',
 'Prioriza la detección de anomalías, picos de demanda, umbrales críticos, vencimientos y cualquier indicador que requiera atención inmediata.', 1),
('dirpoles4', 'tendencias_y_patrones',
 'Prioriza la evolución temporal de los datos, tendencias, estacionalidad, variaciones porcentuales mes a mes y patrones de comportamiento relevantes.', 1),
('dirpoles4', 'recomendaciones',
 'Prioriza recomendaciones operativas concretas, accionables y priorizadas para la toma de decisiones de la Dirección.', 1)
ON DUPLICATE KEY UPDATE
    `enfoque` = VALUES(`enfoque`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 4. CATÁLOGOS INSTITUCIONALES CERRADOS
--    Se reemplazan los catálogos de dirpoles4 para eliminar el formato antiguo
--    de PNF sin prefijo y unificar con la base de negocio.
-- -----------------------------------------------------------------------------
DELETE FROM `conocimiento_catalogos_autorizados` WHERE `sistema_id` = 'dirpoles4';

INSERT INTO `conocimiento_catalogos_autorizados`
    (`sistema_id`, `tipo_catalogo`, `codigo`, `nombre_oficial`, `activo`)
VALUES
-- PNF oficial (mismo formato que dirpoles_business.pnf.nombre_pnf)
('dirpoles4', 'pnf', '1',  'PNF Administración', 1),
('dirpoles4', 'pnf', '2',  'PNF Contaduría Pública', 1),
('dirpoles4', 'pnf', '3',  'PNF Informática', 1),
('dirpoles4', 'pnf', '4',  'PNF Higiene y Seguridad Laboral', 1),
('dirpoles4', 'pnf', '5',  'PNF Deporte', 1),
('dirpoles4', 'pnf', '6',  'PNF Turismo', 1),
('dirpoles4', 'pnf', '7',  'PNF Ciencias de la Información', 1),
('dirpoles4', 'pnf', '8',  'PNF Sistemas de Calidad y Ambiente', 1),
('dirpoles4', 'pnf', '9',  'PNF Agroalimentación', 1),
('dirpoles4', 'pnf', '10', 'PNF Distribución y Logística', 1),
('dirpoles4', 'pnf', '11', 'PNF Materiales Industriales', 1),
('dirpoles4', 'pnf', '12', 'PNF Procesos Químicos', 1),
('dirpoles4', 'pnf', '13', 'PNF Sistemas informáticos', 1),

-- Género
('dirpoles4', 'genero', 'M', 'Masculino', 1),
('dirpoles4', 'genero', 'F', 'Femenino', 1),
('dirpoles4', 'genero', 'NE', 'No especificado', 1),

-- Áreas generales
('dirpoles4', 'area', 'BECAS', 'Becas', 1),
('dirpoles4', 'area', 'EXONERACION', 'Exoneración', 1),
('dirpoles4', 'area', 'FAMES', 'FAMES', 1),
('dirpoles4', 'area', 'MEDICINA', 'Medicina', 1),
('dirpoles4', 'area', 'ORIENTACION', 'Orientación', 1),
('dirpoles4', 'area', 'DISCAPACIDAD', 'Discapacidad', 1),
('dirpoles4', 'area', 'PSICOLOGIA', 'Psicología', 1),

-- Submódulos de trabajo social
('dirpoles4', 'submodulo', 'BECAS', 'Becas', 1),
('dirpoles4', 'submodulo', 'EXONERACION', 'Exoneración', 1),
('dirpoles4', 'submodulo', 'FAMES', 'FAMES', 1),
('dirpoles4', 'submodulo', 'GESTION_EMBARAZO', 'Gestión Embarazo', 1),

-- Tipos de consulta psicológica
('dirpoles4', 'tipo_consulta_psicologica', 'DIAGNOSTICO', 'Diagnóstico', 1),
('dirpoles4', 'tipo_consulta_psicologica', 'RETIRO_TEMPORAL', 'Retiro temporal', 1),
('dirpoles4', 'tipo_consulta_psicologica', 'CAMBIO_CARRERA', 'Cambio de carrera', 1),

-- Estados de cita
('dirpoles4', 'estado_cita', 'PENDIENTE', 'Pendiente', 1),
('dirpoles4', 'estado_cita', 'CONFIRMADA', 'Confirmada', 1),
('dirpoles4', 'estado_cita', 'ATENDIDA', 'Atendida', 1),
('dirpoles4', 'estado_cita', 'CANCELADA', 'Cancelada', 1),
('dirpoles4', 'estado_cita', 'NO_ASISTIO', 'No asistió', 1),

-- Tipos de bien
('dirpoles4', 'tipo_bien', 'MOBILIARIO', 'Mobiliario', 1),
('dirpoles4', 'tipo_bien', 'EQUIPO', 'Equipo', 1),

-- Grados de discapacidad
('dirpoles4', 'grado_discapacidad', 'LEVE', 'Leve', 1),
('dirpoles4', 'grado_discapacidad', 'MODERADO', 'Moderado', 1),
('dirpoles4', 'grado_discapacidad', 'GRAVE', 'Grave', 1),

-- Tipos de discapacidad
('dirpoles4', 'tipo_discapacidad', 'FISICA', 'Física', 1),
('dirpoles4', 'tipo_discapacidad', 'SENSORIAL', 'Sensorial', 1),
('dirpoles4', 'tipo_discapacidad', 'INTELECTUAL', 'Intelectual', 1),
('dirpoles4', 'tipo_discapacidad', 'MULTIPLE', 'Múltiple', 1),
('dirpoles4', 'tipo_discapacidad', 'OTRO', 'Otro', 1),

-- Tipos de vehículo
('dirpoles4', 'tipo_vehiculo', 'AUTOBUS', 'Autobús', 1),
('dirpoles4', 'tipo_vehiculo', 'CAMIONETA', 'Camioneta', 1),
('dirpoles4', 'tipo_vehiculo', 'AUTOMOVIL', 'Automóvil', 1),

-- Estados de referencia
('dirpoles4', 'estado_referencia', 'PENDIENTE', 'Pendiente', 1),
('dirpoles4', 'estado_referencia', 'ACEPTADA', 'Aceptada', 1),
('dirpoles4', 'estado_referencia', 'RECHAZADA', 'Rechazada', 1),

-- Estados de jornada
('dirpoles4', 'estado_jornada', 'ACTIVA', 'Activa', 1),
('dirpoles4', 'estado_jornada', 'CANCELADA', 'Cancelada', 1),
('dirpoles4', 'estado_jornada', 'FINALIZADA', 'Finalizada', 1),

-- Estados de inventario
('dirpoles4', 'estado_inventario', 'ACTIVO', 'Activo', 1),
('dirpoles4', 'estado_inventario', 'INACTIVO', 'Inactivo', 1);

-- -----------------------------------------------------------------------------
-- 5. HECHOS OBSERVABLES (variables que el motor mide)
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_hechos_sintomas`
    (`sistema_id`, `codigo_hecho`, `dominio`, `nombre`, `descripcion`,
     `tipo_dato`, `unidad_medida`, `activo`)
VALUES
('dirpoles4', 'CONCENTRACION_AREA_GENERAL', 'general',
 'Concentración de Atenciones por Área',
 'Porcentaje de atenciones concentradas en la principal área de bienestar.',
 'porcentaje', '%', 1),
('dirpoles4', 'STOCK_INSUMO_MEDICO', 'medicina',
 'Nivel de Existencia de Insumo Médico',
 'Cantidad física disponible del insumo en el almacén de salud.',
 'entero', 'unidades', 1),
('dirpoles4', 'DIAS_VENCIMIENTO_VENCIDO', 'medicina',
 'Días de Vencimiento de Insumo (Vencido)',
 'Umbral de días negativos que marca un insumo como vencido.',
 'entero', 'días', 1),
('dirpoles4', 'DIAS_VENCIMIENTO_PROXIMO', 'medicina',
 'Días de Vencimiento Próximo de Insumo',
 'Días de anticipación para marcar un insumo como próximo a vencer.',
 'entero', 'días', 1),
('dirpoles4', 'VARIACION_CONSULTAS_MEDICAS', 'medicina',
 'Variación Mensual de Consultas Médicas',
 'Porcentaje de aumento de consultas médicas respecto al mes anterior.',
 'porcentaje', '%', 1),
('dirpoles4', 'TASA_AUSENTISMO_CITA_PSI', 'psicologia',
 'Tasa de Inasistencia a Citas Psicológicas',
 'Porcentaje de citas programadas que terminan en inasistencia.',
 'porcentaje', '%', 1),
('dirpoles4', 'CITAS_PENDIENTES_PSI', 'psicologia',
 'Citas Psicológicas Pendientes',
 'Cantidad de citas en estado Pendiente sin atender.',
 'entero', 'citas', 1),
('dirpoles4', 'CONCENTRACION_DIAGNOSTICO_PSI', 'psicologia',
 'Concentración de Morbilidad Psicológica',
 'Porcentaje de la principal condición diagnóstica en la morbilidad psicológica.',
 'porcentaje', '%', 1),
('dirpoles4', 'CONCENTRACION_SOLICITUD_BECA', 'trabajo_social',
 'Concentración de Trámites en Submódulo Becas',
 'Proporción de solicitudes de becas respecto al total de bienestar.',
 'porcentaje', '%', 1),
('dirpoles4', 'CASOS_DISCAPACIDAD_GRAVE', 'discapacidad',
 'Casos de Discapacidad con Grado Grave',
 'Cantidad de casos registrados con grado Grave.',
 'entero', 'casos', 1),
('dirpoles4', 'REGISTROS_SIN_CARNET', 'discapacidad',
 'Registros sin Carnet de Discapacidad',
 'Cantidad de registros de discapacidad sin carnet asociado.',
 'entero', 'registros', 1),
('dirpoles4', 'REFERENCIAS_PENDIENTES', 'referencias',
 'Referencias Pendientes de Resolución',
 'Cantidad de referencias médicas pendientes de resolución.',
 'entero', 'referencias', 1),
('dirpoles4', 'OCUPACION_JORNADA', 'jornadas',
 'Ocupación de Jornada de Salud',
 'Porcentaje de ocupación del aforo planificado para una jornada.',
 'porcentaje', '%', 1),
('dirpoles4', 'JORNADAS_SIN_FINALIZAR', 'jornadas',
 'Jornadas sin Finalizar',
 'Cantidad de jornadas que aún no están en estatus Finalizada.',
 'entero', 'jornadas', 1),
('dirpoles4', 'BIENES_INACTIVOS', 'mobiliario',
 'Bienes Inactivos en Inventario',
 'Cantidad de bienes marcados como Inactivo en el inventario.',
 'entero', 'bienes', 1),
('dirpoles4', 'STOCK_REPUESTOS_TRANSPORTE', 'transporte',
 'Existencia de Repuestos Automotrices Críticos',
 'Cantidad en inventario de repuestos para unidades de transporte.',
 'entero', 'unidades', 1),
('dirpoles4', 'VEHICULOS_MANTENIMIENTO', 'transporte',
 'Vehículos en Mantenimiento',
 'Cantidad de vehículos de la flota en estado Mantenimiento.',
 'entero', 'vehículos', 1)
ON DUPLICATE KEY UPDATE
    `dominio` = VALUES(`dominio`),
    `nombre` = VALUES(`nombre`),
    `descripcion` = VALUES(`descripcion`),
    `tipo_dato` = VALUES(`tipo_dato`),
    `unidad_medida` = VALUES(`unidad_medida`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 6. CONCLUSIONES, DIAGNÓSTICOS Y PLANTILLAS DE MENSAJES
--    Las plantillas son exactamente las que emite el motor ETL.
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_conclusiones`
    (`sistema_id`, `codigo_conclusion`, `dominio`, `nivel_severidad`,
     `titulo_diagnostico`, `plantilla_mensaje`, `recomendacion_sugerida`, `activo`)
VALUES
('dirpoles4', 'ALERTA_TRUNCAMIENTO', 'general', 'advertencia',
 'Muestra Analítica Truncada por Límite de Filas',
 'La colección ''{coleccion}'' tiene {total} registros pero solo se analizaron {analizados} por el límite de filas configurado.',
 'Ampliar el límite de registros o segmentar el periodo para analizar la totalidad de la colección.', 1),

('dirpoles4', 'ALERTA_SIN_REGISTROS', 'general', 'info',
 'Sin Registros para los Filtros Aplicados',
 'No se encontraron registros que cumplan los filtros seleccionados.',
 'Verificar el rango de fechas y los filtros aplicados antes de concluir una ausencia de demanda.', 1),

('dirpoles4', 'ALERTA_AREA_CONCENTRADA', 'general', 'advertencia',
 'Concentración de Atenciones en un Área',
 'El área ''{valor}'' concentra el {porcentaje}% de las atenciones del periodo.',
 'Revisar la distribución de la demanda y reforzar las áreas con menor cobertura.', 1),

('dirpoles4', 'ALERTA_INSUMOS_VENCIDOS', 'medicina', 'critico',
 'Insumos Médicos Vencidos',
 '{cantidad} insumo(s) con fecha de vencimiento vencida.',
 'Retirar inmediatamente los insumos vencidos y registrar la novedad en el almacén.', 1),

('dirpoles4', 'ALERTA_INSUMOS_POR_VENCER', 'medicina', 'advertencia',
 'Insumos Próximos a Vencer',
 '{cantidad} insumo(s) vencen en los próximos 30 días.',
 'Priorizar el consumo de los insumos próximos a vencer y reprogramar compras.', 1),

('dirpoles4', 'ALERTA_INSUMOS_STOCK_CRITICO', 'medicina', 'critico',
 'Riesgo de Desabastecimiento de Insumos Médicos',
 '{cantidad} insumo(s) por debajo del umbral crítico ({umbral} unidades).',
 'Tramitar solicitud prioritaria de reabastecimiento ante almacén central.', 1),

('dirpoles4', 'ALERTA_CONSULTAS_AUMENTO', 'medicina', 'advertencia',
 'Aumento de la Demanda de Consultas Médicas',
 'Las consultas médicas aumentaron un {variacion}% respecto al mes anterior.',
 'Evaluar refuerzo de personal médico y disponibilidad de insumos para el próximo periodo.', 1),

('dirpoles4', 'ALERTA_CITAS_PENDIENTES', 'psicologia', 'advertencia',
 'Citas Psicológicas Pendientes sin Atender',
 '{cantidad} cita(s) en estado Pendiente sin atender.',
 'Reprogramar las citas pendientes y reforzar la confirmación previa.', 1),

('dirpoles4', 'ALERTA_CITAS_NO_ASISTIO', 'psicologia', 'critico',
 'Deserción Significativa en Consultas de Psicología',
 'El {porcentaje}% de las citas terminó en ''No asistió''.',
 'Implementar recordatorio de citas vía mensajería y revisar turnos vespertinos.', 1),

('dirpoles4', 'ALERTA_MORBILIDAD_CONCENTRADA', 'psicologia', 'advertencia',
 'Concentración de una Condición Diagnóstica',
 'Una condición diagnóstica concentra el {porcentaje}% de la morbilidad psicológica del periodo.',
 'Diseñar una intervención preventiva específica para la condición predominante.', 1),

('dirpoles4', 'ALERTA_BECAS_CONCENTRADAS', 'trabajo_social', 'advertencia',
 'Alta Demanda Focalizada en Programa de Becas',
 'El área ''Becas'' concentra el {porcentaje}% de las atenciones del periodo.',
 'Habilitar comisiones evaluadoras de expedientes para agilizar asignaciones.', 1),

('dirpoles4', 'ALERTA_DISCAPACIDAD_GRAVE', 'discapacidad', 'advertencia',
 'Casos de Discapacidad con Grado Grave',
 '{cantidad} caso(s) de discapacidad con grado Grave.',
 'Priorizar la atención y el acompañamiento de los casos con grado Grave.', 1),

('dirpoles4', 'ALERTA_SIN_CARNET', 'discapacidad', 'advertencia',
 'Registros sin Carnet de Discapacidad',
 '{cantidad} registro(s) sin carnet de discapacidad asociado.',
 'Iniciar el trámite de carnetización ante CONAPDIS para los registros pendientes.', 1),

('dirpoles4', 'ALERTA_REFERENCIAS_PENDIENTES', 'referencias', 'advertencia',
 'Referencias Pendientes de Resolución',
 '{cantidad} referencia(s) pendientes de resolución ({porcentaje}% del total).',
 'Gestionar el seguimiento con la red de salud para reducir los tiempos de espera.', 1),

('dirpoles4', 'ALERTA_JORNADAS_AFORO', 'jornadas', 'advertencia',
 'Jornadas con Aforo Completo o Sobrecupo',
 '{cantidad} jornada(s) alcanzaron o superaron el 100% del aforo.',
 'Revisar la capacidad planificada y prever refuerzos para futuras jornadas.', 1),

('dirpoles4', 'ALERTA_JORNADAS_SIN_FINALIZAR', 'jornadas', 'info',
 'Jornadas Pendientes de Cierre',
 '{cantidad} jornada(s) aún no están en estatus Finalizada.',
 'Solicitar el cierre administrativo de las jornadas para consolidar los indicadores.', 1),

('dirpoles4', 'ALERTA_BIENES_INACTIVOS', 'mobiliario', 'info',
 'Bienes Inactivos en el Inventario',
 '{cantidad} bien(es) marcados como Inactivo en el inventario.',
 'Evaluar la reparación, reasignación o desincorporación de los bienes inactivos.', 1),

('dirpoles4', 'ALERTA_VEHICULOS_MANTENIMIENTO', 'transporte', 'advertencia',
 'Vehículos de la Flota en Mantenimiento',
 '{cantidad} vehículo(s) en estado Mantenimiento.',
 'Coordinar el mantenimiento preventivo y verificar la disponibilidad de repuestos.', 1),

('dirpoles4', 'ALERTA_REPUESTOS_BAJO_STOCK', 'transporte', 'critico',
 'Reserva Crítica de Repuestos',
 '{cantidad} repuesto(s) con cantidad menor a {umbral} unidades.',
 'Gestionar compras de filtros y frenos para garantizar la operatividad de las rutas.', 1)
ON DUPLICATE KEY UPDATE
    `dominio` = VALUES(`dominio`),
    `nivel_severidad` = VALUES(`nivel_severidad`),
    `titulo_diagnostico` = VALUES(`titulo_diagnostico`),
    `plantilla_mensaje` = VALUES(`plantilla_mensaje`),
    `recomendacion_sugerida` = VALUES(`recomendacion_sugerida`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 7. REGLAS DE INFERENCIA Y UMBRALES
--    Se reseedan las reglas de dirpoles4 para que la BD sea la única fuente
--    de verdad de los umbrales que consume el ETL.
-- -----------------------------------------------------------------------------
DELETE FROM `conocimiento_regla_hecho_pivote`
WHERE `regla_id` IN (
    SELECT `id` FROM `conocimiento_reglas_inferencia` WHERE `sistema_id` = 'dirpoles4'
);
DELETE FROM `conocimiento_reglas_inferencia` WHERE `sistema_id` = 'dirpoles4';

INSERT INTO `conocimiento_reglas_inferencia`
    (`sistema_id`, `codigo_regla`, `dominio`, `conclusion_id`, `nombre_regla`,
     `descripcion_logica`, `prioridad`, `activa`)
VALUES
('dirpoles4', 'REG-GEN-01', 'general',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_AREA_CONCENTRADA'),
 'Concentración de Atenciones por Área',
 'SI concentración del área principal >= 40% ENTONCES advertir concentración de demanda', 5, 1),

('dirpoles4', 'REG-MED-01', 'medicina',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_INSUMOS_STOCK_CRITICO'),
 'Insumos Médicos en Reserva Crítica',
 'SI existencia de insumo < 10 ENTONCES emitir alerta crítica de desabastecimiento', 10, 1),

('dirpoles4', 'REG-MED-02', 'medicina',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_INSUMOS_VENCIDOS'),
 'Insumos Médicos Vencidos',
 'SI días hasta vencimiento < 0 ENTONCES emitir alerta crítica de insumo vencido', 9, 1),

('dirpoles4', 'REG-MED-03', 'medicina',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_INSUMOS_POR_VENCER'),
 'Insumos Próximos a Vencer',
 'SI días hasta vencimiento <= 30 ENTONCES advertir vencimiento próximo', 7, 1),

('dirpoles4', 'REG-MED-04', 'medicina',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_CONSULTAS_AUMENTO'),
 'Aumento de la Demanda de Consultas Médicas',
 'SI variación mensual de consultas >= 25% ENTONCES advertir aumento de demanda', 5, 1),

('dirpoles4', 'REG-PSI-01', 'psicologia',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_CITAS_NO_ASISTIO'),
 'Alerta por Inasistencia Psicológica',
 'SI porcentaje de inasistencia a citas >= 15% ENTONCES emitir alerta crítica de ausentismo', 10, 1),

('dirpoles4', 'REG-PSI-02', 'psicologia',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_CITAS_PENDIENTES'),
 'Citas Psicológicas Pendientes',
 'SI citas pendientes > 0 ENTONCES advertir citas sin atender', 6, 1),

('dirpoles4', 'REG-PSI-03', 'psicologia',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_MORBILIDAD_CONCENTRADA'),
 'Concentración de Morbilidad Psicológica',
 'SI concentración de la principal condición diagnóstica >= 30% ENTONCES advertir concentración', 5, 1),

('dirpoles4', 'REG-SOC-01', 'trabajo_social',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_BECAS_CONCENTRADAS'),
 'Alerta por Sobrecarga de Becas',
 'SI concentración de Becas >= 60% del módulo ENTONCES sugerir refuerzo administrativo', 3, 1),

('dirpoles4', 'REG-DIS-01', 'discapacidad',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_DISCAPACIDAD_GRAVE'),
 'Casos de Discapacidad Grave',
 'SI casos con grado Grave > 0 ENTONCES advertir priorización de atención', 5, 1),

('dirpoles4', 'REG-DIS-02', 'discapacidad',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_SIN_CARNET'),
 'Registros sin Carnet de Discapacidad',
 'SI registros sin carnet > 0 ENTONCES advertir carnetización pendiente', 4, 1),

('dirpoles4', 'REG-REF-01', 'referencias',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_REFERENCIAS_PENDIENTES'),
 'Referencias Pendientes de Resolución',
 'SI referencias pendientes > 0 ENTONCES advertir seguimiento pendiente', 5, 1),

('dirpoles4', 'REG-JOR-01', 'jornadas',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_JORNADAS_AFORO'),
 'Jornadas con Aforo Completo o Sobrecupo',
 'SI ocupación de jornada >= 100% ENTONCES advertir aforo completo', 4, 1),

('dirpoles4', 'REG-JOR-02', 'jornadas',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_JORNADAS_SIN_FINALIZAR'),
 'Jornadas Pendientes de Cierre',
 'SI jornadas sin finalizar > 0 ENTONCES informar cierre pendiente', 2, 1),

('dirpoles4', 'REG-MOB-01', 'mobiliario',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_BIENES_INACTIVOS'),
 'Bienes Inactivos en Inventario',
 'SI bienes inactivos > 0 ENTONCES informar inventario inactivo', 2, 1),

('dirpoles4', 'REG-TRA-01', 'transporte',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_REPUESTOS_BAJO_STOCK'),
 'Reserva Crítica de Repuestos',
 'SI existencia de repuesto < 5 ENTONCES emitir alerta de suspensión preventiva', 9, 1),

('dirpoles4', 'REG-TRA-02', 'transporte',
 (SELECT `id` FROM `conocimiento_conclusiones` WHERE `sistema_id`='dirpoles4' AND `codigo_conclusion`='ALERTA_VEHICULOS_MANTENIMIENTO'),
 'Vehículos en Mantenimiento',
 'SI vehículos en mantenimiento > 0 ENTONCES advertir disponibilidad de flota', 4, 1);

-- 7.1. Condiciones (tabla pivote). Cada regla tiene una condición numérica.
INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 40.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'CONCENTRACION_AREA_GENERAL'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-GEN-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '<', 10.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'STOCK_INSUMO_MEDICO'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-MED-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '<', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'DIAS_VENCIMIENTO_VENCIDO'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-MED-02';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '<=', 30.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'DIAS_VENCIMIENTO_PROXIMO'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-MED-03';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 25.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'VARIACION_CONSULTAS_MEDICAS'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-MED-04';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 15.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'TASA_AUSENTISMO_CITA_PSI'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-PSI-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'CITAS_PENDIENTES_PSI'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-PSI-02';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 30.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'CONCENTRACION_DIAGNOSTICO_PSI'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-PSI-03';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 60.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'CONCENTRACION_SOLICITUD_BECA'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-SOC-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'CASOS_DISCAPACIDAD_GRAVE'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-DIS-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'REGISTROS_SIN_CARNET'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-DIS-02';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'REFERENCIAS_PENDIENTES'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-REF-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>=', 100.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'OCUPACION_JORNADA'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-JOR-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'JORNADAS_SIN_FINALIZAR'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-JOR-02';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'BIENES_INACTIVOS'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-MOB-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '<', 5.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'STOCK_REPUESTOS_TRANSPORTE'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-TRA-01';

INSERT INTO `conocimiento_regla_hecho_pivote`
    (`regla_id`, `hecho_id`, `operador_comparacion`, `valor_umbral`,
     `operador_logico_siguiente`, `orden`)
SELECT r.`id`, h.`id`, '>', 0.00, 'FIN', 1
FROM `conocimiento_reglas_inferencia` r
JOIN `conocimiento_hechos_sintomas` h
  ON h.`sistema_id` = r.`sistema_id` AND h.`codigo_hecho` = 'VEHICULOS_MANTENIMIENTO'
WHERE r.`sistema_id`='dirpoles4' AND r.`codigo_regla`='REG-TRA-02';

-- -----------------------------------------------------------------------------
-- 8. DIRECTRICES CANÓNICAS (opcionales; el texto libre nunca se transmite)
-- -----------------------------------------------------------------------------
INSERT INTO `conocimiento_directrices` (`sistema_id`, `clave`, `directriz`, `activo`)
VALUES
('dirpoles4', 'priorizar_alertas_criticas',
 'Prioriza las alertas de nivel crítico y los riesgos operativos inmediatos.', 1),
('dirpoles4', 'enfocar_prevencion',
 'Enfatiza recomendaciones preventivas y de seguimiento comunitario.', 1),
('dirpoles4', 'solicitar_recomendaciones',
 'Concentra el informe en recomendaciones operativas priorizadas para la Dirección.', 1)
ON DUPLICATE KEY UPDATE
    `directriz` = VALUES(`directriz`),
    `activo` = VALUES(`activo`);

-- -----------------------------------------------------------------------------
-- 9. PLANTILLAS CANÓNICAS DE ALERTAS (validación de salida hacia el LLM)
--    Se usan clases de caracteres ([0-9], [.], [(], [)]) para evitar problemas
--    de escape de backslashes entre MySQL y Python.
-- -----------------------------------------------------------------------------
DELETE FROM `conocimiento_plantillas_alertas` WHERE `sistema_id` = 'dirpoles4';

INSERT INTO `conocimiento_plantillas_alertas`
    (`sistema_id`, `nivel`, `patron_regex`, `descripcion`, `activo`)
VALUES
('dirpoles4', 'info',
 '^No se encontraron registros que cumplan los filtros seleccionados[.]$',
 'Dataset vacío para los filtros aplicados', 1),

('dirpoles4', 'advertencia',
 '^La colección ''(consultas|insumos|atenciones|casos|remisiones|jornadas|bienes|vehiculos|rutas|proveedores|repuestos|asignaciones|mantenimientos)'' tiene [0-9]+ registros pero solo se analizaron [0-9]+ por el límite de filas configurado[.]$',
 'Truncamiento de muestra por límite de filas', 1),

('dirpoles4', 'critico',
 '^[0-9]+ insumo[(]s[)] con fecha de vencimiento vencida[.]$',
 'Insumos vencidos', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ insumo[(]s[)] vencen en los próximos 30 días[.]$',
 'Insumos próximos a vencer', 1),

('dirpoles4', 'critico',
 '^[0-9]+ insumo[(]s[)] por debajo del umbral crítico [(][0-9]+ unidades[)][.]$',
 'Stock crítico de insumos', 1),

('dirpoles4', 'advertencia',
 '^El área ''(Becas|Exoneración|FAMES|Medicina|Orientación|Discapacidad|Psicología)'' concentra el [0-9]+(?:[.][0-9]+)?% de las atenciones del periodo[.]$',
 'Concentración de atenciones por área', 1),

('dirpoles4', 'advertencia',
 '^Las consultas médicas aumentaron un [0-9]+(?:[.][0-9]+)?% respecto al mes anterior[.]$',
 'Aumento mensual de consultas médicas', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ cita[(]s[)] en estado Pendiente sin atender[.]$',
 'Citas pendientes', 1),

('dirpoles4', 'critico',
 '^El [0-9]+(?:[.][0-9]+)?% de las citas terminó en ''No asistió''[.]$',
 'Inasistencia a citas psicológicas', 1),

('dirpoles4', 'advertencia',
 '^Una condición diagnóstica concentra el [0-9]+(?:[.][0-9]+)?% de la morbilidad psicológica del periodo[.]$',
 'Concentración de morbilidad psicológica', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ caso[(]s[)] de discapacidad con grado Grave[.]$',
 'Casos de discapacidad grave', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ registro[(]s[)] sin carnet de discapacidad asociado[.]$',
 'Registros sin carnet de discapacidad', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ referencia[(]s[)] pendientes de resolución [(][0-9]+(?:[.][0-9]+)?% del total[)][.]$',
 'Referencias pendientes', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ jornada[(]s[)] alcanzaron o superaron el 100% del aforo[.]$',
 'Jornadas con aforo completo', 1),

('dirpoles4', 'info',
 '^[0-9]+ jornada[(]s[)] aún no están en estatus Finalizada[.]$',
 'Jornadas sin finalizar', 1),

('dirpoles4', 'info',
 '^[0-9]+ bien[(]es[)] marcados como Inactivo en el inventario[.]$',
 'Bienes inactivos', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ vehículo[(]s[)] en estado Mantenimiento[.]$',
 'Vehículos en mantenimiento', 1),

('dirpoles4', 'critico',
 '^[0-9]+ repuesto[(]s[)] con cantidad menor a [0-9]+ unidades[.]$',
 'Repuestos en stock crítico', 1),

-- Cierres sintéticos utilizados por la suite histórica de pruebas
('dirpoles4', 'critico',
 '^Stock de insumos en nivel crítico [(]< [0-9]+[)][.]$',
 'Cierre sintético de stock crítico', 1),

('dirpoles4', 'critico',
 '^[0-9]+ insumos vencidos[.]$',
 'Cierre sintético de insumos vencidos', 1),

('dirpoles4', 'advertencia',
 '^[0-9]+ insumos por vencer[.]$',
 'Cierre sintético de insumos por vencer', 1),

('dirpoles4', 'advertencia',
 '^Alerta legítima de inasistencia$',
 'Cierre sintético de inasistencia', 1),

('dirpoles4', 'info',
 '^Alerta analítica sin PII[.]$',
 'Cierre sintético sin PII', 1);

-- -----------------------------------------------------------------------------
-- 10. VERIFICACIÓN RÁPIDA (opcional)
-- -----------------------------------------------------------------------------
-- SELECT tipo_catalogo, COUNT(*) FROM conocimiento_catalogos_autorizados
--   WHERE sistema_id='dirpoles4' GROUP BY tipo_catalogo;
-- SELECT codigo_regla, valor_umbral FROM conocimiento_reglas_inferencia r
--   JOIN conocimiento_regla_hecho_pivote p ON p.regla_id=r.id
--   WHERE r.sistema_id='dirpoles4' ORDER BY r.prioridad DESC;
