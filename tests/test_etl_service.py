from datetime import date

import pandas as pd
from app.schemas.enums import Modulo
from app.schemas.request import FiltrosDTO
from app.services.etl_service import Extraccion, transformar


def _filtros(**kwargs: object) -> FiltrosDTO:
    return FiltrosDTO.model_validate(kwargs)


def _extraccion(datos: dict[str, pd.DataFrame], totales: dict[str, int]) -> Extraccion:
    return Extraccion(datos=datos, totales=totales)


def test_medicina_detecta_stock_critico_y_vencidos() -> None:
    consultas = pd.DataFrame(
        [
            {
                "fecha": date(2026, 3, 1),
                "genero": "M",
                "nombre_pnf": "PNF Informática",
                "motivo": "Fiebre",
                "diagnostico": "Gripe",
            },
            {
                "fecha": date(2026, 3, 15),
                "genero": "F",
                "nombre_pnf": "PNF Informática",
                "motivo": "Dolor",
                "diagnostico": "Gripe",
            },
        ]
    )
    insumos = pd.DataFrame(
        [
            {
                "nombre_insumo": "Paracetamol",
                "cantidad": 2,
                "fecha_vencimiento": date(2026, 1, 1),
                "estatus": "Disponible",
            },
            {
                "nombre_insumo": "Guantes",
                "cantidad": 50,
                "fecha_vencimiento": date(2030, 1, 1),
                "estatus": "Disponible",
            },
        ]
    )
    extraccion = _extraccion(
        {"consultas": consultas, "insumos": insumos},
        {"consultas": 2, "insumos": 2},
    )
    resumen = transformar(Modulo.MEDICINA, extraccion, _filtros())

    assert resumen["registros_procesados"] == 4
    niveles = {a["nivel"] for a in resumen["alertas"]}
    assert "critico" in niveles
    indicadores = resumen["indicadores"]["insumos"]
    assert indicadores["vencidos"] == 1
    assert indicadores["stock_critico"][0]["nombre"] == "Paracetamol"
    assert resumen["distribuciones"]["top_diagnosticos"][0]["valor"] == "Gripe"
    assert resumen["distribuciones"]["top_diagnosticos"][0]["porcentaje"] == 100.0


def test_medicina_comparativa_mensual() -> None:
    consultas = pd.DataFrame(
        [
            {"fecha": date(2026, 1, 5), "genero": "M", "diagnostico": "A", "motivo": "x"},
            {"fecha": date(2026, 2, 5), "genero": "M", "diagnostico": "A", "motivo": "x"},
            {"fecha": date(2026, 2, 6), "genero": "M", "diagnostico": "A", "motivo": "x"},
            {"fecha": date(2026, 2, 7), "genero": "M", "diagnostico": "B", "motivo": "x"},
        ]
    )
    extraccion = _extraccion({"consultas": consultas, "insumos": pd.DataFrame()}, {"consultas": 4})
    resumen = transformar(Modulo.MEDICINA, extraccion, _filtros())
    comp = resumen["comparativa"]
    assert comp is not None
    assert comp["mes_anterior"]["cantidad"] == 1
    assert comp["mes_actual"]["cantidad"] == 3
    assert comp["variacion_pct"] == 200.0


def test_psicologia_alerta_por_no_asistio() -> None:
    citas = pd.DataFrame(
        [
            {"fecha": date(2026, 3, 1), "estado": "Atendida"},
            {"fecha": date(2026, 3, 2), "estado": "No asistió"},
            {"fecha": date(2026, 3, 3), "estado": "No asistió"},
            {"fecha": date(2026, 3, 4), "estado": "Pendiente"},
        ]
    )
    morbilidad = pd.DataFrame(
        [{"fecha": date(2026, 3, 1), "tipo_consulta": "Diagnóstico", "diagnostico": "Ansiedad"}]
    )
    extraccion = _extraccion(
        {"citas": citas, "morbilidad": morbilidad},
        {"citas": 4, "morbilidad": 1},
    )
    resumen = transformar(Modulo.PSICOLOGIA, extraccion, _filtros())
    assert resumen["indicadores"]["citas_no_asistio"] == 2
    assert resumen["indicadores"]["citas_pendientes"] == 1
    assert any("No asistió" in a["mensaje"] for a in resumen["alertas"])


def test_referencias_alerta_por_pendientes() -> None:
    remisiones = pd.DataFrame(
        [
            {"fecha": date(2026, 3, 1), "estado": "Pendiente", "servicio_destino": "Medicina"},
            {"fecha": date(2026, 3, 2), "estado": "Aceptada", "servicio_destino": "Medicina"},
        ]
    )
    extraccion = _extraccion({"remisiones": remisiones}, {"remisiones": 2})
    resumen = transformar(Modulo.REFERENCIAS, extraccion, _filtros())
    assert resumen["indicadores"]["pendientes"] == 1
    assert any("pendiente" in a["mensaje"].lower() for a in resumen["alertas"])


def test_general_distribuciones_y_area_concentrada() -> None:
    filas = [
        {
            "fecha": date(2026, 3, 1),
            "area": "Medicina",
            "genero": "F",
            "nombre_pnf": "PNF Informática",
        }
        for _ in range(7)
    ] + [
        {
            "fecha": date(2026, 3, 2),
            "area": "Psicología",
            "genero": "M",
            "nombre_pnf": "PNF Contaduría",
        }
        for _ in range(3)
    ]
    extraccion = _extraccion({"atenciones": pd.DataFrame(filas)}, {"atenciones": 10})
    resumen = transformar(Modulo.GENERAL, extraccion, _filtros())
    assert resumen["distribuciones"]["por_area"][0]["valor"] == "Medicina"
    assert resumen["distribuciones"]["por_area"][0]["porcentaje"] == 70.0
    assert resumen["distribuciones"]["por_genero"][0]["valor"] == "Femenino"
    assert any("Medicina" in a["mensaje"] for a in resumen["alertas"])


def test_dataset_vacio_genera_alerta_informativa() -> None:
    extraccion = _extraccion(
        {"casos": pd.DataFrame()},
        {"casos": 0},
    )
    resumen = transformar(Modulo.ORIENTACION, extraccion, _filtros())
    assert resumen["registros_procesados"] == 0
    assert any("No se encontraron registros" in a["mensaje"] for a in resumen["alertas"])


def test_truncamiento_por_limit_genera_advertencia() -> None:
    df = pd.DataFrame([{"fecha": date(2026, 3, 1), "submodulo": "Becas"}] * 3)
    extraccion = _extraccion({"registros": df}, {"registros": 100})
    resumen = transformar(Modulo.TRABAJO_SOCIAL, extraccion, _filtros())
    assert any("límite de filas" in a["mensaje"] for a in resumen["alertas"])


def test_transporte_repuestos_bajo_stock() -> None:
    repuestos = pd.DataFrame(
        [
            {"nombre": "Filtro de aceite", "cantidad": 2, "estatus": "Disponible"},
            {"nombre": "Pastillas", "cantidad": 20, "estatus": "Disponible"},
        ]
    )
    extraccion = _extraccion(
        {"repuestos": repuestos, "vehiculos": pd.DataFrame()},
        {"repuestos": 2, "vehiculos": 0},
    )
    resumen = transformar(Modulo.TRANSPORTE, extraccion, _filtros())
    assert resumen["secciones"]["repuestos"]["bajo_stock"] == 1
    assert any("repuesto" in a["mensaje"].lower() for a in resumen["alertas"])


def test_jornadas_ocupacion_de_aforo() -> None:
    jornadas = pd.DataFrame(
        [
            {
                "nombre_jornada": "Jornada Dental",
                "tipo_jornada": "Especializada",
                "fecha_inicio": date(2026, 3, 1),
                "estatus": "Finalizada",
                "aforo_maximo": 10,
                "total_asistentes": 12,
                "total_diagnosticos": 8,
            }
        ]
    )
    extraccion = _extraccion({"jornadas": jornadas}, {"jornadas": 1})
    resumen = transformar(Modulo.JORNADAS, extraccion, _filtros())
    assert resumen["indicadores"]["asistentes_totales"] == 12
    assert resumen["indicadores"]["ocupacion_por_jornada"][0]["ocupacion_pct"] == 120.0
    assert any("aforo" in a["mensaje"] for a in resumen["alertas"])


def test_discapacidad_conteo_carnet_y_grave() -> None:
    df = pd.DataFrame(
        [
            {
                "fecha": date(2026, 3, 1),
                "tipo_discapacidad": "Física",
                "grado": "Grave",
                "carnet_discapacidad": "C-001",
                "requiere_asistencia": "Si",
            },
            {
                "fecha": date(2026, 3, 2),
                "tipo_discapacidad": "Sensorial",
                "grado": "Leve",
                "carnet_discapacidad": "",
                "requiere_asistencia": "No",
            },
        ]
    )
    extraccion = _extraccion({"registros": df}, {"registros": 2})
    resumen = transformar(Modulo.DISCAPACIDAD, extraccion, _filtros())
    assert resumen["indicadores"]["con_carnet"] == 1
    assert resumen["indicadores"]["sin_carnet"] == 1
    assert resumen["indicadores"]["grado_grave"] == 1
    assert any("Grave" in a["mensaje"] for a in resumen["alertas"])
