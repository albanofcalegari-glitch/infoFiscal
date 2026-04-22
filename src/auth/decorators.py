"""
src/auth/decorators.py
Decoradores de autenticacion para rutas Flask.

Uso:
    @app.route("/ruta-protegida")
    @login_required
    def mi_ruta():
        user = g.user  # dict con id, estudio_id, nombre, email, rol
        ...

    @app.route("/solo-admin")
    @login_required
    @role_required("admin", "superadmin")
    def panel_admin():
        ...
"""

from __future__ import annotations

from functools import wraps

from flask import g, jsonify, redirect, render_template, request, session, url_for

from src.auth.service import validate_session


def login_required(f):
    """
    Protege una ruta.
    - Valida session_token contra PostgreSQL.
    - Inyecta g.user (dict) con los datos del usuario.
    - Si falla: redirect a login (paginas) o 401 JSON (APIs/AJAX).
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        token = session.get("session_token")

        if not token:
            return _unauthorized()

        user = validate_session(token)

        if user is None:
            # Token invalido o expirado — limpiar cookie
            session.pop("session_token", None)
            session.pop("usuario", None)
            return _unauthorized()

        g.user = user
        return f(*args, **kwargs)

    return decorated


def role_required(*roles: str):
    """
    Requiere que g.user.rol sea uno de los roles indicados.
    Usar DESPUES de @login_required.
    """

    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not hasattr(g, "user") or g.user["rol"] not in roles:
                if _wants_json():
                    return jsonify({"error": "No tiene permisos para esta accion"}), 403
                return render_template("403.html"), 403
            return f(*args, **kwargs)

        return decorated

    return decorator


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------


def _wants_json() -> bool:
    """Heuristica para detectar si el cliente espera JSON."""
    return (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )


def _unauthorized():
    """Respuesta apropiada cuando no hay sesion valida."""
    if _wants_json():
        return jsonify({"error": "No autorizado"}), 401
    return redirect(url_for("auth.login_page"))
