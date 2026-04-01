# -*- coding: utf-8 -*-
"""Diagnóstico completo de servicios AFIP"""
import sys
import io
import os
from pathlib import Path

# Configurar encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv('.env')

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit = os.getenv('AFIP_CUIT')

print("=" * 70)
print("DIAGNOSTICO COMPLETO AFIP")
print("=" * 70)
print(f"\nCUIT: {cuit}")
print(f"Cert: {cert_path}")
print(f"Key: {key_path}")

# 1. WSFEv1
print("\n" + "=" * 70)
print("[1] WSFEv1 - Factura Electrónica Tradicional")
print("=" * 70)

try:
    from wsfev1_client import WSFEv1Client
    client_wsfe = WSFEv1Client(cert_path, key_path, 'prod')

    # Probar con varios puntos de venta
    print("\nProbando puntos de venta 1-5 con Factura C:")
    for pv in range(1, 6):
        ultimo = client_wsfe.obtener_ultimo_comprobante(cuit, 11, pv)
        if ultimo and ultimo > 0:
            print(f"  PV {pv}: Último = {ultimo} ✓")
        else:
            print(f"  PV {pv}: Sin facturas")

except Exception as e:
    print(f"ERROR WSFEv1: {e}")

# 2. WSMTXCA
print("\n" + "=" * 70)
print("[2] WSMTXCA - Monotributo con Codificación")
print("=" * 70)

try:
    from src.wsmtxca_client import WSMTXCAClient
    client_mtx = WSMTXCAClient(cert_path, key_path, 'prod')

    # Autenticar
    print("\nAutenticando...")
    token, sign = client_mtx.autenticar_wsaa(cuit)
    print(f"Token obtenido: {token[:30]}... ✓")

    # Consultar comprobante de prueba
    print("\nConsultando comprobante PV 1, Nro 1:")
    try:
        resultado = client_mtx.consultar_comprobante(cuit, 11, 1, 1)
        if resultado:
            print(f"  Comprobante encontrado ✓")
        else:
            print(f"  Sin datos")
    except Exception as e:
        print(f"  Error: {str(e)[:80]}")

except Exception as e:
    print(f"ERROR WSMTXCA: {e}")

# 3. Verificar certificado
print("\n" + "=" * 70)
print("[3] INFORMACION DEL CERTIFICADO")
print("=" * 70)

try:
    import subprocess

    # Leer info del certificado
    cmd = ['openssl', 'x509', '-in', cert_path, '-noout', '-subject', '-dates']
    try:
        openssl_path = 'C:\\Program Files\\Git\\mingw64\\bin\\openssl.exe'
        result = subprocess.run([openssl_path, 'x509', '-in', cert_path, '-noout', '-text'],
                              capture_output=True, text=True, timeout=10)

        if result.returncode == 0:
            # Buscar CUIT en el certificado
            for line in result.stdout.split('\n'):
                if 'Subject:' in line or 'CN' in line or 'serialNumber' in line:
                    print(f"  {line.strip()}")
                if 'Not Before' in line or 'Not After' in line:
                    print(f"  {line.strip()}")
        else:
            print("  No se pudo leer el certificado")
    except Exception as e:
        print(f"  Error leyendo certificado: {e}")

except Exception as e:
    print(f"ERROR: {e}")

# 4. Probar servicio de padron
print("\n" + "=" * 70)
print("[4] CONSULTA DE PADRON (información del CUIT)")
print("=" * 70)

try:
    # Usando WSFEV1, consultar datos del contribuyente
    print(f"\nConsultando datos de {cuit} en AFIP...")
    print("(Esta consulta podría dar info sobre estado y permisos)")

    # Nota: Esto requeriría ws_sr_padron_a4 o a5
    print("  [INFO] Se requiere servicio ws_sr_padron para consulta de padrón")

except Exception as e:
    print(f"ERROR: {e}")

print("\n" + "=" * 70)
print("FIN DEL DIAGNOSTICO")
print("=" * 70)

print("\n📋 CONCLUSIONES:")
print(f"  - Si WSFEv1 no encuentra facturas, podrían estar en WSMTXCA")
print(f"  - Si sos monotributo, es posible que uses WSMTXCA")
print(f"  - El certificado debe coincidir con el CUIT consultado")
print(f"  - Las delegaciones deben estar activas en AFIP")
