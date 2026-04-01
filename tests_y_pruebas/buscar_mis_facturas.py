# -*- coding: utf-8 -*-
"""Buscar facturas propias - CUIT 20321518045"""
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
print(f"BUSQUEDA DE FACTURAS PROPIAS")
print(f"CUIT: {cuit}")
print(f"Ambiente: {ambiente.upper()}")
print("=" * 70)

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, ambiente)

# 1. Primero obtener puntos de venta habilitados
print("\n[1] Obteniendo puntos de venta habilitados...")
try:
    puntos_venta_info = client.obtener_puntos_venta(cuit)
    if puntos_venta_info:
        print(f"    Puntos de venta encontrados: {len(puntos_venta_info)}")
        for pv_info in puntos_venta_info:
            print(f"      - PV {pv_info['numero']:04d}: {pv_info.get('descripcion', 'Sin descripción')}")
        puntos_venta = [pv['numero'] for pv in puntos_venta_info]
    else:
        print("    No se obtuvieron puntos de venta, usando lista predeterminada")
        puntos_venta = [1, 2, 3, 4, 5]
except Exception as e:
    print(f"    Error obteniendo PV: {e}")
    puntos_venta = [1, 2, 3, 4, 5]

print(f"    Puntos de venta a consultar: {puntos_venta}")

# 2. Buscar últimos números autorizados por tipo
print("\n[2] Consultando últimos números autorizados...")

tipos_buscar = {
    11: "Factura C",
    6: "Factura B",
    1: "Factura A",
    51: "Factura M",
    3: "Nota de Crédito A",
    8: "Nota de Crédito B",
    13: "Nota de Crédito C"
}

ultimos = {}
for tipo, desc in tipos_buscar.items():
    print(f"\n    {desc} (Tipo {tipo}):")
    for pv in puntos_venta[:10]:  # Limitar a primeros 10 PV
        try:
            ultimo = client.obtener_ultimo_comprobante(cuit, tipo, pv)
            if ultimo and ultimo > 0:
                print(f"      PV {pv:04d}: Último = {ultimo}")
                if tipo not in ultimos:
                    ultimos[tipo] = []
                ultimos[tipo].append({'pv': pv, 'ultimo': ultimo})
        except Exception as e:
            continue

# 3. Consultar facturas encontradas
print("\n[3] Consultando facturas...")
facturas = []

for tipo, pvs_data in ultimos.items():
    tipo_desc = tipos_buscar.get(tipo, f'Tipo {tipo}')
    print(f"\n    {tipo_desc}:")

    for pv_data in pvs_data:
        pv = pv_data['pv']
        ultimo = pv_data['ultimo']

        print(f"      PV {pv:04d} - Consultando últimas 10 facturas...")

        # Consultar últimas 10 facturas
        inicio = max(1, ultimo - 9)
        encontradas_pv = 0

        for num in range(ultimo, inicio - 1, -1):
            try:
                comp = client.consultar_comprobante(cuit, tipo, pv, num)

                if comp and 'CAE' in comp:
                    fecha = comp.get('CbteFch', comp.get('fecha_emision', 'N/A'))
                    importe = comp.get('ImpTotal', comp.get('importe_total', 'N/A'))
                    cae = comp.get('CAE', comp.get('cae', 'N/A'))

                    print(f"        {pv:04d}-{num:08d}: ${importe} ({fecha}) CAE: {cae[:15]}...")

                    facturas.append({
                        'tipo': tipo,
                        'tipo_desc': tipo_desc,
                        'punto_venta': pv,
                        'numero': num,
                        'numero_formato': f"{pv:04d}-{num:08d}",
                        'fecha': fecha,
                        'importe': importe,
                        'cae': cae,
                        'datos_completos': comp
                    })
                    encontradas_pv += 1

            except Exception as e:
                continue

        if encontradas_pv == 0:
            print(f"        No se pudieron recuperar datos")

# 4. Mostrar resumen
print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)

if facturas:
    print(f"\n✅ Total facturas encontradas: {len(facturas)}")

    # Agrupar por tipo
    por_tipo = {}
    for fact in facturas:
        tipo = fact['tipo_desc']
        if tipo not in por_tipo:
            por_tipo[tipo] = []
        por_tipo[tipo].append(fact)

    print("\nFacturas por tipo:")
    for tipo, facts in por_tipo.items():
        print(f"\n  {tipo}: {len(facts)} facturas")
        # Mostrar primeras 5
        for i, fact in enumerate(facts[:5], 1):
            print(f"    {i}. {fact['numero_formato']} - ${fact['importe']} ({fact['fecha']})")
        if len(facts) > 5:
            print(f"    ... y {len(facts) - 5} más")

    # Facturas más recientes
    facturas_ordenadas = sorted(facturas, key=lambda x: x['fecha'], reverse=True)
    print("\n✨ Facturas más recientes:")
    for i, fact in enumerate(facturas_ordenadas[:10], 1):
        print(f"  {i}. {fact['tipo_desc']} {fact['numero_formato']}")
        print(f"     Fecha: {fact['fecha']} - Importe: ${fact['importe']}")
        print(f"     CAE: {fact['cae'][:20]}...")

    # Guardar a JSON
    import json
    output_file = f'mis_facturas_{cuit}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(facturas, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Facturas guardadas en: {output_file}")

else:
    print("\n❌ No se encontraron facturas")
    print("\nVerificaciones:")
    print("  1. ¿Tiene facturas electrónicas emitidas desde 2013?")
    print("  2. ¿El certificado está asociado al CUIT correcto?")
    print("  3. ¿Está en ambiente de producción o homologación?")
    print(f"  4. Ambiente actual: {ambiente.upper()}")

print("\n" + "=" * 70)
