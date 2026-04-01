# -*- coding: utf-8 -*-
"""Buscar facturas específicas del CUIT 27312238018"""
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
ambiente = os.getenv('AFIP_ENV', 'prod')

CUIT = '27312238018'
PUNTO_VENTA = 2  # 0002
TIPO_COMPROBANTE = 11  # Factura C
NUMEROS = [235, 236]  # Facturas específicas

print("=" * 70)
print(f"BUSQUEDA DE FACTURAS ESPECIFICAS")
print(f"CUIT: {CUIT}")
print(f"Punto de Venta: {PUNTO_VENTA:04d}")
print(f"Tipo: Factura C (11)")
print(f"Números: {NUMEROS}")
print("=" * 70)

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, ambiente)

facturas_encontradas = []

# 1. Obtener último comprobante autorizado
print(f"\n[1] Consultando último comprobante autorizado...")
try:
    ultimo = client.obtener_ultimo_comprobante(CUIT, TIPO_COMPROBANTE, PUNTO_VENTA)
    print(f"    Último número autorizado: {ultimo}")
except Exception as e:
    print(f"    ERROR: {e}")
    ultimo = None

# 2. Consultar facturas específicas
print(f"\n[2] Consultando facturas específicas...")
for num in NUMEROS:
    print(f"\n    Factura {PUNTO_VENTA:04d}-{num:08d}:")
    try:
        comp = client.consultar_comprobante(CUIT, TIPO_COMPROBANTE, PUNTO_VENTA, num)

        if comp:
            print(f"      ✓ ENCONTRADA")
            print(f"      - CAE: {comp.get('CAE', comp.get('cae', 'N/A'))}")
            print(f"      - Fecha: {comp.get('CbteFch', comp.get('fecha_emision', 'N/A'))}")
            print(f"      - Importe: ${comp.get('ImpTotal', comp.get('importe_total', 'N/A'))}")
            print(f"      - Moneda: {comp.get('MonId', 'N/A')}")
            print(f"      - Receptor Doc: {comp.get('DocNro', 'N/A')}")

            facturas_encontradas.append({
                'numero': num,
                'numero_formato': f"{PUNTO_VENTA:04d}-{num:08d}",
                'datos': comp
            })
        else:
            print(f"      ✗ No encontrada o sin datos")

    except Exception as e:
        print(f"      ✗ ERROR: {e}")

# 3. Si encontramos el último, buscar rango alrededor de 235-236
if ultimo and ultimo >= 230:
    print(f"\n[3] Buscando en rango {max(1, ultimo-20)} a {ultimo}...")

    for num in range(max(1, ultimo - 20), ultimo + 1):
        if num in NUMEROS:
            continue  # Ya lo consultamos

        try:
            comp = client.consultar_comprobante(CUIT, TIPO_COMPROBANTE, PUNTO_VENTA, num)

            if comp:
                fecha = comp.get('CbteFch', comp.get('fecha_emision', 'N/A'))
                importe = comp.get('ImpTotal', comp.get('importe_total', 'N/A'))
                print(f"    {PUNTO_VENTA:04d}-{num:08d}: ${importe} ({fecha})")

                facturas_encontradas.append({
                    'numero': num,
                    'numero_formato': f"{PUNTO_VENTA:04d}-{num:08d}",
                    'datos': comp
                })
        except:
            continue

# Resultados
print("\n" + "=" * 70)
print("RESULTADOS")
print("=" * 70)

if facturas_encontradas:
    print(f"\nTotal facturas encontradas: {len(facturas_encontradas)}")

    print("\nDetalle completo:")
    for i, fact in enumerate(facturas_encontradas, 1):
        datos = fact['datos']
        print(f"\n{i}. Factura C {fact['numero_formato']}")
        print(f"   CAE: {datos.get('CAE', datos.get('cae', 'N/A'))}")
        print(f"   Fecha: {datos.get('CbteFch', datos.get('fecha_emision', 'N/A'))}")
        print(f"   Importe Total: ${datos.get('ImpTotal', datos.get('importe_total', 'N/A'))}")
        print(f"   Importe Neto: ${datos.get('ImpNeto', 'N/A')}")
        print(f"   IVA: ${datos.get('ImpIVA', 'N/A')}")
        print(f"   Moneda: {datos.get('MonId', 'N/A')}")
        print(f"   Receptor Doc Tipo: {datos.get('DocTipo', 'N/A')}")
        print(f"   Receptor Doc Nro: {datos.get('DocNro', 'N/A')}")
        print(f"   Concepto: {datos.get('Concepto', 'N/A')}")

    # Guardar a JSON
    import json
    output_file = f'facturas_{CUIT}_detalle.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(facturas_encontradas, f, ensure_ascii=False, indent=2)
    print(f"\nFacturas guardadas en: {output_file}")

else:
    print("\n❌ No se encontraron facturas")
    print("\nPosibles causas:")
    print("  1. Las facturas están en otro punto de venta")
    print("  2. Se requiere autorización específica en AFIP")
    print("  3. El ambiente (prod/homo) no coincide")
    print("  4. El certificado no tiene permisos para este CUIT")

print("\n" + "=" * 70)
