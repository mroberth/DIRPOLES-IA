"""Configuración común del paquete de pruebas.

La suite debe ser determinista y no depender de servicios externos:

- ``KNOWLEDGE_BACKEND=static``: usa el fallback declarativo en Python. Las
  pruebas específicas de MariaDB instancian ``ConocimientoMariaDB`` de forma
  explícita, por lo que siguen cubriendo la integración con la base de datos.
- ``MOCK_LLM=True``: evita llamadas reales a Google Gemini durante la suite.
  Las pruebas que necesitan el cliente real lo configuran con ``patch``.
"""

import os

os.environ.setdefault("KNOWLEDGE_BACKEND", "static")
os.environ.setdefault("MOCK_LLM", "True")
