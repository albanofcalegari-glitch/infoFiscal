# -*- coding: utf-8 -*-
"""Búsqueda exhaustiva de facturas propias - CUIT 20321518045"""
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
cuit = os.getenv('AFIP_CUIT')  # 20321518045
ambiente = os.getenv('AFIP_ENV', 'prod')

print("=" * 70)
print(f"BUSQUEDA EXHAUSTIVA DE FACTURAS")
print(f"CUIT: {cuit}")
print(f"Buscando en PV 1-20 para todos los tipos")
print("=" * 70)

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, ambiente)

tipos_buscar = {
    1: "Factura A",
    6: "Factura B",
    11: "Factura C",
    51: "Factura M",
}

# Buscar en muchos puntos de venta
puntos_venta_buscar = list(range(1, 21))  # PV 1 a 20

print("\n[1] Buscando últimos números autorizados...\n")

facturas_encontradas = []
ultimos_por_tipo = {}

for tipo, desc in tipos_buscar.items():
    print(f"{desc} (Tipo {tipo}):")
    ultimos_pv = []

    for pv in puntos_venta_buscar:
        try:
            ultimo = client.obtener_ultimo_comprobante(cuit, tipo, pv)

            if ultimo and ultimo > 0:
                print(f"  ✓ PV {pv:04d}: Último = {ultimo}")
                ultimos_pv.append({'pv': pv, 'ultimo': ultimo})

                # Consultar inmediatamente las últimas 5 facturas
                for num in range(max(1, ultimo - 4), ultimo + 1):
                    try:
                        comp = client.consultar_comprobante(cuit, tipo, pv, num)

                        if comp and ('CAE' in comp or 'cae' in comp):
                            fecha = comp.get('CbteFch', comp.get('fecha_emision', 'N/A'))
                            importe = comp.get('ImpTotal', comp.get('importe_total', 'N/A'))
                            cae = comp.get('CAE', comp.get('cae', 'N/A'))

                            print(f"    → {pv:04d}-{num:08d}: ${importe} ({fecha})")

                            facturas_encontradas.append({
                                'tipo': tipo,
                                'tipo_desc': desc,
                                'punto_venta': pv,
                                'numero': num,
                                'numero_formato': f"{pv:04d}-{num:08d}",
                                'fecha': fecha,
                                'importe': importe,
                                'cae': cae,
                                'receptor_doc': comp.get('DocNro', 'N/A'),
                                'datos': comp
                            })
                    except Exception as e:
                        continue

        except Exception as e:
            continue

    if ultimos_pv:
        ultimos_por_tipo[tipo] = ultimos_pv
        print(f"  Total PV activos: {len(ultimos_pv)}\n")
    else:
        print(f"  Sin facturas\n")

# Resumen
print("=" * 70)
print("RESULTADOS")
print("=" * 70)

if facturas_encontradas:
    print(f"\n✅ Total facturas encontradas: {len(facturas_encontradas)}")

    # Por tipo
    por_tipo = {}
    for fact in facturas_encontradas:
        t = fact['tipo_desc']
        if t not in por_tipo:
            por_tipo[t] = []
        por_tipo[t].append(fact)

    print("\nDistribución por tipo:")
    for tipo, facts in por_tipo.items():
        print(f"  {tipo}: {len(facts)}")

    # Más recientes
    facturas_ordenadas = sorted(facturas_encontradas,
                                key=lambda x: x['fecha'] if x['fecha'] != 'N/A' else '0',
                                reverse=True)

    print("\n📋 Facturas más recientes (últimas 15):")
    for i, fact in enumerate(facturas_ordenadas[:15], 1):
        print(f"  {i:2d}. {fact['tipo_desc']:15s} {fact['numero_formato']} - ${fact['importe']:>12s} ({fact['fecha']})")

    # Guardar
    import json
    output_file = f'facturas_exhaustivas_{cuit}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(facturas_encontradas, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Guardado en: {output_file}")

else:
    print("\n❌ No se encontraron facturas en ningún punto de venta (1-20)")
    print("\nPosibilidades:")
    print("  1. Las facturas están en puntos de venta mayores a 20")
    print("  2. El CUIT no ha emitido facturas electrónicas")
    print("  3. Las facturas están en otro servicio (WSMTXCA, WSFEX)")
    print("  4. Problema de permisos o certificado")

print("\n" + "=" * 70)
