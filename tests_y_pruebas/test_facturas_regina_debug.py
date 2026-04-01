# -*- coding: utf-8 -*-
"""Test debug específico para facturas de Regina Cereto"""
import sys
import io
import os
from pathlib import Path

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv('.env')

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit_consultor = os.getenv('AFIP_CUIT')  # 20321518045

CUIT_REGINA = '27312238018'
PV = 2
TIPO = 11  # Factura C
NUMEROS = [235, 236, 237, 238, 234, 233]  # Probar varios

print("=" * 70)
print("TEST DEBUG - FACTURAS REGINA CERETO")
print("=" * 70)
print(f"Consultor CUIT: {cuit_consultor}")
print(f"Cliente CUIT: {CUIT_REGINA}")
print(f"Punto Venta: {PV:04d}")
print(f"Tipo: Factura C (11)")
print("=" * 70)

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, 'prod')

# 1. Verificar autenticación
print("\n[1] Autenticando con WSAA...")
try:
    token, sign = client.autenticar_wsaa(CUIT_REGINA)
    print(f"    Token (primeros 50): {token[:50]}...")
    print(f"    Sign (primeros 50): {sign[:50]}...")
    print("    ✓ Autenticación exitosa")
except Exception as e:
    print(f"    ✗ Error: {e}")
    sys.exit(1)

# 2. Consultar último autorizado
print(f"\n[2] Consultando último autorizado PV {PV:04d}...")
try:
    ultimo = client.obtener_ultimo_comprobante(CUIT_REGINA, TIPO, PV)
    print(f"    Último: {ultimo}")

    if ultimo == 0:
        print("    ⚠️ ATENCION: Último = 0 podría significar:")
        print("       - No hay permisos para consultar")
        print("       - El PV no existe para este CUIT")
        print("       - Las facturas están en otro servicio")
except Exception as e:
    print(f"    ✗ Error: {e}")

# 3. Consultar facturas específicas CON FULL DEBUG
print(f"\n[3] Consultando facturas específicas (CON DEBUG COMPLETO)...")

for num in NUMEROS:
    print(f"\n    --- Factura {PV:04d}-{num:08d} ---")

    try:
        # Hacer request directo para ver respuesta completa
        params = {
            'tipo_comprobante': TIPO,
            'punto_venta': PV,
            'numero': num
        }

        xml_response = client._wsfe_request(
            'FECompConsultar',
            params,
            token,
            sign,
            CUIT_REGINA
        )

        print(f"    XML completo (primeros 1000 chars):")
        print(f"    {xml_response[:1000]}")
        print()

        # Buscar errores en el XML
        if '<Errors>' in xml_response or '<Error>' in xml_response:
            print("    ⚠️ La respuesta contiene errores:")

            import xml.etree.ElementTree as ET
            root = ET.fromstring(xml_response)

            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag in ['Code', 'Msg', 'Obs']:
                    print(f"       {tag}: {elem.text}")

        # Intentar parsear como comprobante
        comp = client.consultar_comprobante(CUIT_REGINA, TIPO, PV, num)

        if comp and ('CAE' in comp or 'cae' in comp):
            print(f"    ✓ ENCONTRADO")
            print(f"       CAE: {comp.get('CAE', comp.get('cae'))}")
            print(f"       Fecha: {comp.get('CbteFch', comp.get('fecha_emision'))}")
            print(f"       Importe: ${comp.get('ImpTotal', comp.get('importe_total'))}")
        else:
            print(f"    ✗ No encontrado o sin datos")

    except Exception as e:
        print(f"    ✗ Error: {e}")
        import traceback
        print(f"    Traceback: {traceback.format_exc()[:300]}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("\nSi todas las consultas devuelven 'No encontrado':")
print("  1. Verificar delegación en AFIP → Administrador de Relaciones")
print("  2. El servicio delegado debe ser: 'Facturación Electrónica'")
print("  3. El CUIT consultor (20321518045) debe tener permiso EXPLÍCITO")
print("  4. La delegación debe incluir el servicio 'wsfe' o 'wsfev1'")
print("\nSi hay error 'No autorizado' o similar:")
print("  → Falta la delegación o expiró")
print("\n" + "=" * 70)
