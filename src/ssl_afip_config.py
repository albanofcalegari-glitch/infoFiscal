#!/usr/bin/env python3
"""
Configuración SSL personalizada para AFIP
Soluciona el problema "DH_KEY_TOO_SMALL" 
"""

import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class AFIPHTTPSAdapter(HTTPAdapter):
    """Adaptador HTTPS personalizado para AFIP"""
    
    def init_poolmanager(self, *args, **pool_kwargs):
        # Crear contexto SSL personalizado para AFIP
        context = create_urllib3_context()
        context.set_ciphers('DEFAULT@SECLEVEL=1')  # Permitir cifrados más antiguos
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        pool_kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **pool_kwargs)

def crear_session_afip():
    """Crear sesión requests configurada para AFIP"""
    session = requests.Session()
    session.mount('https://', AFIPHTTPSAdapter())
    session.verify = False  # Desactivar verificación SSL para AFIP
    
    return session

# Configurar warnings SSL
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)