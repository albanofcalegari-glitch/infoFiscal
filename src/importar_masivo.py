# -*- coding: utf-8 -*-
"""
Importación masiva de comprobantes desde CSV/Excel.

Soporta archivos CSV y XLSX. Mapea columnas automáticamente por nombre
y valida datos antes de insertar en comprobantes_emitidos o comprobantes_recibidos.
"""

from __future__ import annotations
import csv
import io
from datetime import datetime
from decimal import Decimal, InvalidOperation

from src.db import get_cursor

COLUMNAS_ESPERADAS = {
    'tipo_comprobante': ['tipo_comprobante', 'tipo', 'cbte_tipo', 'tipo_cbte'],
    'punto_venta': ['punto_venta', 'pto_vta', 'punto_de_venta', 'sucursal'],
    'nro_comprobante': ['nro_comprobante', 'numero', 'nro', 'cbte_nro', 'comprobante'],
    'fecha_emision': ['fecha_emision', 'fecha', 'date', 'fecha_cbte'],
    'cuit_receptor': ['cuit_receptor', 'cuit', 'cuit_emisor', 'cuit_cliente'],
    'receptor_nombre': ['receptor_nombre', 'razon_social', 'nombre', 'denominacion'],
    'importe_neto': ['importe_neto', 'neto', 'gravado', 'base_imp'],
    'importe_iva': ['importe_iva', 'iva', 'iva_21'],
    'importe_total': ['importe_total', 'total', 'imp_total'],
    'cae': ['cae', 'cae_nro'],
}


def _normalizar_columna(nombre: str) -> str:
    return nombre.strip().lower().replace(' ', '_').replace('-', '_')


def _mapear_columnas(headers: list[str]) -> dict[str, int]:
    mapa = {}
    headers_norm = [_normalizar_columna(h) for h in headers]

    for campo, aliases in COLUMNAS_ESPERADAS.items():
        for i, h in enumerate(headers_norm):
            if h in aliases:
                mapa[campo] = i
                break

    return mapa


def _parsear_fecha(valor: str) -> str | None:
    for fmt in ('%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d'):
        try:
            return datetime.strptime(valor.strip(), fmt).strftime('%Y-%m-%d')
        except (ValueError, AttributeError):
            continue
    return None


def _parsear_decimal(valor) -> Decimal:
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))
    try:
        clean = str(valor).strip().replace('$', '').replace('.', '').replace(',', '.')
        return Decimal(clean)
    except (InvalidOperation, ValueError):
        return Decimal('0')


def _leer_csv(archivo) -> list[list[str]]:
    text = archivo.read().decode('utf-8-sig')
    reader = csv.reader(io.StringIO(text), delimiter=';')
    filas = list(reader)
    if not filas:
        reader = csv.reader(io.StringIO(text), delimiter=',')
        filas = list(reader)
    return filas


def _leer_xlsx(archivo) -> list[list]:
    try:
        import openpyxl
        wb = openpyxl.load_workbook(archivo, read_only=True, data_only=True)
        ws = wb.active
        return [[cell.value for cell in row] for row in ws.iter_rows()]
    except ImportError:
        raise ImportError("Para importar archivos Excel, instale openpyxl: pip install openpyxl")


def procesar_archivo(archivo, extension: str, estudio_id: int,
                     tipo_import: str = 'emitidos') -> dict:
    if extension == 'csv':
        filas = _leer_csv(archivo)
    elif extension in ('xlsx', 'xls'):
        filas = _leer_xlsx(archivo)
    else:
        raise ValueError(f"Formato no soportado: {extension}")

    if len(filas) < 2:
        raise ValueError("El archivo no contiene datos (necesita encabezado + filas)")

    headers = [str(c or '') for c in filas[0]]
    mapa = _mapear_columnas(headers)

    if 'importe_total' not in mapa:
        raise ValueError("No se encontró la columna de importe total. "
                        "Asegurese de que el archivo tenga una columna 'importe_total' o 'total'.")

    tabla = 'comprobantes_emitidos' if tipo_import == 'emitidos' else 'comprobantes_recibidos'
    insertados = 0
    errores = 0
    detalle_errores = []

    with get_cursor() as cur:
        for idx, fila in enumerate(filas[1:], start=2):
            try:
                vals = [str(c or '') for c in fila]

                tipo_cbte = int(vals[mapa['tipo_comprobante']]) if 'tipo_comprobante' in mapa else 1
                pto_vta = int(vals[mapa['punto_venta']]) if 'punto_venta' in mapa else 1
                nro = int(vals[mapa['nro_comprobante']]) if 'nro_comprobante' in mapa else 0

                fecha = _parsear_fecha(vals[mapa['fecha_emision']]) if 'fecha_emision' in mapa else None
                if not fecha:
                    raise ValueError("Fecha de emisión inválida o faltante")

                cuit_rec = vals[mapa['cuit_receptor']].strip() if 'cuit_receptor' in mapa else ''
                nombre_rec = vals[mapa['receptor_nombre']].strip() if 'receptor_nombre' in mapa else ''

                neto = _parsear_decimal(vals[mapa['importe_neto']]) if 'importe_neto' in mapa else Decimal('0')
                iva = _parsear_decimal(vals[mapa['importe_iva']]) if 'importe_iva' in mapa else Decimal('0')
                total = _parsear_decimal(vals[mapa['importe_total']])
                cae = vals[mapa['cae']].strip() if 'cae' in mapa else ''

                cur.execute(f"""
                    INSERT INTO {tabla}
                        (estudio_id, tipo_comprobante, punto_venta, nro_comprobante,
                         fecha_emision, cuit_receptor, receptor_nombre,
                         importe_neto, importe_iva, importe_total, cae)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """, (estudio_id, tipo_cbte, pto_vta, nro, fecha,
                      cuit_rec, nombre_rec, neto, iva, total, cae))

                insertados += 1
            except Exception as e:
                errores += 1
                detalle_errores.append({'fila': idx, 'error': str(e)})

    return {
        'insertados': insertados,
        'errores': errores,
        'total_filas': len(filas) - 1,
        'detalle_errores': detalle_errores,
    }
