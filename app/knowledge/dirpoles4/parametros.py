"""Parámetros declarativos de respaldo para DIRPOLES-4.

Estos valores son el *fallback* determinista del motor cuando la base de
conocimiento ``dirpoles_knowledge`` no está disponible. La fuente de verdad en
producción es la base de datos; este módulo garantiza que el servicio siga
operando (patrón fallback) si MariaDB cae o no tiene las tablas nuevas.
"""

# Umbrales de inferencia por código de hecho observable.
# La clave coincide con ``conocimiento_hechos_sintomas.codigo_hecho``.
UMBRALES_POR_DEFECTO: dict[str, float] = {
    "CONCENTRACION_AREA_GENERAL": 40.0,
    "STOCK_INSUMO_MEDICO": 10.0,
    "DIAS_VENCIMIENTO_VENCIDO": 0.0,
    "DIAS_VENCIMIENTO_PROXIMO": 30.0,
    "VARIACION_CONSULTAS_MEDICAS": 25.0,
    "TASA_AUSENTISMO_CITA_PSI": 15.0,
    "CITAS_PENDIENTES_PSI": 0.0,
    "CONCENTRACION_DIAGNOSTICO_PSI": 30.0,
    "CONCENTRACION_SOLICITUD_BECA": 60.0,
    "CASOS_DISCAPACIDAD_GRAVE": 0.0,
    "REGISTROS_SIN_CARNET": 0.0,
    "REFERENCIAS_PENDIENTES": 0.0,
    "OCUPACION_JORNADA": 100.0,
    "JORNADAS_SIN_FINALIZAR": 0.0,
    "BIENES_INACTIVOS": 0.0,
    "VEHICULOS_MANTENIMIENTO": 0.0,
    "STOCK_REPUESTOS_TRANSPORTE": 5.0,
}

# Plantillas de mensajes por código de conclusión.
# La clave coincide con ``conocimiento_conclusiones.codigo_conclusion``.
MENSAJES_POR_DEFECTO: dict[str, str] = {
    "ALERTA_TRUNCAMIENTO": (
        "La colección '{coleccion}' tiene {total} registros pero solo se analizaron "
        "{analizados} por el límite de filas configurado."
    ),
    "ALERTA_SIN_REGISTROS": ("No se encontraron registros que cumplan los filtros seleccionados."),
    "ALERTA_INSUMOS_VENCIDOS": "{cantidad} insumo(s) con fecha de vencimiento vencida.",
    "ALERTA_INSUMOS_POR_VENCER": "{cantidad} insumo(s) vencen en los próximos 30 días.",
    "ALERTA_INSUMOS_STOCK_CRITICO": (
        "{cantidad} insumo(s) por debajo del umbral crítico ({umbral} unidades)."
    ),
    "ALERTA_AREA_CONCENTRADA": (
        "El área '{valor}' concentra el {porcentaje}% de las atenciones del periodo."
    ),
    "ALERTA_CONSULTAS_AUMENTO": (
        "Las consultas médicas aumentaron un {variacion}% respecto al mes anterior."
    ),
    "ALERTA_CITAS_PENDIENTES": "{cantidad} cita(s) en estado Pendiente sin atender.",
    "ALERTA_CITAS_NO_ASISTIO": "El {porcentaje}% de las citas terminó en 'No asistió'.",
    "ALERTA_MORBILIDAD_CONCENTRADA": (
        "Una condición diagnóstica concentra el {porcentaje}% de la morbilidad "
        "psicológica del periodo."
    ),
    "ALERTA_BECAS_CONCENTRADAS": (
        "El área 'Becas' concentra el {porcentaje}% de las atenciones del periodo."
    ),
    "ALERTA_DISCAPACIDAD_GRAVE": "{cantidad} caso(s) de discapacidad con grado Grave.",
    "ALERTA_SIN_CARNET": ("{cantidad} registro(s) sin carnet de discapacidad asociado."),
    "ALERTA_REFERENCIAS_PENDIENTES": (
        "{cantidad} referencia(s) pendientes de resolución ({porcentaje}% del total)."
    ),
    "ALERTA_JORNADAS_AFORO": ("{cantidad} jornada(s) alcanzaron o superaron el 100% del aforo."),
    "ALERTA_JORNADAS_SIN_FINALIZAR": ("{cantidad} jornada(s) aún no están en estatus Finalizada."),
    "ALERTA_BIENES_INACTIVOS": ("{cantidad} bien(es) marcados como Inactivo en el inventario."),
    "ALERTA_VEHICULOS_MANTENIMIENTO": ("{cantidad} vehículo(s) en estado Mantenimiento."),
    "ALERTA_REPUESTOS_BAJO_STOCK": (
        "{cantidad} repuesto(s) con cantidad menor a {umbral} unidades."
    ),
}

__all__ = ["MENSAJES_POR_DEFECTO", "UMBRALES_POR_DEFECTO"]
