# -*- coding: utf-8 -*-
"""
Analytics — métricas y datos para gráficos del dashboard.
"""

from __future__ import annotations
from datetime import date, timedelta


def kpis_estudio(cursor, estudio_id: int) -> dict:
    """KPIs principales del estudio."""
    hoy = date.today()
    mes_actual = hoy.strftime('%Y-%m')
    mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    # Clientes totales
    cursor.execute("SELECT COUNT(*) as c FROM clientes WHERE estudio_id = %s", (estudio_id,))
    total_clientes = cursor.fetchone()['c']

    # Facturación mes actual
    cursor.execute("""
        SELECT COUNT(*) as cant, COALESCE(SUM(importe_total), 0) as total
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND TO_CHAR(fecha_emision, 'YYYY-MM') = %s
    """, (estudio_id, mes_actual))
    row = cursor.fetchone()
    fact_mes = {'cantidad': row['cant'], 'total': float(row['total'])}

    # Facturación mes anterior
    cursor.execute("""
        SELECT COUNT(*) as cant, COALESCE(SUM(importe_total), 0) as total
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND TO_CHAR(fecha_emision, 'YYYY-MM') = %s
    """, (estudio_id, mes_anterior))
    row = cursor.fetchone()
    fact_mes_ant = {'cantidad': row['cant'], 'total': float(row['total'])}

    # Variación
    if fact_mes_ant['total'] > 0:
        variacion = ((fact_mes['total'] - fact_mes_ant['total']) / fact_mes_ant['total']) * 100
    else:
        variacion = 0

    # Retenciones del mes
    cursor.execute("""
        SELECT COALESCE(SUM(importe_retenido), 0) as total
        FROM retenciones
        WHERE estudio_id = %s AND TO_CHAR(fecha, 'YYYY-MM') = %s
    """, (estudio_id, mes_actual))
    ret_mes = float(cursor.fetchone()['total'])

    # Saldos CC
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tipo = 'cliente' AND saldo > 0 THEN saldo ELSE 0 END), 0) as por_cobrar,
            COALESCE(SUM(CASE WHEN tipo = 'proveedor' AND saldo > 0 THEN saldo ELSE 0 END), 0) as por_pagar
        FROM cuentas_corrientes
        WHERE estudio_id = %s
    """, (estudio_id,))
    row = cursor.fetchone()

    return {
        'total_clientes': total_clientes,
        'facturacion_mes': fact_mes,
        'facturacion_mes_anterior': fact_mes_ant,
        'variacion_pct': round(variacion, 1),
        'retenciones_mes': ret_mes,
        'por_cobrar': float(row['por_cobrar']),
        'por_pagar': float(row['por_pagar']),
    }


def facturacion_mensual(cursor, estudio_id: int, meses: int = 12) -> list[dict]:
    """Facturación mensual de los últimos N meses."""
    cursor.execute("""
        SELECT TO_CHAR(fecha_emision, 'YYYY-MM') as periodo,
               COUNT(*) as cantidad,
               COALESCE(SUM(importe_total), 0) as total,
               COALESCE(SUM(importe_neto), 0) as neto,
               COALESCE(SUM(importe_iva), 0) as iva
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND fecha_emision >= (CURRENT_DATE - INTERVAL '%s months')
        GROUP BY TO_CHAR(fecha_emision, 'YYYY-MM')
        ORDER BY periodo
    """, (estudio_id, meses))
    return cursor.fetchall()


def facturacion_por_tipo(cursor, estudio_id: int, periodo: str = None) -> list[dict]:
    """Facturación agrupada por tipo de comprobante."""
    query = """
        SELECT tipo_comprobante, COUNT(*) as cantidad,
               COALESCE(SUM(importe_total), 0) as total
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
    """
    params = [estudio_id]
    if periodo:
        query += " AND TO_CHAR(fecha_emision, 'YYYY-MM') = %s"
        params.append(periodo)
    query += " GROUP BY tipo_comprobante ORDER BY total DESC"

    cursor.execute(query, params)
    return cursor.fetchall()


def top_clientes(cursor, estudio_id: int, limite: int = 10) -> list[dict]:
    """Top clientes por facturación."""
    cursor.execute("""
        SELECT ce.receptor_nombre, ce.cuit_receptor,
               COUNT(*) as cantidad,
               COALESCE(SUM(ce.importe_total), 0) as total
        FROM comprobantes_emitidos ce
        WHERE ce.estudio_id = %s
          AND ce.fecha_emision >= (CURRENT_DATE - INTERVAL '12 months')
        GROUP BY ce.receptor_nombre, ce.cuit_receptor
        ORDER BY total DESC
        LIMIT %s
    """, (estudio_id, limite))
    return cursor.fetchall()


def iva_mensual(cursor, estudio_id: int, meses: int = 6) -> list[dict]:
    """Posición de IVA mensual (débito vs crédito)."""
    cursor.execute("""
        SELECT TO_CHAR(fecha_emision, 'YYYY-MM') as periodo,
               COALESCE(SUM(importe_iva), 0) as debito
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND fecha_emision >= (CURRENT_DATE - INTERVAL '%s months')
        GROUP BY TO_CHAR(fecha_emision, 'YYYY-MM')
        ORDER BY periodo
    """, (estudio_id, meses))
    debitos = {r['periodo']: float(r['debito']) for r in cursor.fetchall()}

    cursor.execute("""
        SELECT TO_CHAR(fecha_emision, 'YYYY-MM') as periodo,
               COALESCE(SUM(importe_iva), 0) as credito
        FROM comprobantes_recibidos
        WHERE estudio_id = %s
          AND fecha_emision >= (CURRENT_DATE - INTERVAL '%s months')
        GROUP BY TO_CHAR(fecha_emision, 'YYYY-MM')
        ORDER BY periodo
    """, (estudio_id, meses))
    creditos = {r['periodo']: float(r['credito']) for r in cursor.fetchall()}

    periodos = sorted(set(list(debitos.keys()) + list(creditos.keys())))
    return [
        {
            'periodo': p,
            'debito': debitos.get(p, 0),
            'credito': creditos.get(p, 0),
            'saldo': debitos.get(p, 0) - creditos.get(p, 0),
        }
        for p in periodos
    ]
