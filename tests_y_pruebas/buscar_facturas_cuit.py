# -*- coding: utf-8 -*-
"""Buscar facturas para un CUIT específico"""
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

CUIT_BUSCAR = '27312238018'

print("=" * 70)
print(f"BUSQUEDA DE FACTURAS - CUIT {CUIT_BUSCAR}")
print("=" * 70)

# 1. Buscar en WSFEv1 (facturas tradicionales)
print("\n[1] Buscando en WSFEv1 (Facturas Electrónicas Tradicionales)...")
print(f"    Ambiente: {ambiente.upper()}")

try:
    from wsfev1_client import WSFEv1Client

    client_wsfe = WSFEv1Client(cert_path, key_path, ambiente)

    # Buscar en tipos comunes de comprobante
    tipos_buscar = [11, 6, 1, 51]  # C, B, A, M
    puntos_venta = [1, 2, 3, 4, 5]

    facturas_wsfe = []

    for tipo in tipos_buscar:
        tipo_desc = client_wsfe.tipos_comprobante.get(tipo, f'Tipo {tipo}')
        print(f"\n    Tipo {tipo} - {tipo_desc}:")

        for pv in puntos_venta:
            try:
                # Obtener último número
                ultimo = client_wsfe.obtener_ultimo_comprobante(CUIT_BUSCAR, tipo, pv)

                if ultimo and ultimo > 0:
                    print(f"      PV {pv:04d}: Ultimo = {ultimo}")

                    # Consultar últimas 5 facturas
                    for num in range(max(1, ultimo - 4), ultimo + 1):
                        try:
                            comp = client_wsfe.consultar_comprobante(CUIT_BUSCAR, tipo, pv, num)
                            if comp:
                                facturas_wsfe.append({
                                    'servicio': 'WSFEv1',
                                    'tipo': tipo,
                                    'tipo_desc': tipo_desc,
                                    'punto_venta': pv,
                                    'numero': num,
                                    'numero_formato': f"{pv:04d}-{num:08d}",
                                    'cae': comp.get('CAE', comp.get('cae', 'N/A')),
                                    'fecha': comp.get('CbteFch', comp.get('fecha_emision', 'N/A')),
                                    'importe': comp.get('ImpTotal', comp.get('importe_total', 'N/A')),
                                    'datos': comp
                                })
                                print(f"        - {pv:04d}-{num:08d}: ${comp.get('ImpTotal', 'N/A')} - CAE {comp.get('CAE', 'N/A')[:10]}...")
                        except Exception as e:
                            continue

            except Exception as e:
                continue

    print(f"\n    Total facturas WSFEv1: {len(facturas_wsfe)}")

except Exception as e:
    print(f"\n    ERROR WSFEv1: {str(e)}")
    facturas_wsfe = []

# 2. Buscar en WSMTXCA (monotributo)
print("\n[2] Buscando en WSMTXCA (Monotributo)...")

try:
    from src.wsmtxca_client import WSMTXCAClient

    client_mtx = WSMTXCAClient(cert_path, key_path, ambiente)

    # Buscar comprobantes
    facturas_mtx = []

    # Obtener token
    token, sign = client_mtx.autenticar_wsaa(CUIT_BUSCAR)
    print(f"    Token WSMTXCA obtenido")

    # Consultar comprobantes autorizados
    # WSMTXCA usa punto de venta y número de comprobante
    puntos_venta = [1, 2, 3]

    for pv in puntos_venta:
        print(f"    Consultando PV {pv}...")
        try:
            # Intentar consultar últimos números
            for num in range(1, 100):  # Buscar primeros 100
                try:
                    resultado = client_mtx.consultar_comprobante(
                        CUIT_BUSCAR,
                        11,  # Tipo C
                        pv,
                        num
                    )

                    if resultado:
                        facturas_mtx.append({
                            'servicio': 'WSMTXCA',
                            'tipo': 11,
                            'tipo_desc': 'Factura C (MTX)',
                            'punto_venta': pv,
                            'numero': num,
                            'numero_formato': f"{pv:04d}-{num:08d}",
                            'datos': resultado
                        })
                        print(f"      - {pv:04d}-{num:08d}: Encontrada")
                except:
                    break  # Si falla, asumir que no hay más

        except Exception as e:
            continue

    print(f"    Total facturas WSMTXCA: {len(facturas_mtx)}")

except Exception as e:
    print(f"\n    ERROR WSMTXCA: {str(e)}")
    facturas_mtx = []

# 3. Consolidar resultados
print("\n" + "=" * 70)
print("RESULTADOS")
print("=" * 70)

total_facturas = facturas_wsfe + facturas_mtx

if total_facturas:
    print(f"\nTotal facturas encontradas: {len(total_facturas)}")
    print(f"  - WSFEv1: {len(facturas_wsfe)}")
    print(f"  - WSMTXCA: {len(facturas_mtx)}")

    print("\nDetalle:")
    for i, fact in enumerate(total_facturas[:20], 1):  # Mostrar primeras 20
        print(f"  {i}. [{fact['servicio']}] {fact['tipo_desc']} {fact['numero_formato']}")
        if 'fecha' in fact:
            print(f"     Fecha: {fact['fecha']} - Importe: ${fact.get('importe', 'N/A')}")
        if 'cae' in fact:
            print(f"     CAE: {fact['cae']}")

    if len(total_facturas) > 20:
        print(f"\n  ... y {len(total_facturas) - 20} facturas más")

    # Guardar a JSON
    import json
    output_file = f'facturas_{CUIT_BUSCAR}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(total_facturas, f, ensure_ascii=False, indent=2)
    print(f"\nFacturas guardadas en: {output_file}")

else:
    print("\nNo se encontraron facturas para este CUIT")

print("\n" + "=" * 70)
