import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL = os.environ["DATABASE_URL"]
    SECRET_KEY = os.environ["SECRET_KEY"]
    SESSION_HOURS = int(os.getenv("SESSION_HOURS", 8))
    MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", 5))
    LOCKOUT_MINUTES = int(os.getenv("LOCKOUT_MINUTES", 15))

    # ── AFIP ──────────────────────────────────────────────────────────
    # CUIT del estudio/contador que posee el certificado digital.
    # Es quien firma el TRA y tiene delegaciones en AFIP.
    # NO es el CUIT del cliente consultado — ese sale de la UI/DB.
    #
    # TODO multi-tenant: este valor debería salir de la tabla `estudios`
    #   (columna cuit_afip o similar), uno por estudio. Cuando se implemente,
    #   reemplazar esta constante global por g.estudio['cuit_afip'] en cada
    #   request, y eliminar esta variable de entorno.
    AFIP_SOLICITANTE_CUIT = os.getenv("AFIP_SOLICITANTE_CUIT", "20321518045")

    # Portal AFIP (scraping RCEL — PVs no cubiertos por Web Services)
    AFIP_PORTAL_CUIT = os.getenv("AFIP_PORTAL_CUIT", "")
    AFIP_PORTAL_PASSWORD = os.getenv("AFIP_PORTAL_PASSWORD", "")