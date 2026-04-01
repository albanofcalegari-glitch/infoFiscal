#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrations/run_migrations.py
Aplica migraciones SQL en orden numérico. Idempotente.

Uso (desde la raíz del proyecto):
    python migrations/run_migrations.py

Comportamiento:
    - Crea la tabla schema_migrations si no existe.
    - Lee todos los archivos *.sql de esta carpeta, ordenados por nombre.
    - Aplica solo los que no estén registrados en schema_migrations.
    - Cada migración se aplica en una transacción propia.
    - Si una migración falla, se detiene y muestra el error. No continúa.
"""

import os
import sys
from pathlib import Path

# Permitir imports desde la raíz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg

DATABASE_URL   = os.environ.get("DATABASE_URL")
MIGRATIONS_DIR = Path(__file__).parent

# Tabla de control — no usa el esquema de negocio, es infraestructura del runner.
INIT_SQL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    filename    TEXT         PRIMARY KEY,
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);
"""


def get_applied(conn) -> set[str]:
    result = conn.execute("SELECT filename FROM schema_migrations ORDER BY filename")
    return {row[0] for row in result.fetchall()}


def run() -> None:
    if not DATABASE_URL:
        print("ERROR: DATABASE_URL no está definida en .env")
        sys.exit(1)

    print(f"Conectando a PostgreSQL...")

    try:
        with psycopg.connect(DATABASE_URL) as conn:

            # Crear tabla de control si no existe
            conn.execute(INIT_SQL)
            conn.commit()

            applied = get_applied(conn)

            # Todos los .sql de este directorio, en orden numérico
            sql_files = sorted(
                f for f in MIGRATIONS_DIR.glob("*.sql")
            )

            if not sql_files:
                print("No se encontraron archivos .sql en migrations/")
                return

            pending = [f for f in sql_files if f.name not in applied]

            if not pending:
                print("Todas las migraciones ya están aplicadas.")
                for f in sql_files:
                    print(f"  [ok] {f.name}")
                return

            # Mostrar estado completo
            for f in sql_files:
                estado = "[ok]     " if f.name in applied else "[pendiente]"
                print(f"  {estado} {f.name}")

            print()

            applied_count = 0
            for sql_file in pending:
                print(f"Aplicando {sql_file.name}...")
                sql = sql_file.read_text(encoding="utf-8")

                try:
                    # Cada migración en su propia transacción
                    conn.execute(sql)
                    conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES (%s)",
                        (sql_file.name,)
                    )
                    conn.commit()
                    print(f"  OK — {sql_file.name}")
                    applied_count += 1

                except Exception as e:
                    conn.rollback()
                    print(f"\nERROR aplicando {sql_file.name}:")
                    print(f"  {e}")
                    print("Migraciones detenidas. Corregí el error y reintentá.")
                    sys.exit(1)

            print(f"\n{applied_count} migración(es) aplicada(s) correctamente.")

    except psycopg.OperationalError as e:
        print(f"\nNo se pudo conectar a la base de datos:")
        print(f"  {e}")
        print("\nVerificá que PostgreSQL esté corriendo (docker compose up -d)")
        print(f"  DATABASE_URL={DATABASE_URL}")
        sys.exit(1)


if __name__ == "__main__":
    run()
