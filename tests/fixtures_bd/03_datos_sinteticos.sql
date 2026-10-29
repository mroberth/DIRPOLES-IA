-- ==============================================================================
-- FIXTURES CON DATOS ESTRICTAMENTE SINTÉTICOS PARA PRUEBAS DE INTEGRACIÓN
-- ==============================================================================
-- IMPORTANTE:
-- Este archivo NO CONTIENE datos personales reales, cédulas operativas, historias
-- clínicas, credenciales de producción ni registros extraídos de volcados institucionales.
-- Todos los datos son entidades ficticias para validar las consultas de los 10 módulos.
-- ==============================================================================

USE `dirpoles_security_test`;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Esquema de Seguridad: Tipos y Empleados Sintéticos
INSERT INTO `tipo_empleado` (`id_tipo_emp`, `tipo`, `id_servicios`, `estatus`, `fecha_creacion`) VALUES
(1, 'Médico', 1, 1, '2026-01-01'),
(2, 'Psicólogo', 2, 1, '2026-01-01'),
(3, 'Orientador', 3, 1, '2026-01-01');

INSERT INTO `empleado` (`id_empleado`, `nombre`, `apellido`, `tipo_cedula`, `cedula`, `correo`, `telefono`, `id_tipo_empleado`, `fecha_nacimiento`, `direccion`, `clave`, `estatus`, `fecha_creacion`) VALUES
(17, 'Médico', 'Sintético', 'V', '00000017', 'medico.test@uptaeb.edu.ve', '04120000017', 1, '1985-05-15', 'Barquisimeto', 'hash', 1, '2026-01-01'),
(1, 'Psicólogo', 'Sintético', 'V', '00000001', 'psicologo.test@uptaeb.edu.ve', '04120000001', 2, '1988-08-20', 'Barquisimeto', 'hash', 1, '2026-01-01');

USE `dirpoles_business_test`;

-- 2. Catálogo Oficial de PNF Institucional (13 registros oficiales de UPTAEB)
INSERT INTO `pnf` (`id_pnf`, `nombre_pnf`, `estatus`, `fecha_creacion`) VALUES
(1, 'PNF Administración', 1, '2024-11-12'),
(2, 'PNF Contaduría Pública', 1, '2024-11-12'),
(3, 'PNF Informática', 1, '2024-11-12'),
(4, 'PNF Higiene y Seguridad Laboral', 1, '2024-11-12'),
(5, 'PNF Deporte', 1, '2024-11-12'),
(6, 'PNF Turismo', 1, '2024-11-12'),
(7, 'PNF Ciencias de la Información', 1, '2024-11-12'),
(8, 'PNF Sistemas de Calidad y Ambiente', 1, '2024-11-12'),
(9, 'PNF Agroalimentación', 1, '2024-11-12'),
(10, 'PNF Distribución y Logística', 1, '2024-11-12'),
(11, 'PNF Materiales Industriales', 1, '2024-11-26'),
(12, 'PNF Procesos Químicos', 1, '2024-11-26'),
(13, 'PNF Sistemas informáticos', 0, '2026-02-02');

-- 3. Catálogo de Servicios
INSERT INTO `servicio` (`id_servicios`, `nombre_serv`, `estatus`, `fecha_creacion`) VALUES
(1, 'Medicina', 1, '2026-01-01'),
(2, 'Psicología', 1, '2026-01-01'),
(3, 'Orientación', 1, '2026-01-01'),
(4, 'Discapacidad', 1, '2026-01-01'),
(5, 'Trabajo Social', 1, '2026-01-01');

-- 4. Catálogo de Estados de Cita
INSERT INTO `estado_cita` (`id_estado`, `nombre`, `descripcion`, `es_activo`, `fecha_creacion`) VALUES
(1, 'Pendiente', 'Cita pendiente', 1, '2026-01-01 00:00:00'),
(2, 'Confirmada', 'Cita confirmada', 1, '2026-01-01 00:00:00'),
(3, 'Atendida', 'Cita atendida', 1, '2026-01-01 00:00:00'),
(4, 'Cancelada', 'Cita cancelada', 1, '2026-01-01 00:00:00'),
(5, 'No asistió', 'Beneficiario no asistió', 1, '2026-01-01 00:00:00');

-- 5. Beneficiarios y Solicitudes Sintéticas
INSERT INTO `beneficiario` (`id_beneficiario`, `id_pnf`, `seccion`, `nombres`, `apellidos`, `tipo_cedula`, `cedula`, `fecha_nac`, `telefono`, `correo`, `genero`, `direccion`, `estatus`, `fecha_creacion`) VALUES
(1, 3, 'INF-101', 'EstudianteFemenina', 'Sintética', 'V', '99000001', '2002-04-10', '04149900001', 'est1@test.com', 'F', 'Barquisimeto', 1, '2026-01-15 00:00:00'),
(2, 1, 'ADM-101', 'EstudianteMasculino', 'Sintético', 'V', '99000002', '2001-07-22', '04149900002', 'est2@test.com', 'M', 'Barquisimeto', 1, '2026-01-20 00:00:00');

INSERT INTO `solicitud_de_servicio` (`id_solicitud_serv`, `id_servicios`, `id_beneficiario`, `id_empleado`) VALUES
(1, 1, 1, 17),
(2, 2, 2, 1),
(3, 3, 1, 17),
(4, 4, 2, 17),
(5, 5, 1, 17);

-- 6. Módulo Medicina e Inventario
INSERT INTO `consulta_medica` (`id_consulta_med`, `id_detalle_patologia`, `id_solicitud_serv`, `estatura`, `peso`, `tipo_sangre`, `motivo_visita`, `diagnostico`, `tratamiento`, `observaciones`, `fecha_creacion`) VALUES
(1, 0, 1, 1.65, 60.0, 'O+', 'Fiebre y malestar sintético', 'Gripe sintética', 'Reposo sintético', 'Evolución favorable', '2026-02-01');

INSERT INTO `presentacion_insumo` (`id_presentacion`, `nombre_presentacion`, `fecha_creacion`) VALUES
(1, 'Caja 20 tabletas', '2026-01-01'),
(2, 'Frasco 120 ml', '2026-01-01');

INSERT INTO `insumos` (`id_insumo`, `id_presentacion`, `nombre_insumo`, `descripcion`, `tipo_insumo`, `fecha_vencimiento`, `fecha_creacion`, `cantidad`, `estatus`) VALUES
(1, 1, 'Paracetamol Sintético', 'Analgésico', 'Medicamento', '2030-01-01', '2026-01-01', 25, 'Disponible'),
(2, 1, 'Ibuprofeno Sintético Crítico', 'Antiinflamatorio', 'Medicamento', '2025-01-01', '2026-01-01', 3, 'Disponible');

-- 7. Módulo Psicología y Citas
INSERT INTO `consulta_psicologica` (`id_psicologia`, `id_solicitud_serv`, `id_detalle_patologia`, `tipo_consulta`, `diagnostico`, `tratamiento_gen`, `motivo_retiro`, `duracion_retiro`, `motivo_cambio`, `observaciones`, `fecha_creacion`) VALUES
(1, 2, NULL, 'Diagnóstico', 'Ansiedad leve sintética', 'Terapia sintética', NULL, NULL, NULL, 'Observación sintética', '2026-02-05 09:00:00');

INSERT INTO `cita` (`id_cita`, `fecha`, `hora`, `id_beneficiario`, `id_empleado`, `estatus`, `fecha_creacion`) VALUES
(1, '2026-02-10', '09:00:00', 1, 1, 3, '2026-02-01'),
(2, '2026-02-12', '10:00:00', 2, 1, 5, '2026-02-01');

-- 8. Módulo Orientación
INSERT INTO `orientacion` (`id_orientacion`, `id_solicitud_serv`, `motivo_orientacion`, `descripcion_orientacion`, `obs_adic_orientacion`, `indicaciones_orientacion`, `fecha_creacion`) VALUES
(1, 3, 'Vocacional', 'Evaluación vocacional sintética', 'Ninguna', 'Continuar estudios', '2026-02-10');

-- 9. Módulo Discapacidad
INSERT INTO `discapacidad` (`id_discapacidad`, `id_solicitud_serv`, `tipo_discapacidad`, `disc_especifica`, `diagnostico`, `grado`, `medicamentos`, `habilidades_funcionales`, `requiere_asistencia`, `dispositivo_asistencia`, `observaciones`, `recomendaciones`, `carnet_discapacidad`, `fecha_creacion`) VALUES
(1, 4, 'Física', 'Movilidad reducida', 'Diagnóstico sintético', 'Leve', 'Ninguno', 'Autónomo', 'No', 'Bastón', 'Observación', 'Recomendación', 'C-990001', '2026-02-15');

-- 10. Módulo Trabajo Social (Submódulos)
INSERT INTO `becas` (`id_becas`, `id_solicitud_serv`, `cta_bcv`, `direccion_pdf`, `tipo_banco`, `fecha_creacion`) VALUES
(1, 5, '01020000000000000001', '/docs/beca1.pdf', 'VENE', '2026-02-20');

INSERT INTO `exoneracion` (`id_exoneracion`, `id_solicitud_serv`, `motivo`, `otro_motivo`, `direccion_carta`, `direccion_estudiose`, `carnet_discapacidad`, `fecha_creacion`) VALUES
(1, 5, 'Exoneración sintética', NULL, '/docs/carta.pdf', '/docs/estudio.pdf', 'C-990001', '2026-02-21');

INSERT INTO `fames` (`id_fames`, `id_solicitud_serv`, `id_detalle_patologia`, `tipo_ayuda`, `otro_tipo`, `fecha_creacion`) VALUES
(1, 5, 0, 'Medicamentos', NULL, '2026-02-22');

INSERT INTO `gestion_emb` (`id_gestion`, `id_solicitud_serv`, `id_detalle_patologia`, `semanas_gest`, `codigo_patria`, `serial_patria`, `estado`, `fecha_creacion`) VALUES
(1, 5, 0, 26, 123456, 789012, 'Activo', '2026-02-23');

-- 11. Módulo Referencias
INSERT INTO `referencias` (`id_referencia`, `id_beneficiario`, `id_empleado_origen`, `id_servicio_origen`, `id_empleado_destino`, `id_servicio_destino`, `fecha_referencia`, `motivo`, `estado`, `observaciones`) VALUES
(1, 1, 17, 1, 1, 2, '2026-02-01 10:00:00', 'Interconsulta psicológica sintética', 'Aceptada', 'Sin observaciones');

-- 12. Módulo Jornadas
INSERT INTO `jornadas_medicas` (`id_jornada`, `nombre_jornada`, `tipo_jornada`, `aforo_maximo`, `fecha_inicio`, `fecha_fin`, `ubicacion`, `descripcion`, `estatus`, `fecha_creacion`) VALUES
(1, 'Jornada Preventiva Sintética', 'Especializada', 40, '2026-02-25 08:00:00', '2026-02-25 14:00:00', 'Campus UPTAEB', 'Jornada sintética', 'Finalizada', '2026-02-20 00:00:00');

INSERT INTO `jornada_beneficiarios` (`id_jornada_beneficiario`, `tipo_cedula`, `cedula`, `nombres`, `apellidos`, `fecha_nacimiento`, `genero`, `tipo_paciente`, `telefono`, `correo`, `direccion`, `id_jornada`, `fecha_atencion`, `estatus`) VALUES
(1, 'V', '99000001', 'EstudianteFemenina', 'Sintética', '2002-04-10', 'Femenino', 'Estudiante', '04149900001', 'est1@test.com', 'Barquisimeto', 1, '2026-02-25 09:00:00', 'Atendido');

INSERT INTO `jornada_diagnosticos` (`id_jornada_diagnostico`, `id_jornada_beneficiario`, `id_empleado_medico`, `diagnostico`, `tratamiento`, `observaciones`, `fecha_diagnostico`) VALUES
(1, 1, 17, 'Diagnóstico jornada sintético', 'Tratamiento sintético', 'Sin observaciones', '2026-02-25 10:00:00');

-- 13. Módulo Mobiliario y Equipos
INSERT INTO `tipo_mobiliario` (`id_tipo_mobiliario`, `nombre`, `descripcion`, `estatus`, `fecha_creacion`) VALUES
(1, 'Escritorio', 'Mobiliario administrativo', 1, '2026-01-01');

INSERT INTO `tipo_equipo` (`id_tipo_equipo`, `nombre`, `descripcion`, `estatus`, `fecha_creacion`) VALUES
(1, 'Computadora', 'Equipo de computación', 1, '2026-01-01');

INSERT INTO `mobiliario` (`id_mobiliario`, `id_tipo_mobiliario`, `id_servicios`, `cantidad`, `estado`, `estatus`, `fecha_registro`, `marca`, `modelo`, `color`, `fecha_adquisicion`, `descripcion_adicional`, `observaciones`) VALUES
(1, 1, 1, 1, 'Bueno', 'Activo', '2026-01-10 10:00:00', 'MarcaTest', 'ModTest', 'Gris', '2026-01-01', 'Desc', 'Obs');

INSERT INTO `equipos` (`id_equipo`, `id_tipo_equipo`, `id_servicios`, `marca`, `modelo`, `serial`, `color`, `estado`, `fecha_adquisicion`, `descripcion`, `observaciones`, `estatus`, `fecha_registro`) VALUES
(1, 1, 1, 'HP', 'ProDesk', 'SN-001', 'Negro', 'Bueno', '2026-01-01', 'Equipo sintético', 'Obs', 'Activo', '2026-01-11 10:00:00');

-- 14. Módulo Transporte
INSERT INTO `vehiculos` (`id_vehiculo`, `placa`, `modelo`, `tipo`, `fecha_adquisicion`, `estado`) VALUES
(1, 'TEST-01', 'Yutong Sintético', 'Autobús', '2026-01-01', 'Activo');

INSERT INTO `rutas` (`id_ruta`, `nombre_ruta`, `tipo_ruta`, `punto_partida`, `punto_destino`, `estatus`, `fecha_creacion`) VALUES
(1, 'Ruta UPTAEB Sintética', 'Urbana', 'Campus', 'Terminal', 'Activa', '2026-01-01 08:00:00');

INSERT INTO `proveedores` (`id_proveedor`, `tipo_documento`, `num_documento`, `nombre`, `telefono`, `correo`, `direccion`, `estatus`, `fecha_creacion`) VALUES
(1, 'J', '123456789', 'Proveedor Repuestos Sintético C.A.', '02510000000', 'prov@test.com', 'Barquisimeto', 'Activo', '2026-01-01 00:00:00');

INSERT INTO `repuestos_vehiculos` (`id_repuesto`, `nombre`, `descripcion`, `cantidad`, `id_proveedor`, `fecha_creacion`, `estatus`) VALUES
(1, 'Filtro Sintético', 'Filtro de aceite', 15, 1, '2026-01-01', 'Disponible');

INSERT INTO `asignaciones_rutas` (`id_asignacion`, `id_ruta`, `id_vehiculo`, `id_empleado`, `fecha_asignacion`, `estatus`) VALUES
(1, 1, 1, 17, '2026-02-01', 'Activa');

INSERT INTO `mantenimiento_vehiculos` (`id_mantenimiento`, `id_vehiculo`, `tipo`, `fecha`, `descripcion`) VALUES
(1, 1, 'Preventivo', '2026-02-05', 'Mantenimiento sintético');

SET FOREIGN_KEY_CHECKS = 1;
