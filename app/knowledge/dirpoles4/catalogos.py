from app.schemas.enums import (
    AreaGeneral,
    EstadoCita,
    EstadoInventario,
    EstadoJornada,
    EstadoReferencia,
    GradoDiscapacidad,
    SubmoduloTrabajoSocial,
    TipoBien,
    TipoConsultaPsicologica,
    TipoDiscapacidad,
    TipoVehiculo,
)

# Catálogo oficial verificable de Programas Nacionales de Formación (PNF) institucionales
CATALOGO_PNF_OFICIAL: frozenset[str] = frozenset(
    {
        "PNF Administración",
        "PNF Contaduría Pública",
        "PNF Informática",
        "PNF Higiene y Seguridad Laboral",
        "PNF Deporte",
        "PNF Turismo",
        "PNF Ciencias de la Información",
        "PNF Sistemas de Calidad y Ambiente",
        "PNF Agroalimentación",
        "PNF Distribución y Logística",
        "PNF Materiales Industriales",
        "PNF Procesos Químicos",
        "PNF Sistemas informáticos",
    }
)

# Dominios cerrados demostrables y autorizados para cada distribución analítica permitida
DOMINIOS_DISTRIBUCIONES: dict[str, frozenset[str]] = {
    "por_genero": frozenset({"Masculino", "Femenino", "No especificado"}),
    "por_pnf": CATALOGO_PNF_OFICIAL,
    "por_area": frozenset(e.value for e in AreaGeneral),
    "por_submodulo": frozenset(e.value for e in SubmoduloTrabajoSocial),
    "morbilidad_por_tipo_consulta": frozenset(e.value for e in TipoConsultaPsicologica),
    "citas_por_estado": frozenset(e.value for e in EstadoCita),
    "por_tipo_bien": frozenset(e.value for e in TipoBien),
    "por_grado": frozenset(e.value for e in GradoDiscapacidad),
    "por_tipo": frozenset(e.value for e in TipoDiscapacidad) | frozenset(e.value for e in TipoVehiculo),
    "por_estado": frozenset(e.value for e in EstadoReferencia),
    "por_estatus": frozenset(e.value for e in EstadoJornada) | frozenset(e.value for e in EstadoInventario),
}

# Catálogo cerrado de distribuciones analíticas autorizadas para transmisión al LLM
DISTRIBUCIONES_PERMITIDAS_LLM: frozenset[str] = frozenset(DOMINIOS_DISTRIBUCIONES.keys())

# Estados de jornada estrictamente controlados
ESTADOS_JORNADA_VALIDOS: frozenset[str] = frozenset(e.value for e in EstadoJornada)

# Lista estricta de claves analíticas agregadas autorizadas para transmisión al LLM
CAMPOS_PERMITIDOS_LLM: frozenset[str] = frozenset(
    {
        "modulo",
        "periodo",
        "registros_procesados",
        "totales",
        "distribuciones",
        "comparativa",
        "serie_mensual",
        "top_areas_concentracion",
        "indicadores",
        "secciones",
        "alertas",
    }
)
