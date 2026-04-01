# -*- coding: utf-8 -*-
"""Verificar detalle del token WSAA"""
import sys
import io
import os
import base64
import xml.etree.ElementTree as ET
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv('.env')

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit_cert = os.getenv('AFIP_CUIT')

print("=" * 70)
print("ANALISIS DETALLADO DEL TOKEN")
print("=" * 70)

from wsfev1_client import WSFEv1Client

# Test 1: Token para 27312238018
print("\n[TEST 1] Token autenticando CON cuit 27312238018:")
client1 = WSFEv1Client(cert_path, key_path, 'prod')
try:
    token1, sign1 = client1.autenticar_wsaa('27312238018')

    # Decodificar token
    token_xml = base64.b64decode(token1).decode('utf-8')
    print(f"\nToken decodificado (primeros 500 chars):")
    print(token_xml[:500])

    # Buscar CUIT en el token
    if 'destination' in token_xml:
        print("\n✓ Campo 'destination' encontrado en token")

    # Parsear XML
    root = ET.fromstring(token_xml)
    for elem in root.iter():
        if 'destination' in elem.tag.lower():
            print(f"   destination: {elem.text}")
        if 'source' in elem.tag.lower():
            print(f"   source: {elem.text}")

except Exception as e:
    print(f"ERROR: {e}")

# Test 2: Token para el CUIT del certificado
print("\n" + "=" * 70)
print(f"[TEST 2] Token autenticando CON cuit del certificado ({cuit_cert}):")
client2 = WSFEv1Client(cert_path, key_path, 'prod')
try:
    token2, sign2 = client2.autenticar_wsaa(cuit_cert)

    # Decodificar token
    token_xml2 = base64.b64decode(token2).decode('utf-8')
    print(f"\nToken decodificado (primeros 500 chars):")
    print(token_xml2[:500])

    # Parsear XML
    root2 = ET.fromstring(token_xml2)
    for elem in root2.iter():
        if 'destination' in elem.tag.lower():
            print(f"   destination: {elem.text}")
        if 'source' in elem.tag.lower():
            print(f"   source: {elem.text}")

except Exception as e:
    print(f"ERROR: {e}")

# Test 3: Probar consulta con el token del certificado pero indicando el CUIT cliente
print("\n" + "=" * 70)
print("[TEST 3] Intentar consultar factura de Regina usando token propio:")
print("   Token de: 20321518045")
print("   Consultando facturas de: 27312238018")
print("=" * 70)

try:
    # Autenticar con CUIT propio
    token_propio, sign_propio = client2.autenticar_wsaa(cuit_cert)

    # Intentar consultar último de Regina
    params = {
        'tipo_comprobante': 11,
        'punto_venta': 2
    }

    # Hacer request usando CUIT de Regina en el campo Auth/Cuit
    xml_response = client2._wsfe_request(
        'FECompUltimoAutorizado',
        params,
        token_propio,
        sign_propio,
        '27312238018'  # CUIT del cliente
    )

    print("\nRespuesta (primeros 800 chars):")
    print(xml_response[:800])

    # Buscar si hay último número
    root = ET.fromstring(xml_response)
    for elem in root.iter():
        if 'CbteNro' in elem.tag and elem.text:
            print(f"\n✓ Último comprobante: {elem.text}")
        if 'Code' in elem.tag and elem.text:
            print(f"   Error Code: {elem.text}")
        if 'Msg' in elem.tag and elem.text:
            print(f"   Error Msg: {elem.text[:100]}")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("""
HIPOTESIS:
1. El token se genera con un CUIT específico (el del TRA)
2. AFIP valida que el CUIT en <Auth><Cuit> coincida o tenga relación
3. La delegación debe estar EN EL SENTIDO CORRECTO:
   - Cliente (27312238018) delega AL contador (20321518045) ✓
4. Pero el certificado debe estar asociado al CUIT correcto

PROBLEMA POSIBLE:
- El certificado podría no estar correctamente asociado en AFIP
- O necesitamos autenticar con el CUIT propio (20321518045)
  y luego usar ese token para consultar clientes delegados
""")
