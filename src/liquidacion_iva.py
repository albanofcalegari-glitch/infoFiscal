# -*- coding: utf-8 -*-
"""
Liquidación de IVA — posición mensual y Libro IVA Digital.

Calcula:
  - Débito Fiscal (ventas): IVA de comprobantes emitidos
  - Crédito Fiscal (compras): IVA de comprobantes recibidos
  - Saldo técnico: Débito - Crédito
  - Saldo a favor del período anterior
  - Resultado: a pagar o saldo a favor
"""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PosicionIVA:
    periodo: str  # YYYY-MM
    # Ventas (débito fiscal)
    ventas_gravadas: Decimal = Decimal('0')
    ventas_iva_105: Decimal = Decimal('0')
    ventas_iva_21: Decimal = Decimal('0')
    ventas_iva_27: Decimal = Decimal('0')
    ventas_exentas: Decimal = Decimal('0')
    ventas_no_gravadas: Decimal = Decimal('0')
    total_debito: Decimal = Decimal('0')
    cant_ventas: int = 0
    # Compras (crédito fiscal)
    compras_gravadas: Decimal = Decimal('0')
    compras_iva_105: Decimal = Decimal('0')
    compras_iva_21: Decimal = Decimal('0')
    compras_iva_27: Decimal = Decimal('0')
    compras_exentas: Decimal = Decimal('0')
    compras_no_gravadas: Decimal = Decimal('0')
    total_credito: Decimal = Decimal('0')
    cant_compras: int = 0
    # Saldos
    saldo_tecnico: Decimal = Decimal('0')
    saldo_anterior: Decimal = Decimal('0')
    resultado: Decimal = Decimal('0')  # >0 a pagar, <0 saldo a favor


def calcular_posicion_iva(cursor, estudio_id: int, periodo: str,
                           cuit_emisor: str = None,
                           saldo_anterior: Decimal = Decimal('0')) -> PosicionIVA:
    """
    Calcula la posición de IVA para un período dado.

    Args:
        cursor: cursor de DB abierto
        estudio_id: tenant
        periodo: 'YYYY-MM'
        cuit_emisor: filtrar por CUIT emisor (opcional)
        saldo_anterior: saldo a favor del período anterior
    """
    pos = PosicionIVA(periodo=periodo, saldo_anterior=saldo_anterior)
    year, month = periodo.split('-')

    # Débito fiscal (ventas/emitidos)
    query_ventas = """
        SELECT
            COUNT(*) as cant,
            COALESCE(SUM(importe_neto), 0) as gravado,
            COALESCE(SUM(importe_iva), 0) as iva_total,
            COALESCE(SUM(importe_exento), 0) as exento,
            COALESCE(SUM(importe_no_gravado), 0) as no_gravado,
            COALESCE(SUM(CASE WHEN tipo_comprobante IN (3, 8, 13) THEN -importe_iva ELSE importe_iva END), 0) as debito_neto
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
          AND EXTRACT(MONTH FROM fecha_emision) = %s
    """
    params_v = [estudio_id, int(year), int(month)]
    if cuit_emisor:
        query_ventas += " AND cuit_emisor = %s"
        params_v.append(cuit_emisor.replace('-', ''))

    cursor.execute(query_ventas, params_v)
    row = cursor.fetchone()
    if row:
        pos.cant_ventas = row['cant']
        pos.ventas_gravadas = Decimal(str(row['gravado']))
        pos.ventas_exentas = Decimal(str(row['exento']))
        pos.ventas_no_gravadas = Decimal(str(row['no_gravado']))
        pos.total_debito = Decimal(str(row['debito_neto']))

    # IVA ventas por alícuota
    cursor.execute("""
        SELECT iva_json FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
          AND EXTRACT(MONTH FROM fecha_emision) = %s
    """, [estudio_id, int(year), int(month)])
    # El detalle por alícuota se calcula si hay iva_json

    # Crédito fiscal (compras/recibidos)
    query_compras = """
        SELECT
            COUNT(*) as cant,
            COALESCE(SUM(importe_neto), 0) as gravado,
            COALESCE(SUM(importe_iva), 0) as iva_total,
            COALESCE(SUM(importe_exento), 0) as exento,
            COALESCE(SUM(importe_no_gravado), 0) as no_gravado,
            COALESCE(SUM(iva_105), 0) as iva_105,
            COALESCE(SUM(iva_21), 0) as iva_21,
            COALESCE(SUM(iva_27), 0) as iva_27
        FROM comprobantes_recibidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
          AND EXTRACT(MONTH FROM fecha_emision) = %s
    """
    params_c = [estudio_id, int(year), int(month)]
    cursor.execute(query_compras, params_c)
    row = cursor.fetchone()
    if row:
        pos.cant_compras = row['cant']
        pos.compras_gravadas = Decimal(str(row['gravado']))
        pos.compras_iva_105 = Decimal(str(row['iva_105']))
        pos.compras_iva_21 = Decimal(str(row['iva_21']))
        pos.compras_iva_27 = Decimal(str(row['iva_27']))
        pos.compras_exentas = Decimal(str(row['exento']))
        pos.compras_no_gravadas = Decimal(str(row['no_gravado']))
        pos.total_credito = Decimal(str(row['iva_total']))

    # Saldo técnico y resultado
    pos.saldo_tecnico = pos.total_debito - pos.total_credito
    pos.resultado = pos.saldo_tecnico - abs(saldo_anterior) if saldo_anterior < 0 else pos.saldo_tecnico

    return pos


def generar_libro_iva_digital(cursor, estudio_id: int, periodo: str) -> dict:
    """
    Genera los datos para el Libro IVA Digital (RG 3685).
    Retorna dict con {ventas: [...], compras: [...]} listos para exportar.
    """
    year, month = periodo.split('-')

    # Ventas
    cursor.execute("""
        SELECT tipo_comprobante, punto_venta, numero_desde, fecha_emision,
               nro_doc_receptor, receptor_nombre, tipo_doc_receptor,
               importe_total, importe_neto, importe_iva, importe_exento,
               importe_no_gravado, importe_tributos, cae, moneda, cotizacion
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
          AND EXTRACT(MONTH FROM fecha_emision) = %s
        ORDER BY tipo_comprobante, punto_venta, numero_desde
    """, [estudio_id, int(year), int(month)])
    ventas = cursor.fetchall()

    # Compras
    cursor.execute("""
        SELECT tipo_comprobante, punto_venta, numero, fecha_emision,
               cuit_emisor, emisor_nombre,
               importe_total, importe_neto, importe_iva, importe_exento,
               importe_no_gravado, importe_tributos,
               iva_105, iva_21, iva_27, cae
        FROM comprobantes_recibidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
          AND EXTRACT(MONTH FROM fecha_emision) = %s
        ORDER BY tipo_comprobante, punto_venta, numero
    """, [estudio_id, int(year), int(month)])
    compras = cursor.fetchall()

    return {'ventas': ventas, 'compras': compras, 'periodo': periodo}
