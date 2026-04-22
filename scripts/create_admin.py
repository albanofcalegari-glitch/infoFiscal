#!/usr/bin/env python3
"""
scripts/create_admin.py
Crea el estudio inicial y el primer usuario admin en PostgreSQL.

Ejecutar UNA vez desde la raiz del proyecto:
    python scripts/create_admin.py

Requisitos previos:
    - PostgreSQL corriendo (docker compose up -d)
    - Migraciones aplicadas (python migrations/run_migrations.py)
    - .env con DATABASE_URL configurado
"""

import getpass
import sys
from pathlib import Path

# Permitir imports desde la raiz del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg

from src.config import Config
from src.auth.service import hash_password


def main() -> None:
    print("=" * 50)
    print("  InfoFiscal - Crear usuario admin")
    print("=" * 50)
    print()

    # --- Datos del estudio ---
    estudio_nombre = input("Nombre del estudio [Mi Estudio]: ").strip() or "Mi Estudio"
    estudio_email = input("Email del estudio: ").strip()
    if not estudio_email:
        print("ERROR: El email del estudio es obligatorio.")
        sys.exit(1)

    # --- Datos del admin ---
    admin_nombre = input("Nombre del admin [Administrador]: ").strip() or "Administrador"
    admin_email = input("Email del admin: ").strip()
    if not admin_email:
        print("ERROR: El email del admin es obligatorio.")
        sys.exit(1)

    # --- Password con validacion ---
    while True:
        password = getpass.getpass("Password (min 8 caracteres): ")
        if len(password) < 8:
            print("  Debe tener al menos 8 caracteres.")
            continue
        confirm = getpass.getpass("Confirmar password: ")
        if password != confirm:
            print("  Las passwords no coinciden.")
            continue
        break

    pw_hash = hash_password(password)

    # --- Insertar en DB ---
    print(f"\nCreando estudio '{estudio_nombre}' y admin '{admin_email}'...")

    try:
        with psycopg.connect(Config.DATABASE_URL) as conn:
            with conn.cursor() as cur:
                # Crear estudio (idempotente por email unico)
                cur.execute(
                    """
                    INSERT INTO estudios (nombre, email)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO UPDATE SET nombre = EXCLUDED.nombre
                    RETURNING id
                    """,
                    (estudio_nombre, estudio_email),
                )
                estudio_id = cur.fetchone()[0]

                # Crear usuario admin (idempotente por estudio_id + email)
                cur.execute(
                    """
                    INSERT INTO usuarios (estudio_id, nombre, email, password_hash, rol)
                    VALUES (%s, %s, %s, %s, 'admin')
                    ON CONFLICT (estudio_id, email) DO UPDATE
                        SET password_hash = EXCLUDED.password_hash,
                            nombre = EXCLUDED.nombre,
                            activo = TRUE,
                            intentos_fallidos = 0,
                            bloqueado_hasta = NULL
                    RETURNING id
                    """,
                    (estudio_id, admin_nombre, admin_email, pw_hash),
                )
                admin_id = cur.fetchone()[0]

            conn.commit()

        print()
        print(f"  Estudio creado  (id={estudio_id})")
        print(f"  Admin creado    (id={admin_id}, rol=admin)")
        print()
        print(f"  Ya podes iniciar sesion con: {admin_email}")

    except psycopg.OperationalError as e:
        print(f"\nERROR de conexion: {e}")
        print("Verifica que PostgreSQL este corriendo (docker compose up -d)")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
