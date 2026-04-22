"""
src/auth/service.py
Logica de autenticacion — sin dependencias de Flask.

Columnas referenciadas (001_initial.sql):
  usuarios: id, estudio_id, nombre, email, password_hash, rol,
            activo, ultimo_login, intentos_fallidos, bloqueado_hasta
  sesiones: id (token TEXT PK), usuario_id, ip, user_agent,
            created_at, expires_at, revocada
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from src.config import Config
from src.db import get_cursor


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Genera hash seguro (scrypt por defecto en werkzeug >= 2.3)."""
    return generate_password_hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return check_password_hash(hashed, plain)


# ---------------------------------------------------------------------------
# Autenticacion
# ---------------------------------------------------------------------------

def authenticate(
    email: str,
    password: str,
    ip: str | None = None,
    user_agent: str | None = None,
) -> dict:
    """
    Flujo completo de login.

    Returns
    -------
    Exito:  {"ok": True,  "token": str, "user": dict}
    Fallo:  {"ok": False, "reason": str}
    """
    with get_cursor() as cur:
        # 1. Buscar usuario activo por email
        cur.execute(
            """
            SELECT id, estudio_id, nombre, email, password_hash, rol,
                   intentos_fallidos, bloqueado_hasta
            FROM usuarios
            WHERE email = %s AND activo = TRUE
            LIMIT 1
            """,
            (email,),
        )
        user = cur.fetchone()

        if user is None:
            return {"ok": False, "reason": "Credenciales invalidas."}

        # 1b. Verificar que el estudio esté activo (superadmin no tiene estudio)
        if user["estudio_id"] is not None:
            cur.execute(
                "SELECT activo, membresia_hasta FROM estudios WHERE id = %s",
                (user["estudio_id"],),
            )
            estudio = cur.fetchone()
            if estudio and not estudio["activo"]:
                return {"ok": False, "reason": "Su estudio se encuentra desactivado. Contacte al administrador."}
            if estudio and estudio.get("membresia_hasta"):
                from datetime import date
                if estudio["membresia_hasta"] < date.today():
                    return {"ok": False, "reason": "La membresia de su estudio ha vencido. Contacte al administrador."}

        # 2. Verificar lockout
        if user["bloqueado_hasta"] is not None:
            if user["bloqueado_hasta"] > datetime.now(timezone.utc):
                diff = user["bloqueado_hasta"] - datetime.now(timezone.utc)
                mins_left = int(diff.total_seconds() / 60) + 1
                return {
                    "ok": False,
                    "reason": f"Usuario bloqueado. Intente en {mins_left} minutos.",
                }
            # Lockout vencido: resetear contador
            cur.execute(
                "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = %s",
                (user["id"],),
            )
            user["intentos_fallidos"] = 0

        # 3. Verificar password
        if not verify_password(password, user["password_hash"]):
            new_attempts = user["intentos_fallidos"] + 1

            if new_attempts >= Config.MAX_LOGIN_ATTEMPTS:
                bloqueado_hasta = datetime.now(timezone.utc) + timedelta(
                    minutes=Config.LOCKOUT_MINUTES
                )
                cur.execute(
                    """
                    UPDATE usuarios
                    SET intentos_fallidos = %s, bloqueado_hasta = %s
                    WHERE id = %s
                    """,
                    (new_attempts, bloqueado_hasta, user["id"]),
                )
                return {
                    "ok": False,
                    "reason": f"Usuario bloqueado por {Config.LOCKOUT_MINUTES} minutos.",
                }

            cur.execute(
                "UPDATE usuarios SET intentos_fallidos = %s WHERE id = %s",
                (new_attempts, user["id"]),
            )
            remaining = Config.MAX_LOGIN_ATTEMPTS - new_attempts
            return {
                "ok": False,
                "reason": f"Credenciales invalidas. {remaining} intentos restantes.",
            }

        # 4. Login exitoso — resetear intentos, registrar timestamp
        cur.execute(
            """
            UPDATE usuarios
            SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_login = NOW()
            WHERE id = %s
            """,
            (user["id"],),
        )

        # 5. Crear sesion server-side
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=Config.SESSION_HOURS)

        cur.execute(
            """
            INSERT INTO sesiones (id, usuario_id, ip, user_agent, expires_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (token, user["id"], ip, user_agent, expires_at),
        )

        return {
            "ok": True,
            "token": token,
            "user": {
                "id": user["id"],
                "estudio_id": user["estudio_id"],
                "nombre": user["nombre"],
                "email": user["email"],
                "rol": user["rol"],
            },
        }


# ---------------------------------------------------------------------------
# Validacion / revocacion de sesiones
# ---------------------------------------------------------------------------

def validate_session(token: str) -> dict | None:
    """
    Valida token de sesion contra la DB.
    Retorna dict con datos del usuario si es valida, None si no.
    """
    with get_cursor() as cur:
        cur.execute(
            """
            SELECT u.id, u.estudio_id, u.nombre, u.email, u.rol
            FROM sesiones s
            JOIN usuarios u ON u.id = s.usuario_id
            WHERE s.id = %s
              AND s.revocada = FALSE
              AND s.expires_at > NOW()
              AND u.activo = TRUE
            """,
            (token,),
        )
        return cur.fetchone()


def revoke_session(token: str) -> None:
    """Marca una sesion como revocada (logout)."""
    with get_cursor() as cur:
        cur.execute(
            "UPDATE sesiones SET revocada = TRUE WHERE id = %s",
            (token,),
        )


def cleanup_expired_sessions() -> int:
    """Elimina sesiones expiradas o revocadas. Retorna cantidad eliminada."""
    with get_cursor() as cur:
        cur.execute(
            "DELETE FROM sesiones WHERE revocada = TRUE OR expires_at < NOW()"
        )
        return cur.rowcount
