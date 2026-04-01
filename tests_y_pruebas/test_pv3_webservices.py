# -*- coding: utf-8 -*-
"""Test con punto de venta 3 - Web Services"""
import sys
import io
import os

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from dotenv import load_dotenv
load_dotenv('.env')

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit = '20321518045'

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, 'prod')

print("=" * 70)
print("TEST - PUNTO DE VENTA 3 (WEB SERVICES)")
print("=" * 70)

print("\n[1] Probando PV 1, 2 y 3 con Factura C:")
for pv in [1, 2, 3]:
    try:
        ultimo = client.obtener_ultimo_comprobante(cuit, 11, pv)
        print(f"    PV {pv}: Ultimo = {ultimo}")
    except Exception as e:
        print(f"    PV {pv}: Error - {str(e)[:50]}")

print("\n[2] Probando PV 3 con diferentes tipos de comprobante:")
for tipo in [11, 6, 51, 1]:
    try:
        ultimo = client.obtener_ultimo_comprobante(cuit, tipo, 3)
        nombre_tipo = client.tipos_comprobante.get(tipo, f'Tipo {tipo}')
        print(f"    {nombre_tipo}: Ultimo = {ultimo}")

        # Si hay facturas, consultar la última
        if ultimo and ultimo > 0:
            print(f"      -> Consultando factura {ultimo}...")
            comp = client.consultar_comprobante(cuit, tipo, 3, ultimo)
            if comp:
                print(f"         CAE: {comp.get('CAE', 'N/A')}")
                print(f"         Fecha: {comp.get('CbteFch', 'N/A')}")
                print(f"         Importe: ${comp.get('ImpTotal', 'N/A')}")
    except Exception as e:
        nombre_tipo = client.tipos_comprobante.get(tipo, f'Tipo {tipo}')
        print(f"    {nombre_tipo}: Error - {str(e)[:50]}")

print("\n[3] Ahora probando con CUIT de Regina (27312238018):")
print("    (Para verificar si las delegaciones funcionan ahora)")

for pv in [2, 3]:
    try:
        ultimo = client.obtener_ultimo_comprobante('27312238018', 11, pv)
        print(f"    Regina PV {pv}: Ultimo = {ultimo}")

        if ultimo and ultimo > 0:
            print(f"      -> Consultando últimas 3 facturas...")
            for num in range(max(1, ultimo-2), ultimo+1):
                comp = client.consultar_comprobante('27312238018', 11, pv, num)
                if comp:
                    print(f"         {pv:04d}-{num:08d}: ${comp.get('ImpTotal', 'N/A')} - {comp.get('CbteFch', 'N/A')}")
    except Exception as e:
        print(f"    Regina PV {pv}: Error - {str(e)[:80]}")

print("\n" + "=" * 70)
print("CONCLUSION")
print("=" * 70)
print("""
Si ves facturas para tu CUIT (20321518045):
  -> Web Services FUNCIONANDO para vos

Si ves facturas de Regina (27312238018):
  -> Delegaciones FUNCIONANDO correctamente

Si NO ves facturas de Regina:
  -> Aun hay un problema con las delegaciones
  -> Revisar permisos en Administrador de Relaciones
""")
