#!/usr/bin/env python3
r"""
Descarga masiva de comprobantes WSFEv1 para un CUIT.

Uso:
    cd "C:\Users\DELL\Desktop\proyectos python\infofiscal"
    python scripts/descargar_comprobantes.py --cuit 20308757626

Opciones:
    --cuit          CUIT del emisor a consultar (obligatorio)
    --desde         Fecha desde YYYYMMDD (opcional, filtra resultados)
    --hasta         Fecha hasta YYYYMMDD (opcional, filtra resultados)
    --puntos-venta  Puntos de venta separados por coma (default: 1,2,3,4,5)
    --tipos         Tipos de comprobante separados por coma (default: 1,6,11,51)
    --output        Carpeta de salida (default: facturas/<cuit>/)
"""

import argparse
import json
import sys
import time
from pathlib import Path
from datetime import datetime

# Agregar raíz del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from wsfev1_client import WSFEv1Client


def descargar(cuit, fecha_desde=None, fecha_hasta=None, puntos_venta=None, tipos=None, output_dir=None):
    cert_path = ROOT / 'certs' / 'certificado.crt'
    key_path = ROOT / 'certs' / 'clave_privada.key'

    client = WSFEv1Client(str(cert_path), str(key_path), 'prod')

    if puntos_venta is None:
        puntos_venta = [1, 2, 3, 4, 5]
    if tipos is None:
        tipos = [1, 6, 11, 51]

    if output_dir is None:
        output_dir = ROOT / 'facturas' / cuit
    else:
        output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"{'='*60}")
    print(f"DESCARGA MASIVA WSFEv1")
    print(f"CUIT: {cuit}")
    print(f"Tipos: {tipos}")
    print(f"Puntos de venta: {puntos_venta}")
    if fecha_desde:
        print(f"Desde: {fecha_desde}")
    if fecha_hasta:
        print(f"Hasta: {fecha_hasta}")
    print(f"Output: {output_dir}")
    print(f"{'='*60}")

    todos = []
    inicio = time.time()

    for tipo in tipos:
        tipo_desc = client.tipos_comprobante.get(tipo, f'Tipo {tipo}')
        for pv in puntos_venta:
            ultimo = client.obtener_ultimo_comprobante(cuit, tipo, pv)
            if not ultimo or ultimo <= 0:
                continue

            print(f"\n[{tipo_desc}] PV {pv}: {ultimo} comprobantes")
            descargados = 0
            saltados = 0

            for num in range(ultimo, 0, -1):
                try:
                    comp = client.consultar_comprobante(cuit, tipo, pv, num)
                    if comp is None:
                        continue

                    fecha_cbte = comp.get('CbteFch') or ''

                    # Early stop
                    if fecha_desde and fecha_cbte < fecha_desde:
                        print(f"  -> Early stop en #{num} (fecha {fecha_cbte} < {fecha_desde})")
                        break

                    # Filtrar posterior
                    if fecha_hasta and fecha_cbte > fecha_hasta:
                        saltados += 1
                        continue

                    comp['CUIT'] = cuit
                    comp['PtoVta'] = str(pv)
                    comp['CbteTipo'] = str(tipo)
                    comp['CbteTipoDesc'] = tipo_desc
                    comp['CbteNro'] = str(num)
                    todos.append(comp)
                    descargados += 1

                    if descargados % 50 == 0:
                        print(f"  ... {descargados} descargados (actual: #{num}, fecha: {fecha_cbte})")

                except Exception as e:
                    print(f"  Error en #{num}: {e}")
                    continue

            print(f"  Total: {descargados} descargados, {saltados} saltados")

    elapsed = time.time() - inicio

    # Guardar JSON
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"comprobantes_{cuit}_{ts}.json"
    filepath = output_dir / filename

    resultado = {
        'cuit': cuit,
        'solicitante': '20321518045',
        'fecha_descarga': datetime.now().isoformat(),
        'total': len(todos),
        'filtro_desde': fecha_desde,
        'filtro_hasta': fecha_hasta,
        'comprobantes': todos
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"RESULTADO: {len(todos)} comprobantes en {elapsed:.1f}s")
    print(f"Guardado en: {filepath}")
    print(f"{'='*60}")

    return filepath


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Descarga masiva de comprobantes WSFEv1')
    parser.add_argument('--cuit', required=True, help='CUIT del emisor')
    parser.add_argument('--desde', default=None, help='Fecha desde YYYYMMDD')
    parser.add_argument('--hasta', default=None, help='Fecha hasta YYYYMMDD')
    parser.add_argument('--puntos-venta', default='1,2,3,4,5', help='PV separados por coma')
    parser.add_argument('--tipos', default='1,6,11,51', help='Tipos separados por coma')
    parser.add_argument('--output', default=None, help='Carpeta de salida')

    args = parser.parse_args()

    pvs = [int(x) for x in args.puntos_venta.split(',')]
    tipos = [int(x) for x in args.tipos.split(',')]

    descargar(
        cuit=args.cuit,
        fecha_desde=args.desde,
        fecha_hasta=args.hasta,
        puntos_venta=pvs,
        tipos=tipos,
        output_dir=args.output
    )
