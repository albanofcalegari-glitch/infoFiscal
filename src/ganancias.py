# -*- coding: utf-8 -*-
"""
Proyección de Impuesto a las Ganancias — estimación anual PH/PJ.

Calcula ingresos, gastos deducibles, deducciones personales y estima
el impuesto anual según las escalas vigentes de ARCA.
"""

from __future__ import annotations
from decimal import Decimal
from dataclasses import dataclass, field

# Escalas Ganancias PH 2025 (simplificadas, montos en pesos)
ESCALAS_PH = [
    (Decimal('0'),          Decimal('1_200_000'),   Decimal('5'),   Decimal('0')),
    (Decimal('1_200_000'),  Decimal('2_400_000'),   Decimal('9'),   Decimal('60_000')),
    (Decimal('2_400_000'),  Decimal('3_600_000'),   Decimal('12'),  Decimal('168_000')),
    (Decimal('3_600_000'),  Decimal('5_400_000'),   Decimal('15'),  Decimal('312_000')),
    (Decimal('5_400_000'),  Decimal('8_100_000'),   Decimal('19'),  Decimal('582_000')),
    (Decimal('8_100_000'),  Decimal('10_800_000'),  Decimal('23'),  Decimal('1_095_000')),
    (Decimal('10_800_000'), Decimal('16_200_000'),  Decimal('27'),  Decimal('1_716_000')),
    (Decimal('16_200_000'), Decimal('24_300_000'),  Decimal('31'),  Decimal('3_174_000')),
    (Decimal('24_300_000'), Decimal('999_999_999'), Decimal('35'),  Decimal('5_685_000')),
]

ALICUOTA_PJ = Decimal('35')

DEDUCCIONES_PERSONALES = {
    'ganancia_no_imponible': Decimal('3_091_035'),
    'deduccion_especial_4ta': Decimal('14_836_968'),
    'conyuge': Decimal('2_911_135'),
    'hijo': Decimal('1_468_096'),
}


@dataclass
class ProyeccionGanancias:
    anio: int
    tipo_persona: str
    ingresos_brutos: Decimal = Decimal('0')
    gastos_deducibles: Decimal = Decimal('0')
    ingresos_mensuales: list = field(default_factory=list)
    deducciones: dict = field(default_factory=dict)
    ganancia_neta: Decimal = Decimal('0')
    ganancia_neta_sujeta: Decimal = Decimal('0')
    impuesto_determinado: Decimal = Decimal('0')
    alicuota_efectiva: Decimal = Decimal('0')
    retenciones_sufridas: Decimal = Decimal('0')
    saldo_a_pagar: Decimal = Decimal('0')


def _calcular_impuesto_ph(ganancia_sujeta: Decimal) -> Decimal:
    if ganancia_sujeta <= 0:
        return Decimal('0')

    for min_rango, max_rango, alicuota, fijo in ESCALAS_PH:
        if ganancia_sujeta <= max_rango:
            excedente = ganancia_sujeta - min_rango
            return fijo + (excedente * alicuota / 100)

    return Decimal('0')


def proyectar_ganancias(cursor, estudio_id: int, anio: int,
                         tipo_persona: str = 'PH') -> ProyeccionGanancias:
    proy = ProyeccionGanancias(anio=anio, tipo_persona=tipo_persona)

    cursor.execute("""
        SELECT TO_CHAR(fecha_emision, 'YYYY-MM') as periodo,
               COALESCE(SUM(importe_neto), 0) as neto
        FROM comprobantes_emitidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
        GROUP BY TO_CHAR(fecha_emision, 'YYYY-MM')
        ORDER BY periodo
    """, (estudio_id, anio))

    meses_data = cursor.fetchall()
    total_ingresos = Decimal('0')
    for m in meses_data:
        val = Decimal(str(m['neto']))
        proy.ingresos_mensuales.append({
            'periodo': m['periodo'],
            'monto': float(val),
        })
        total_ingresos += val

    meses_con_datos = len(meses_data)
    if meses_con_datos > 0 and meses_con_datos < 12:
        promedio = total_ingresos / meses_con_datos
        total_ingresos = promedio * 12

    proy.ingresos_brutos = total_ingresos

    cursor.execute("""
        SELECT COALESCE(SUM(importe_neto), 0) as gastos
        FROM comprobantes_recibidos
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha_emision) = %s
    """, (estudio_id, anio))
    gastos = Decimal(str(cursor.fetchone()['gastos']))

    if meses_con_datos > 0 and meses_con_datos < 12:
        gastos = (gastos / meses_con_datos) * 12

    proy.gastos_deducibles = gastos

    ganancia_neta = total_ingresos - gastos
    proy.ganancia_neta = ganancia_neta

    if tipo_persona == 'PH':
        gni = DEDUCCIONES_PERSONALES['ganancia_no_imponible']
        ded_esp = DEDUCCIONES_PERSONALES['deduccion_especial_4ta']

        proy.deducciones = {
            'ganancia_no_imponible': float(gni),
            'deduccion_especial': float(ded_esp),
            'total': float(gni + ded_esp),
        }

        ganancia_sujeta = ganancia_neta - gni - ded_esp
        proy.ganancia_neta_sujeta = max(ganancia_sujeta, Decimal('0'))
        proy.impuesto_determinado = _calcular_impuesto_ph(proy.ganancia_neta_sujeta)
    else:
        proy.ganancia_neta_sujeta = max(ganancia_neta, Decimal('0'))
        proy.impuesto_determinado = proy.ganancia_neta_sujeta * ALICUOTA_PJ / 100

    if proy.ingresos_brutos > 0:
        proy.alicuota_efectiva = (proy.impuesto_determinado / proy.ingresos_brutos) * 100

    cursor.execute("""
        SELECT COALESCE(SUM(importe_retenido), 0) as ret
        FROM retenciones
        WHERE estudio_id = %s
          AND EXTRACT(YEAR FROM fecha) = %s
          AND impuesto = 'ganancias'
    """, (estudio_id, anio))
    proy.retenciones_sufridas = Decimal(str(cursor.fetchone()['ret']))

    proy.saldo_a_pagar = max(proy.impuesto_determinado - proy.retenciones_sufridas, Decimal('0'))

    return proy
