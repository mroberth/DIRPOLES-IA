# Entorno de Integración Aislado para DIRPOLES-IA y MySQL/MariaDB

Este directorio contiene las definiciones DDL oficiales y fixtures con datos estrictamente sintéticos para validar las consultas SQL y el endpoint de generación end-to-end contra una instancia de base de datos aislada, sin interactuar jamás con las bases de datos operativas de DIRPOLES-4.

---

## 1. Contenido de este Directorio

* **`01_schema_business_test.sql`**: Definición DDL oficial (46 tablas) para el esquema de negocio `dirpoles_business_test` (extraída de `dirpoles_business_actualizada.sql`, sin registros operativos ni PII).
* **`02_schema_security_test.sql`**: Definición DDL oficial (11 tablas) para el esquema de seguridad `dirpoles_security_test` (extraída de `dirpoles_security_actualizada.sql`).
* **`03_datos_sinteticos.sql`**: Fixtures con datos mínimos ficticios y relaciones íntegras para los 10 módulos analíticos y el catálogo de 13 PNF institucionales.

---

## 2. Instrucciones de Inicialización (Opción A: Contenedor Docker / Podman)

Para levantar una base de datos MySQL/MariaDB temporal completamente aislada en un puerto alterno (ej. 3307):

```bash
# 1. Iniciar contenedor temporal MariaDB
podman run --name dirpoles-test-db \
  -e MARIADB_ROOT_PASSWORD=root_test_pwd \
  -e MARIADB_USER=dirpoles_test_user \
  -e MARIADB_PASSWORD=clave_test \
  -p 3307:3306 -d mariadb:10.11

# 2. Esperar a que el servidor esté listo
sleep 5

# 3. Cargar los esquemas DDL y los datos sintéticos
mariadb -h 127.0.0.1 -P 3307 -u root -proot_test_pwd < tests/fixtures_bd/01_schema_business_test.sql
mariadb -h 127.0.0.1 -P 3307 -u root -proot_test_pwd < tests/fixtures_bd/02_schema_security_test.sql
mariadb -h 127.0.0.1 -P 3307 -u root -proot_test_pwd < tests/fixtures_bd/03_datos_sinteticos.sql

# 4. Otorgar permisos de SELECT al usuario de pruebas
mariadb -h 127.0.0.1 -P 3307 -u root -proot_test_pwd -e \
  "GRANT SELECT ON dirpoles_business_test.* TO 'dirpoles_test_user'@'%'; GRANT SELECT ON dirpoles_security_test.* TO 'dirpoles_test_user'@'%'; FLUSH PRIVILEGES;"
```

---

## 3. Instrucciones de Ejecución de las Pruebas de Integración

Con el servidor de pruebas levantado y configurado:

```bash
# 1. Exportar variables de entorno de prueba (compatibles con tests/guard_integracion_bd.py)
export DIRPOLES_TEST_BD=1
export DIRPOLES_TEST_DB_HOST=127.0.0.1
export DIRPOLES_TEST_DB_PORT=3307
export DIRPOLES_TEST_DB_USER=dirpoles_test_user
export DIRPOLES_TEST_DB_PASSWORD=clave_test
export DIRPOLES_TEST_DB_NAME_BUSINESS=dirpoles_business_test
export DIRPOLES_TEST_DB_NAME_SECURITY=dirpoles_security_test

# 2. Ejecutar las pruebas de integración reales
PYTHONPATH=. .venv/bin/python -m unittest tests/test_integracion_bd.py
PYTHONPATH=. .venv/bin/python -m unittest tests/test_flujo_bd_api.py
```

---

## 4. Salvaguardas de Seguridad Inviolables

* El guardián [`tests/guard_integracion_bd.py`](../guard_integracion_bd.py) rechazará la ejecución si:
  * Las variables de entorno apuntan a `dirpoles_business` o `dirpoles_security`.
  * Los nombres de los esquemas no contienen `test` o `prueba`.
  * Se intenta reutilizar el `.env` operativo.
