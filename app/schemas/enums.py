from enum import StrEnum


class Modulo(StrEnum):
    GENERAL = "general"
    MEDICINA = "medicina"
    PSICOLOGIA = "psicologia"
    ORIENTACION = "orientacion"
    DISCAPACIDAD = "discapacidad"
    TRABAJO_SOCIAL = "trabajo_social"
    REFERENCIAS = "referencias"
    JORNADAS = "jornadas"
    MOBILIARIO = "mobiliario"
    TRANSPORTE = "transporte"


class Intencion(StrEnum):
    RESUMEN_EJECUTIVO = "resumen_ejecutivo"
    ALERTAS_Y_ANOMALIAS = "alertas_y_anomalias"
    TENDENCIAS_Y_PATRONES = "tendencias_y_patrones"
    RECOMENDACIONES = "recomendaciones"


class Genero(StrEnum):
    MASCULINO = "M"
    FEMENINO = "F"


class AreaGeneral(StrEnum):
    BECAS = "Becas"
    EXONERACION = "Exoneración"
    FAMES = "FAMES"
    MEDICINA = "Medicina"
    ORIENTACION = "Orientación"
    DISCAPACIDAD = "Discapacidad"
    PSICOLOGIA = "Psicología"


class SubmoduloTrabajoSocial(StrEnum):
    BECAS = "Becas"
    EXONERACION = "Exoneración"
    FAMES = "FAMES"
    GESTION_EMBARAZO = "Gestión Embarazo"


class TipoConsultaPsicologica(StrEnum):
    DIAGNOSTICO = "Diagnóstico"
    RETIRO_TEMPORAL = "Retiro temporal"
    CAMBIO_CARRERA = "Cambio de carrera"


class TipoDiscapacidad(StrEnum):
    FISICA = "Física"
    SENSORIAL = "Sensorial"
    INTELECTUAL = "Intelectual"
    MULTIPLE = "Múltiple"
    OTRO = "Otro"


class GradoDiscapacidad(StrEnum):
    LEVE = "Leve"
    MODERADO = "Moderado"
    GRAVE = "Grave"


class TipoBien(StrEnum):
    MOBILIARIO = "Mobiliario"
    EQUIPO = "Equipo"


class TipoVehiculo(StrEnum):
    AUTOBUS = "Autobús"
    CAMIONETA = "Camioneta"
    AUTOMOVIL = "Automóvil"


class SeccionTransporte(StrEnum):
    VEHICULOS = "Vehículos"
    RUTAS = "Rutas"
    PROVEEDORES = "Proveedores"
    REPUESTOS = "Repuestos"
    ASIGNACIONES = "Asignaciones"
    MANTENIMIENTOS = "Mantenimientos"


class EstadoCita(StrEnum):
    PENDIENTE = "Pendiente"
    CONFIRMADA = "Confirmada"
    ATENDIDA = "Atendida"
    CANCELADA = "Cancelada"
    NO_ASISTIO = "No asistió"


class EstadoReferencia(StrEnum):
    PENDIENTE = "Pendiente"
    ACEPTADA = "Aceptada"
    RECHAZADA = "Rechazada"


class EstadoJornada(StrEnum):
    ACTIVA = "Activa"
    CANCELADA = "Cancelada"
    FINALIZADA = "Finalizada"


class EstadoInventario(StrEnum):
    ACTIVO = "Activo"
    INACTIVO = "Inactivo"


ESTADOS_CONCATABLES: dict[Modulo, tuple[str, ...]] = {
    Modulo.PSICOLOGIA: tuple(estado.value for estado in EstadoCita),
    Modulo.REFERENCIAS: tuple(estado.value for estado in EstadoReferencia),
    Modulo.JORNADAS: tuple(estado.value for estado in EstadoJornada),
    Modulo.MOBILIARIO: tuple(estado.value for estado in EstadoInventario),
}
