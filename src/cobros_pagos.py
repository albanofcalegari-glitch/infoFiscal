# -*- coding: utf-8 -*-
"""
Cobros y Pagos — cuentas corrientes y aging de deuda.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import date, timedelta


def obtener_cuentas(cursor, estudio_id: int, tipo: str = None) -> list[dict]:
    """Lista cuentas corrientes del estudio, opcionalmente filtradas por tipo."""
    query = """
        SELECT cc.*, c.apellido, c.nombres
        FROM cuentas_corrientes cc
        LEFT JOIN clientes c ON c.id = cc.cliente_id
        WHERE cc.estudio_id = %s
    """
    params = [estudio_id]
    if tipo:
        query += " AND cc.tipo = %s"
        params.append(tipo)
    query += " ORDER BY cc.nombre"

    cursor.execute(query, params)
    return cursor.fetchall()


def obtener_movimientos(cursor, cuenta_id: int, limite: int = 50) -> list[dict]:
    """Lista movimientos de una cuenta corriente."""
    cursor.execute("""
        SELECT * FROM movimientos_cc
        WHERE cuenta_id = %s
        ORDER BY fecha DESC, id DESC
        LIMIT %s
    """, (cuenta_id, limite))
    return cursor.fetchall()


def registrar_movimiento(
    cursor, cuenta_id: int, estudio_id: int,
    fecha: date, tipo_mov: str,
    debe: Decimal = Decimal('0'), haber: Decimal = Decimal('0'),
    descripcion: str = '', comprobante_ref: str = None,
) -> None:
    """Registra un movimiento y actualiza el saldo de la cuenta."""
    # Calcular nuevo saldo
    cursor.execute("SELECT saldo FROM cuentas_corrientes WHERE id = %s AND estudio_id = %s",
                   (cuenta_id, estudio_id))
    row = cursor.fetchone()
    if not row:
        raise ValueError('Cuenta no encontrada')

    nuevo_saldo = Decimal(str(row['saldo'])) + debe - haber

    cursor.execute("""
        INSERT INTO movimientos_cc (cuenta_id, estudio_id, fecha, tipo_mov, descripcion,
                                     comprobante_ref, debe, haber, saldo_parcial)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (cuenta_id, estudio_id, fecha, tipo_mov, descripcion,
          comprobante_ref, debe, haber, nuevo_saldo))

    cursor.execute("""
        UPDATE cuentas_corrientes SET saldo = %s, updated_at = NOW()
        WHERE id = %s
    """, (nuevo_saldo, cuenta_id))


def aging_report(cursor, estudio_id: int, tipo: str = 'cliente') -> list[dict]:
    """
    Genera reporte de aging de deuda.
    Agrupa saldos por antigüedad: corriente, 30d, 60d, 90d, +90d.
    """
    hoy = date.today()

    cursor.execute("""
        SELECT cc.id, cc.nombre, cc.cuit, cc.saldo,
               MAX(m.fecha) as ultimo_mov
        FROM cuentas_corrientes cc
        LEFT JOIN movimientos_cc m ON m.cuenta_id = cc.id
        WHERE cc.estudio_id = %s AND cc.tipo = %s AND cc.saldo != 0
        GROUP BY cc.id
        ORDER BY cc.saldo DESC
    """, (estudio_id, tipo))
    cuentas = cursor.fetchall()

    result = []
    for cc in cuentas:
        ultimo = cc['ultimo_mov']
        if ultimo:
            dias = (hoy - ultimo).days
        else:
            dias = 0

        if dias <= 30:
            bucket = 'corriente'
        elif dias <= 60:
            bucket = '30_dias'
        elif dias <= 90:
            bucket = '60_dias'
        else:
            bucket = '90_mas'

        result.append({
            'id': cc['id'],
            'nombre': cc['nombre'],
            'cuit': cc['cuit'],
            'saldo': float(cc['saldo']),
            'ultimo_mov': str(ultimo) if ultimo else None,
            'dias': dias,
            'bucket': bucket,
        })

    return result
