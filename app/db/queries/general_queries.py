from enum import Enum

from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
)
from app.schemas.request import FiltrosDTO

_RAMAS_GENERAL = (
    ("Becas", "becas", "bp", "bp.fecha_creacion"),
    ("Exoneración", "exoneracion", "ep", "ep.fecha_creacion"),
    ("FAMES", "fames", "fp", "fp.fecha_creacion"),
    ("Medicina", "consulta_medica", "mp", "mp.fecha_creacion"),
    ("Orientación", "orientacion", "op", "op.fecha_creacion"),
    ("Discapacidad", "discapacidad", "dp", "dp.fecha_creacion"),
    ("Psicología", "consulta_psicologica", "cp", "cp.fecha_creacion"),
)


def puro(valor: object) -> object:
    return valor.value if isinstance(valor, Enum) else valor


def _rama(area: str, tabla: str, alias: str, columna_fecha: str) -> str:
    return (
        f"SELECT b.id_beneficiario, b.nombres, b.apellidos, "
        f"CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, "
        f"pnf.nombre_pnf, '{area}' AS area, DATE({columna_fecha}) AS fecha "
        f"FROM {tabla} {alias} "
        f"JOIN solicitud_de_servicio ss ON {alias}.id_solicitud_serv = ss.id_solicitud_serv "
        f"JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
        f"LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf "
        f"WHERE {columna_fecha} IS NOT NULL"
    )


def general(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    params: Parametros = {}
    condicion_empleado = ""
    if id_empleado is not None:
        condicion_empleado = " AND ss.id_empleado = :id_empleado"
        params["id_empleado"] = id_empleado

    ramas = [
        _rama(area, tabla, alias, fecha) + condicion_empleado
        for area, tabla, alias, fecha in _RAMAS_GENERAL
    ]
    union = "\nUNION ALL\n".join(ramas)

    cond_externas: list[str] = ["1 = 1"]
    agregar_fechas(cond_externas, params, "t.fecha", filtros)
    agregar_igual(cond_externas, params, "t.genero", "f_genero", puro(filtros.genero))
    agregar_igual(cond_externas, params, "t.id_pnf", "f_pnf", filtros.pnf)
    agregar_igual(cond_externas, params, "t.area", "f_area", puro(filtros.area))

    base = f"SELECT * FROM (\n{union}\n) t WHERE " + " AND ".join(cond_externas)
    return {
        "atenciones": Consulta(base=base, orden="t.fecha DESC, t.apellidos ASC", params=params),
    }
