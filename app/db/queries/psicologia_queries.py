from app.core.config import obtener_ajustes
from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_empleado,
    agregar_fechas,
    agregar_igual,
    clausula_where,
)
from app.db.queries.general_queries import puro
from app.schemas.request import FiltrosDTO


def psicologia(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    seguridad = obtener_ajustes().db_name_security

    morb_cond: list[str] = ["1 = 1"]
    morb_params: Parametros = {}
    agregar_fechas(morb_cond, morb_params, "cp.fecha_creacion", filtros)
    agregar_igual(morb_cond, morb_params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_igual(
        morb_cond, morb_params, "cp.tipo_consulta", "f_tipo_consulta", puro(filtros.tipo_consulta)
    )
    agregar_empleado(morb_cond, morb_params, "ss.id_empleado", id_empleado)

    morbilidad_base = (
        "SELECT cp.id_psicologia, DATE(cp.fecha_creacion) AS fecha, b.nombres, b.apellidos, "
        "CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, pnf.nombre_pnf, "
        "cp.tipo_consulta, cp.diagnostico "
        "FROM consulta_psicologica cp "
        "JOIN solicitud_de_servicio ss ON cp.id_solicitud_serv = ss.id_solicitud_serv "
        "JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        "LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf" + clausula_where(morb_cond)
    )

    citas_cond: list[str] = ["1 = 1"]
    citas_params: Parametros = {}
    agregar_fechas(citas_cond, citas_params, "c.fecha", filtros)
    agregar_igual(citas_cond, citas_params, "b.id_pnf", "f_pnf", filtros.pnf)
    agregar_igual(citas_cond, citas_params, "ec.nombre", "f_estado", filtros.estado)
    agregar_empleado(citas_cond, citas_params, "c.id_empleado", id_empleado)

    citas_base = (
        "SELECT c.id_cita, c.fecha, TIME_FORMAT(c.hora, '%H:%i') AS hora, "
        "b.nombres, b.apellidos, CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, "
        "b.id_pnf, pnf.nombre_pnf, ec.nombre AS estado, "
        "CONCAT(e.nombre, ' ', e.apellido) AS psicologo "
        "FROM cita c "
        "JOIN beneficiario b ON c.id_beneficiario = b.id_beneficiario "
        "LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf "
        "LEFT JOIN estado_cita ec ON ec.id_estado = c.estatus "
        f"LEFT JOIN {seguridad}.empleado e ON e.id_empleado = c.id_empleado"
        + clausula_where(citas_cond)
    )

    return {
        "morbilidad": Consulta(
            base=morbilidad_base,
            orden="cp.fecha_creacion DESC, cp.id_psicologia DESC",
            params=morb_params,
        ),
        "citas": Consulta(
            base=citas_base,
            orden="c.fecha DESC, c.hora DESC",
            params=citas_params,
        ),
    }
