#!/usr/bin/env python3
"""
scripts/create_user.py
Crea un usuario en un estudio existente.

Uso desde la raiz del proyecto:
    python scripts/create_user.py

Requisitos:
    - PostgreSQL corriendo (docker compose up -d)
    - Migraciones aplicadas
    - Al menos un estudio creado (via create_admin.py)
"""

import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import psycopg

from src.config import Config
from src.auth.service import hash_password

ROLES_PERMITIDOS = ("admin", "contador", "readonly")


def main() -> None:
    print("=" * 50)
    print("  InfoFiscal - Crear usuario")
    print("=" * 50)
    print()

    try:
        conn = psycopg.connect(Config.DATABASE_URL)
    except psycopg.OperationalError as e:
        print(f"ERROR de conexion: {e}")
        print("Verifica que PostgreSQL este corriendo (docker compose up -d)")
        sys.exit(1)

    # --- 1. Seleccionar estudio ---
    with conn.cursor() as cur:
        cur.execute("SELECT id, nombre, email FROM estudios WHERE activo = TRUE ORDER BY id")
        estudios = cur.fetchall()

    if not estudios:
        print("ERROR: No hay estudios creados. Ejecuta primero:")
        print("  python scripts/create_admin.py")
        conn.close()
        sys.exit(1)

    print("Estudios disponibles:")
    for est_id, est_nombre, est_email in estudios:
        print(f"  [{est_id}] {est_nombre} ({est_email})")
    print()

    if len(estudios) == 1:
        estudio_id = estudios[0][0]
        print(f"Estudio seleccionado automaticamente: {estudios[0][1]}")
    else:
        while True:
            try:
                estudio_id = int(input("ID del estudio: ").strip())
                if estudio_id in [e[0] for e in estudios]:
                    break
                print("  ID no valido.")
            except ValueError:
                print("  Ingrese un numero.")
    print()

    # --- 2. Datos del usuario ---
    nombre = input("Nombre completo: ").strip()
    if not nombre:
        print("ERROR: El nombre es obligatorio.")
        conn.close()
        sys.exit(1)

    email = input("Email: ").strip()
    if not email:
        print("ERROR: El email es obligatorio.")
        conn.close()
        sys.exit(1)

    # Verificar que no exista
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM usuarios WHERE estudio_id = %s AND email = %s",
            (estudio_id, email),
        )
        if cur.fetchone():
            print(f"\nERROR: Ya existe un usuario con email '{email}' en este estudio.")
            conn.close()
            sys.exit(1)

    # --- 3. Rol ---
    print(f"\nRoles disponibles: {', '.join(ROLES_PERMITIDOS)}")
    while True:
        rol = input("Rol [contador]: ").strip().lower() or "contador"
        if rol in ROLES_PERMITIDOS:
            break
        print(f"  Rol invalido. Opciones: {', '.join(ROLES_PERMITIDOS)}")

    # --- 4. Password ---
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

    # --- 5. Insertar ---
    print(f"\nCreando usuario '{nombre}' ({rol}) en estudio {estudio_id}...")

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO usuarios (estudio_id, nombre, email, password_hash, rol)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (estudio_id, nombre, email, pw_hash, rol),
            )
            user_id = cur.fetchone()[0]
        conn.commit()

        print()
        print(f"  Usuario creado (id={user_id}, rol={rol})")
        print(f"  Ya puede iniciar sesion con: {email}")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
