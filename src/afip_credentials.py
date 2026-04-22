# src/afip_credentials.py
# Carga credenciales AFIP desde la DB por estudio.
#
# Retrocompatible: si no hay registro en estudios_afip, usa los valores
# de Config (.env) como fallback para no romper la instalación existente.

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from src.config import Config
from src.db import get_cursor


def get_afip_credentials(estudio_id: int | None) -> dict:
    """Obtener credenciales AFIP para un estudio.

    Retorna dict con:
        solicitante_cuit, cert_path, key_path, ambiente,
        portal_cuit, portal_password
    """
    # Intentar cargar de DB
    if estudio_id is not None:
        creds = _load_from_db(estudio_id)
        if creds:
            return creds

    # Fallback: Config (.env) — retrocompatible
    root_dir = Path(__file__).parent.parent
    return {
        'solicitante_cuit': Config.AFIP_SOLICITANTE_CUIT,
        'cert_path': str(root_dir / 'certs' / 'certificado.crt'),
        'key_path': str(root_dir / 'certs' / 'clave_privada.key'),
        'ambiente': os.getenv('AFIP_ENV', 'prod'),
        'portal_cuit': Config.AFIP_PORTAL_CUIT,
        'portal_password': Config.AFIP_PORTAL_PASSWORD,
    }


def _load_from_db(estudio_id: int) -> dict | None:
    """Cargar credenciales AFIP de la tabla estudios_afip."""
    try:
        with get_cursor() as cur:
            cur.execute("""
                SELECT solicitante_cuit, cert_path, cert_blob, key_path, key_blob,
                       ambiente, portal_cuit, portal_password_enc
                FROM estudios_afip
                WHERE estudio_id = %s AND activo = TRUE
                  AND ambiente = 'prod'
                ORDER BY id DESC LIMIT 1
            """, (estudio_id,))
            row = cur.fetchone()

        if not row:
            return None

        # Resolver cert y key: blob tiene prioridad sobre path
        cert_path = _resolve_cert(row['cert_blob'], row['cert_path'], 'cert')
        key_path = _resolve_cert(row['key_blob'], row['key_path'], 'key')

        if not cert_path or not key_path:
            return None

        # Desencriptar portal password si existe
        portal_password = ''
        if row['portal_password_enc']:
            portal_password = _decrypt_portal_password(row['portal_password_enc'])

        return {
            'solicitante_cuit': row['solicitante_cuit'],
            'cert_path': cert_path,
            'key_path': key_path,
            'ambiente': row['ambiente'],
            'portal_cuit': row['portal_cuit'] or '',
            'portal_password': portal_password,
        }

    except Exception as e:
        print(f"[AFIP_CREDS] Error cargando de DB para estudio {estudio_id}: {e}")
        return None


def _resolve_cert(blob: bytes | None, path: str | None, prefix: str) -> str | None:
    """Resolver certificado: si hay blob, escribir a temp file. Si hay path, verificar."""
    if blob:
        tmp = tempfile.NamedTemporaryFile(
            prefix=f'afip_{prefix}_', suffix='.pem', delete=False
        )
        tmp.write(blob)
        tmp.close()
        return tmp.name

    if path:
        # Path absoluto o relativo a la raíz del proyecto
        p = Path(path)
        if not p.is_absolute():
            p = Path(__file__).parent.parent / p
        if p.exists():
            return str(p)

    return None


def _decrypt_portal_password(encrypted: str) -> str:
    """Desencriptar password del portal AFIP usando Fernet."""
    try:
        from cryptography.fernet import Fernet
        import hashlib
        import base64
        # Derivar key de Fernet desde SECRET_KEY
        key = base64.urlsafe_b64encode(
            hashlib.sha256(Config.SECRET_KEY.encode()).digest()
        )
        f = Fernet(key)
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        # Si no se puede desencriptar, devolver vacío
        return ''


def encrypt_portal_password(plain: str) -> str:
    """Encriptar password del portal AFIP para guardar en DB."""
    from cryptography.fernet import Fernet
    import hashlib
    import base64
    key = base64.urlsafe_b64encode(
        hashlib.sha256(Config.SECRET_KEY.encode()).digest()
    )
    f = Fernet(key)
    return f.encrypt(plain.encode()).decode()
