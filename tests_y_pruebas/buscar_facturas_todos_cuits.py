# -*- coding: utf-8 -*-
"""Buscar facturas para todos los CUITs de la base de datos"""
import sys
import io
import os
import sqlite3
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

print("=" * 70)
print("BUSQUEDA DE FACTURAS - TODOS LOS CLIENTES")
print("=" * 70)

# Obtener CUITs de la base de datos
conn = sqlite3.connect('infofiscal.db')
cursor = conn.cursor()
cursor.execute('SELECT id, CUIT, apellido, nombres, condicionIVA FROM clientes')
clientes = cursor.fetchall()
conn.close()

print(f"\nClientes en la base de datos: {len(clientes)}")
for cliente in clientes:
    cuit_raw = cliente[1]
    # Limpiar CUIT
    cuit = cuit_raw.replace('-', '').replace(' ', '')
    print(f"  {cliente[0]}. {cliente[2]}, {cliente[3]} - CUIT: {cuit} ({cliente[4]})")

print("\n" + "=" * 70)

from wsfev1_client import WSFEv1Client

client = WSFEv1Client(cert_path, key_path, ambiente)

todas_facturas = []

for cliente in clientes:
    cuit_raw = cliente[1]
    cuit = cuit_raw.replace('-', '').replace(' ', '')
    nombre = f"{cliente[2]}, {cliente[3]}"

    print(f"\n[{cliente[0]}] Buscando facturas para {nombre} - CUIT {cuit}")
    print("-" * 70)

    facturas_cliente = []

    # Tipos de comprobante a buscar
    tipos = [11, 6, 51, 1]  # C, B, M, A

    for tipo in tipos:
        tipo_desc = client.tipos_comprobante.get(tipo, f'Tipo {tipo}')

        # Probar puntos de venta 1-5
        for pv in range(1, 6):
            try:
                ultimo = client.obtener_ultimo_comprobante(cuit, tipo, pv)

                if ultimo and ultimo > 0:
                    print(f"  {tipo_desc} PV{pv:04d}: Ultimo = {ultimo}")

                    # Consultar últimas 3 facturas
                    for num in range(max(1, ultimo - 2), ultimo + 1):
                        try:
                            comp = client.consultar_comprobante(cuit, tipo, pv, num)
                            if comp:
                                facturas_cliente.append({
                                    'cliente_id': cliente[0],
                                    'cliente_nombre': nombre,
                                    'cuit': cuit,
                                    'tipo': tipo,
                                    'tipo_desc': tipo_desc,
                                    'punto_venta': pv,
                                    'numero': num,
                                    'numero_formato': f"{pv:04d}-{num:08d}",
                                    'cae': comp.get('CAE', comp.get('cae', 'N/A')),
                                    'fecha': comp.get('CbteFch', comp.get('fecha_emision', 'N/A')),
                                    'importe': comp.get('ImpTotal', comp.get('importe_total', 'N/A')),
                                    'moneda': comp.get('MonId', 'PES'),
                                })
                                print(f"    - {pv:04d}-{num:08d}: ${comp.get('ImpTotal', 'N/A')} ({comp.get('CbteFch', 'N/A')})")
                        except:
                            continue

            except Exception as e:
                continue

    if facturas_cliente:
        print(f"\n  Total facturas encontradas: {len(facturas_cliente)}")
        todas_facturas.extend(facturas_cliente)
    else:
        print(f"\n  No se encontraron facturas")

# Resumen final
print("\n" + "=" * 70)
print("RESUMEN GENERAL")
print("=" * 70)

if todas_facturas:
    print(f"\nTotal facturas encontradas: {len(todas_facturas)}")

    # Agrupar por cliente
    por_cliente = {}
    for fact in todas_facturas:
        cid = fact['cliente_id']
        if cid not in por_cliente:
            por_cliente[cid] = {
                'nombre': fact['cliente_nombre'],
                'cuit': fact['cuit'],
                'facturas': []
            }
        por_cliente[cid]['facturas'].append(fact)

    print("\nFacturas por cliente:")
    for cid, data in por_cliente.items():
        print(f"\n  [{cid}] {data['nombre']} (CUIT: {data['cuit']})")
        print(f"       Facturas: {len(data['facturas'])}")

        # Mostrar primeras 5
        for i, fact in enumerate(data['facturas'][:5], 1):
            print(f"       {i}. {fact['tipo_desc']} {fact['numero_formato']} - ${fact['importe']} ({fact['fecha']})")

        if len(data['facturas']) > 5:
            print(f"       ... y {len(data['facturas']) - 5} más")

    # Guardar a JSON
    import json
    output_file = 'facturas_todos_clientes.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(todas_facturas, f, ensure_ascii=False, indent=2)
    print(f"\nFacturas guardadas en: {output_file}")

else:
    print("\nNo se encontraron facturas para ningún cliente")
    print("\nPosibles razones:")
    print("  - Los CUITs no tienen facturas emitidas en AFIP")
    print("  - Se requiere autorización adicional para consultar")
    print("  - Los CUITs están en ambiente de homologación")

print("\n" + "=" * 70)
