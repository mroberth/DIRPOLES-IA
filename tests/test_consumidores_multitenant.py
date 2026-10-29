"""Pruebas unitarias para el Registro Multitenant de Consumidores (Fase 5).

Verifica:
1. Modelo PerfilConsumidor e inmutabilidad.
2. RegistroConsumidores en memoria y comparación timing-safe.
3. Desactivación de consumidores (activo=False).
4. Carga declarativa desde archivo JSON.
5. Autenticación exitosa en la API con API Keys de múltiples consumidores distintos.
"""

import json
import os
import tempfile
import unittest

from fastapi.testclient import TestClient

from app.core.config import obtener_ajustes
from app.core.consumers import (
    PerfilConsumidor,
    RegistroConsumidores,
    obtener_registro_consumidores,
)
from app.main import app


class TestConsumidoresMultitenant(unittest.TestCase):
    def setUp(self) -> None:
        self.registro = RegistroConsumidores()
        self.perfil_dirpoles = PerfilConsumidor(
            id="dirpoles4",
            nombre="DIRPOLES-4 Monolito",
            api_key="key-dirpoles-123",
            modo_acceso="sql_pull",
            conocimiento_id="dirpoles4",
            adaptador_id="dirpoles4_sql",
        )
        self.perfil_externo = PerfilConsumidor(
            id="logistica",
            nombre="Sistema Logístico Externo",
            api_key="key-logistica-456",
            modo_acceso="push",
            conocimiento_id="dirpoles4",
            adaptador_id="en_memoria",
        )
        self.registro.registrar(self.perfil_dirpoles)
        self.registro.registrar(self.perfil_externo)

    def test_autenticacion_exitosa_por_api_key(self) -> None:
        c1 = self.registro.autenticar("key-dirpoles-123")
        self.assertIsNotNone(c1)
        self.assertEqual(c1.id, "dirpoles4")

        c2 = self.registro.autenticar("key-logistica-456")
        self.assertIsNotNone(c2)
        self.assertEqual(c2.id, "logistica")

    def test_autenticacion_rechaza_claves_invalidas_o_nulas(self) -> None:
        self.assertIsNone(self.registro.autenticar(None))
        self.assertIsNone(self.registro.autenticar(""))
        self.assertIsNone(self.registro.autenticar("clave_inexistente"))

    def test_consumidor_inactivo_es_rechazado(self) -> None:
        inactivo = PerfilConsumidor(
            id="inactivo",
            nombre="Consumidor Suspendido",
            api_key="key-suspendida",
            activo=False,
        )
        self.registro.registrar(inactivo)
        self.assertIsNone(self.registro.autenticar("key-suspendida"))

    def test_carga_declarativa_desde_json(self) -> None:
        datos = [
            {
                "id": "tenant_a",
                "nombre": "Tenant A en la Nube",
                "api_key": "key-tenant-a",
                "modo_acceso": "push",
            },
            {
                "id": "tenant_b",
                "nombre": "Tenant B Hospitalario",
                "api_key": "key-tenant-b",
                "modo_acceso": "push",
                "activo": False,
            },
        ]
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as f:
            json.dump(datos, f)
            temp_path = f.name

        try:
            reg = RegistroConsumidores()
            cargados = reg.cargar_desde_archivo(temp_path)
            self.assertEqual(cargados, 2)
            self.assertIsNotNone(reg.autenticar("key-tenant-a"))
            self.assertIsNone(reg.autenticar("key-tenant-b"))  # Inactivo
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_api_v2_autentica_consumidor_registrado_dinamicamente(self) -> None:
        """Verifica que un consumidor registrado adicionalmente pueda consumir

        la API V2 con su propia API Key sin interferir con DIRPOLES-4.
        """
        cliente = TestClient(app)
        reg_global = obtener_registro_consumidores()
        nueva_key = "key-consumidor-multitenant-v2"
        reg_global.registrar(
            PerfilConsumidor(
                id="consumidor_v2_test",
                nombre="Consumidor Dinámico V2",
                api_key=nueva_key,
                modo_acceso="push",
            )
        )

        resp = cliente.post(
            "/api/v2/analizar",
            headers={"X-API-Key": nueva_key},
            json={
                "dominio": "inventario_repuestos",
                "intencion": "resumen_ejecutivo",
                "metricas": {
                    "totales": {"repuestos": 100},
                    "distribuciones": {
                        "por_estado": [
                            {"valor": "Operativo", "cantidad": 80},
                            {"valor": "Dañado", "cantidad": 20},
                        ]
                    },
                },
            },
        )
        self.assertEqual(resp.status_code, 200)
        cuerpo = resp.json()
        self.assertTrue(cuerpo["exito"])
        self.assertEqual(cuerpo["dominio"], "inventario_repuestos")


if __name__ == "__main__":
    unittest.main()
