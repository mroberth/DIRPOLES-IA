from app.db.queries._comunes import (
    Consulta,
    Parametros,
    agregar_fechas,
    agregar_igual,
)
from app.db.queries.general_queries import puro
from app.schemas.request import FiltrosDTO

_RAMAS_TS = (
    ("Becas", "becas", "bec", "bec.fecha_creacion", "CONCAT('Banco: ', bec.tipo_banco)"),
    (
        "Exoneración",
        "exoneracion",
        "exo",
        "exo.fecha_creacion",
        "CONCAT('Motivo: ', COALESCE(exo.motivo, 'No indicado'))",
    ),
    ("FAMES", "fames", "fam", "fam.fecha_creacion", "CONCAT('Ayuda: ', fam.tipo_ayuda)"),
    (
        "Gestión Embarazo",
        "gestion_emb",
        "emb",
        "emb.fecha_creacion",
        "CONCAT('Semanas de gestación: ', emb.semanas_gest)",
    ),
)


def trabajo_social(filtros: FiltrosDTO, id_empleado: int | None) -> dict[str, Consulta]:
    params: Parametros = {}
    condicion_empleado = ""
    if id_empleado is not None:
        condicion_empleado = " AND ss.id_empleado = :id_empleado"
        params["id_empleado"] = id_empleado

    ramas = [
        (
            f"SELECT '{submodulo}' AS submodulo, DATE({fecha}) AS fecha, "
            f"b.id_beneficiario, b.nombres, b.apellidos, "
            f"CONCAT(b.tipo_cedula, '-', b.cedula) AS cedula, b.genero, b.id_pnf, "
            f"pnf.nombre_pnf, {detalle} AS detalle_extra "
            f"FROM {tabla} {alias} "
            f"JOIN solicitud_de_servicio ss ON {alias}.id_solicitud_serv = ss.id_solicitud_serv "
            f"JOIN beneficiario b ON ss.id_beneficiario = b.id_beneficiario "
            f"LEFT JOIN pnf ON b.id_pnf = pnf.id_pnf "
            f"WHERE {fecha} IS NOT NULL" + condicion_empleado
        )
        for submodulo, tabla, alias, fecha, detalle in _RAMAS_TS
    ]
    union = "\nUNION ALL\n".join(ramas)

    cond_externas: list[str] = ["1 = 1"]
    agregar_fechas(cond_externas, params, "t.fecha", filtros)
    agregar_igual(cond_externas, params, "t.id_pnf", "f_pnf", filtros.pnf)
    agregar_igual(cond_externas, params, "t.submodulo", "f_submodulo", puro(filtros.submodulo))

    base = f"SELECT * FROM (\n{union}\n) t WHERE " + " AND ".join(cond_externas)
    return {
        "registros": Consulta(base=base, orden="t.fecha DESC, t.submodulo ASC", params=params),
    }
