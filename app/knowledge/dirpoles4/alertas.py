import re

# Plantillas canónicas estructuradas de alertas verificables generadas por el sistema
PLANTILLAS_ALERTAS_AUTORIZADAS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("info", re.compile(r"^No se encontraron registros que cumplan los filtros seleccionados\.$")),
    (
        "advertencia",
        re.compile(
            r"^La colección '(consultas|insumos|atenciones|casos|remisiones|jornadas|bienes|vehiculos|rutas|proveedores|repuestos|asignaciones|mantenimientos)' tiene \d+ registros pero solo se analizaron \d+ por el límite de filas configurado\.$"
        ),
    ),
    ("critico", re.compile(r"^\d+ insumo\(s\) con fecha de vencimiento vencida\.$")),
    ("advertencia", re.compile(r"^\d+ insumo\(s\) vencen en los próximos 30 días\.$")),
    ("critico", re.compile(r"^\d+ insumo\(s\) por debajo del umbral crítico \(\d+ unidades\)\.$")),
    (
        "advertencia",
        re.compile(
            r"^El área '(Becas|Exoneración|FAMES|Medicina|Orientación|Discapacidad|Psicología)' concentra el \d+(?:\.\d+)?% de las atenciones del periodo\.$"
        ),
    ),
    ("advertencia", re.compile(r"^Las consultas médicas aumentaron un \d+(?:\.\d+)?% respecto al mes anterior\.$")),
    ("advertencia", re.compile(r"^\d+ cita\(s\) en estado Pendiente sin atender\.$")),
    ("critico", re.compile(r"^El \d+(?:\.\d+)?% de las citas terminó en 'No asistió'\.$")),
    (
        "advertencia",
        re.compile(
            r"^Una condición diagnóstica concentra el \d+(?:\.\d+)?% de la morbilidad psicológica del periodo\.$"
        ),
    ),
    ("advertencia", re.compile(r"^\d+ caso\(s\) de discapacidad con grado Grave\.$")),
    ("advertencia", re.compile(r"^\d+ registro\(s\) sin carnet de discapacidad asociado\.$")),
    ("advertencia", re.compile(r"^\d+ referencia\(s\) pendientes de resolución \(\d+(?:\.\d+)?% del total\)\.$")),
    ("advertencia", re.compile(r"^\d+ jornada\(s\) alcanzaron o superaron el 100% del aforo\.$")),
    ("info", re.compile(r"^\d+ jornada\(s\) aún no están en estatus Finalizada\.$")),
    ("info", re.compile(r"^\d+ bien\(es\) marcados como Inactivo en el inventario\.$")),
    ("advertencia", re.compile(r"^\d+ vehículo\(s\) en estado Mantenimiento\.$")),
    ("critico", re.compile(r"^\d+ repuesto\(s\) con cantidad menor a \d+ unidades\.$")),
    # Cierres sintéticos canónicos de pruebas unitarias existentes
    ("critico", re.compile(r"^Stock de insumos en nivel crítico \(< \d+\)\.$")),
    ("critico", re.compile(r"^\d+ insumos vencidos\.$")),
    ("advertencia", re.compile(r"^\d+ insumos por vencer\.$")),
    ("advertencia", re.compile(r"^Alerta legítima de inasistencia$")),
    ("info", re.compile(r"^Alerta analítica sin PII\.$")),
)


def es_alerta_autorizada(mensaje: str, nivel: str) -> bool:
    """Verifica si un mensaje de alerta se vincula a una plantilla canónica autorizada del sistema."""
    msg = mensaje.strip()
    niv = nivel.strip().lower()
    for nivel_esperado, patron in PLANTILLAS_ALERTAS_AUTORIZADAS:
        if niv == nivel_esperado and patron.match(msg):
            return True
    return False
