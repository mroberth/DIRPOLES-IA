from typing import Any, Protocol

from app.core.config import obtener_ajustes


class ClienteIA(Protocol):
    modo: str

    def generar_informe(
        self,
        system_prompt: str,
        user_prompt: str,
        contexto: dict[str, Any],
    ) -> str: ...


class ClienteGemini:
    modo = "gemini"

    def __init__(self, api_key: str, modelo: str) -> None:
        from google import genai

        self._cliente = genai.Client(api_key=api_key)
        self._modelo = modelo

    def generar_informe(
        self,
        system_prompt: str,
        user_prompt: str,
        contexto: dict[str, Any],
    ) -> str:
        from google.genai import types

        respuesta = self._cliente.models.generate_content(
            model=self._modelo,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )
        texto = (respuesta.text or "").strip()
        if not texto:
            raise RuntimeError("El proveedor Gemini devolvió una respuesta vacía.")
        return texto


def _valor_alertas(alertas: list[dict[str, str]]) -> str:
    if not alertas:
        return "* No se detectaron anomalías críticas en el periodo analizado.*"
    iconos = {"critico": "🔴", "advertencia": "🟡", "info": "🔵"}
    etiquetas = {"critico": "Crítico", "advertencia": "Advertencia", "info": "Información"}
    lineas = []
    for alerta in alertas:
        nivel = alerta.get("nivel", "info")
        icono = iconos.get(nivel, "🔵")
        etiqueta = etiquetas.get(nivel, nivel.capitalize())
        lineas.append(f"* {icono} **{etiqueta}:** {alerta.get('mensaje', '')}")
    return "\n".join(lineas)


def _tabla_distribucion(clave: str, distribuciones: dict[str, Any]) -> str:
    filas = distribuciones.get(clave) or []
    if not filas:
        return ""
    lineas = [f"\n**{_rotulo(clave)}:**", ""]
    lineas.append("| Valor | Cantidad | % |")
    lineas.append("| --- | ---: | ---: |")
    for fila in filas:
        lineas.append(f"| {fila['valor']} | {fila['cantidad']} | {fila['porcentaje']}% |")
    return "\n".join(lineas)


def _comparativa_markdown(resumen: dict[str, Any]) -> str:
    comp = resumen.get("comparativa")
    if not comp:
        return ""
    variacion = comp.get("variacion_pct")
    if variacion is None:
        nota = comp.get("nota") or "sin base comparable"
        return f"\n**Comparativa mensual:** {nota}.\n"
    direccion = "incremento" if variacion >= 0 else "descenso"
    return (
        f"\n**Comparativa mensual:** {direccion} del **{abs(variacion)}%** "
        f"({comp['mes_anterior']['mes']} → {comp['mes_actual']['mes']}).\n"
    )


def _rotulo(clave: str) -> str:
    return clave.replace("_", " ").capitalize()


def _seccion_indicadores(resumen: dict[str, Any]) -> str:
    indicadores = resumen.get("indicadores") or {}
    lineas = []

    def _volcar(prefijo: str, valor: Any) -> None:
        if isinstance(valor, list):
            return
        if isinstance(valor, dict):
            for subclave, subvalor in valor.items():
                if isinstance(subvalor, (dict, list)):
                    continue
                lineas.append(f"* **{_rotulo(prefijo + ' ' + subclave)}:** {subvalor}")
            return
        lineas.append(f"* **{_rotulo(prefijo)}:** {valor}")

    for clave, valor in indicadores.items():
        _volcar(clave, valor)
    return "\n".join(lineas)


def _seccion_totales(resumen: dict[str, Any]) -> str:
    totales = resumen.get("totales") or {}
    lineas = []
    for clave, valor in totales.items():
        lineas.append(f"* **{_rotulo(clave)}:** {valor}")
    return "\n".join(lineas)


class ClienteSimulado:
    modo = "simulado"

    def generar_informe(
        self,
        system_prompt: str,
        user_prompt: str,
        contexto: dict[str, Any],
    ) -> str:
        del system_prompt, user_prompt
        resumen: dict[str, Any] = contexto.get("resumen", {})
        modulo = resumen.get("modulo", "desconocido")
        intencion = contexto.get("intencion", "resumen_ejecutivo")
        periodo = resumen.get("periodo", {}) or {}
        inicio = periodo.get("fecha_inicio") or "inicio de registros"
        fin = periodo.get("fecha_fin") or "la fecha actual"
        alertas = resumen.get("alertas", [])
        distribuciones = resumen.get("distribuciones", {}) or {}

        criticas = [a for a in alertas if a.get("nivel") == "critico"]
        advertencias = [a for a in alertas if a.get("nivel") == "advertencia"]

        partes = [
            f"### 📊 Informe de Análisis Inteligente: Módulo {modulo.capitalize()}",
            "",
            f"**Periodo:** {inicio} al {fin}  ",
            f"**Intención:** {intencion.replace('_', ' ')}  ",
            f"**Registros procesados:** {resumen.get('registros_procesados', 0)}",
            "",
            "#### 1. Resumen Ejecutivo",
            "",
            _seccion_totales(resumen) or "* Sin totales registrados para el periodo.",
            _comparativa_markdown(resumen),
            "",
            "#### 2. Hallazgos Clave y Puntos Críticos",
            "",
            "**Alertas detectadas por la capa analítica:**",
            "",
            _valor_alertas(alertas),
        ]

        for clave in distribuciones:
            tabla = _tabla_distribucion(clave, distribuciones)
            if tabla:
                partes.append(tabla)

        indicadores = _seccion_indicadores(resumen)
        if indicadores:
            partes.extend(["", "**Indicadores clave:**", "", indicadores])

        partes.extend(
            [
                "",
                "#### 3. Recomendaciones Operativas para la Toma de Decisiones",
                "",
            ]
        )
        recomendaciones: list[str] = []
        if criticas:
            recomendaciones.append(
                f"Priorizar la atención de los {len(criticas)} alerta(s) crítica(s) "
                "identificadas: requieren gestión inmediata."
            )
        if advertencias:
            recomendaciones.append(
                f"Revisar las {len(advertencias)} advertencia(s) y asignar responsables "
                "para su seguimiento en el corto plazo."
            )
        if not alertas:
            recomendaciones.append(
                "Mantener el ritmo operativo actual; no se detectaron anomalías que "
                "requieran intervención."
            )
        recomendaciones.append(
            "Contrastar estos hallazgos con los reportes históricos de la Dirección "
            "para validar la sostenibilidad de las tendencias observadas."
        )
        recomendaciones.append(
            "Registrar en el sistema de gestión las acciones derivadas de este informe "
            "para su trazabilidad."
        )
        for indice, texto in enumerate(recomendaciones, start=1):
            partes.append(f"{indice}. {texto}")
        partes.append("")
        partes.append("---")
        partes.append(
            "*Informe generado por DIRPOLES-IA en modo simulado (sin conexión al proveedor de IA).*"
        )
        partes.append("")
        return "\n".join(partes)


def obtener_cliente() -> ClienteIA:
    ajustes = obtener_ajustes()
    if ajustes.usar_gemini_real:
        try:
            return ClienteGemini(api_key=ajustes.gemini_api_key, modelo=ajustes.gemini_model)
        except Exception:
            return ClienteSimulado()
    return ClienteSimulado()
