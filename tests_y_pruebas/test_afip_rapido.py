# -*- coding: utf-8 -*-
"""Test rápido de autenticación AFIP"""
import sys
import io
import os
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Cargar .env
from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit = os.getenv('AFIP_CUIT')

print("=" * 60)
print("TEST RAPIDO AFIP")
print("=" * 60)

print(f"\n[1] Variables de entorno:")
print(f"    Certificado: {cert_path}")
print(f"    Clave: {key_path}")
print(f"    CUIT: {cuit}")

print(f"\n[2] Verificando archivos:")
print(f"    Cert existe: {os.path.exists(cert_path)}")
print(f"    Key existe: {os.path.exists(key_path)}")

print(f"\n[3] Probando autenticación WSAA...")

try:
    from afip_simple import build_simple_tra, sign_tra_simple

    # Crear TRA
    print("    - Creando TRA...")
    tra = build_simple_tra('wsfe')
    print("    - TRA creado OK")

    # Firmar TRA
    print("    - Firmando TRA...")
    signed = sign_tra_simple(tra, cert_path, key_path)
    print(f"    - TRA firmado OK ({len(signed)} bytes)")

    # Enviar a WSAA
    print("    - Enviando a WSAA...")
    import base64
    import requests
    import xml.etree.ElementTree as ET

    tra_b64 = base64.b64encode(signed).decode('utf-8')

    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    <loginCms xmlns="http://wsaa.view.sua.dvadac.desein.afip.gov">
        <in0>{tra_b64}</in0>
    </loginCms>
</soap:Body>
</soap:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': ''
    }

    # Determinar ambiente
    ambiente = os.getenv('AFIP_ENV', 'prod')
    wsaa_urls = {
        'prod': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
        'homo': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms'
    }

    response = requests.post(
        wsaa_urls[ambiente],
        data=soap_request,
        headers=headers,
        timeout=30,
        verify=False
    )

    print(f"    - Respuesta HTTP: {response.status_code}")

    if response.status_code == 200:
        # Parsear respuesta
        root = ET.fromstring(response.text)
        login_return = None

        for elem in root.iter():
            if 'loginCmsReturn' in elem.tag:
                login_return = elem.text
                break

        if login_return:
            import html
            login_xml = html.unescape(login_return)
            login_root = ET.fromstring(login_xml)

            credentials = {}
            for child in login_root.iter():
                if child.tag in ['token', 'sign']:
                    credentials[child.tag] = child.text

            if 'token' in credentials and 'sign' in credentials:
                print(f"    - TOKEN obtenido: {credentials['token'][:50]}...")
                print(f"    - SIGN obtenido: {credentials['sign'][:50]}...")
                print("\n✅ AUTENTICACION EXITOSA")
            else:
                print("\n❌ No se encontraron token/sign en la respuesta")
        else:
            print("\n❌ No se encontró loginCmsReturn")
    else:
        print(f"\n❌ Error HTTP: {response.status_code}")
        print(f"    Response: {response.text[:200]}")

except Exception as e:
    print(f"\n❌ ERROR: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
