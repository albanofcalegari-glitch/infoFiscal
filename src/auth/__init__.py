"""
src/auth/__init__.py
Blueprint de autenticacion.

Rutas:
    GET  /auth/login   -> render login.html
    POST /auth/login   -> authenticate, redirect a /home
    GET  /auth/logout  -> revocar sesion, redirect a /auth/login
"""

from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from src.auth.service import authenticate, revoke_session

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    """Muestra el formulario de login."""
    return render_template("login.html", error=None)


@auth_bp.route("/login", methods=["POST"])
def login():
    """Procesa el login contra PostgreSQL."""
    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Complete todos los campos.")

    result = authenticate(
        email=email,
        password=password,
        ip=request.remote_addr,
        user_agent=(request.headers.get("User-Agent") or "")[:256],
    )

    if not result["ok"]:
        return render_template("login.html", error=result["reason"])

    # Guardar token en la cookie-session de Flask
    session.clear()
    session.permanent = True  # sobrevive cierre de browser
    session["session_token"] = result["token"]
    # Backward-compat: las rutas legacy de app.py verifican 'usuario' in session
    session["usuario"] = result["user"]["nombre"]

    return redirect(url_for("home"))


@auth_bp.route("/logout")
def logout():
    """Revoca la sesion en DB y limpia la cookie."""
    token = session.get("session_token")
    if token:
        revoke_session(token)
    session.clear()
    return redirect(url_for("auth.login_page"))
