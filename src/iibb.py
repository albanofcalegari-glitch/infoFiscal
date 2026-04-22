# -*- coding: utf-8 -*-
"""
Ingresos Brutos — CM03 (mensual) y CM05 (anual) para SIFERE.

Jurisdicciones del Convenio Multilateral (código SIFERE):
  900 = CABA, 901 = Buenos Aires, 902 = Catamarca, 903 = Córdoba, etc.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import date
import json
import xml.etree.ElementTree as ET


JURISDICCIONES = {
    '900': 'CABA', '901': 'Buenos Aires', '902': 'Catamarca',
    '903': 'Córdoba', '904': 'Corrientes', '905': 'Chaco',
    '906': 'Chubut', '907': 'Entre Ríos', '908': 'Formosa',
    '909': 'Jujuy', '910': 'La Pampa', '911': 'La Rioja',
    '912': 'Mendoza', '913': 'Misiones', '914': 'Neuquén',
    '915': 'Río Negro', '916': 'Salta', '917': 'San Juan',
    '918': 'San Luis', '919': 'Santa Cruz', '920': 'Santa Fe',
    '921': 'Santiago del Estero', '922': 'Tucumán',
    '923': 'Tierra del Fuego',
}


def calcular_cm03(
    cursor, estudio_id: int, cliente_id: int, periodo: str,
    actividades: list[dict] = None,
) -> dict:
    """
    Calcula la declaración CM03 (mensual) para Convenio Multilateral.

    actividades: lista de dict con {jurisdiccion, base_imponible, alicuota}
    Si no se pasan, las obtiene de iibb_actividades + comprobantes_emitidos.
    """
    if not actividades:
        # Obtener actividades del cliente
        cursor.execute("""
            SELECT jurisdiccion, alicuota FROM iibb_actividades
            WHERE estudio_id = %s AND cliente_id = %s AND activa = TRUE
        """, (estudio_id, cliente_id))
        acts = cursor.fetchall()

        if not acts:
            return {'error': 'No hay actividades de IIBB configuradas para este cliente'}

        # Obtener facturación del período
        year, month = periodo.split('-')
        cursor.execute("""
            SELECT COALESCE(SUM(importe_neto), 0) as total_neto
            FROM comprobantes_emitidos
            WHERE estudio_id = %s
              AND EXTRACT(YEAR FROM fecha_emision) = %s
              AND EXTRACT(MONTH FROM fecha_emision) = %s
        """, (estudio_id, int(year), int(month)))
        row = cursor.fetchone()
        total_neto = Decimal(str(row['total_neto']))

        # Distribuir proporcionalmente (simplificado: por coeficiente)
        n_juris = len(acts)
        actividades = []
        for act in acts:
            actividades.append({
                'jurisdiccion': act['jurisdiccion'],
                'base_imponible': total_neto / n_juris,
                'alicuota': Decimal(str(act['alicuota'])),
            })

    detalle = []
    total_base = Decimal('0')
    total_impuesto = Decimal('0')

    for act in actividades:
        base = Decimal(str(act['base_imponible']))
        alic = Decimal(str(act['alicuota']))
        impuesto = (base * alic / 100).quantize(Decimal('0.01'))

        detalle.append({
            'jurisdiccion': act['jurisdiccion'],
            'jurisdiccion_nombre': JURISDICCIONES.get(act['jurisdiccion'], act['jurisdiccion']),
            'base_imponible': float(base),
            'alicuota': float(alic),
            'impuesto': float(impuesto),
        })
        total_base += base
        total_impuesto += impuesto

    # Obtener retenciones/percepciones del período
    cursor.execute("""
        SELECT
            COALESCE(SUM(CASE WHEN tipo = 'sufrida' AND impuesto = 'iibb' THEN importe_retenido ELSE 0 END), 0) as retenciones,
            COALESCE(SUM(CASE WHEN impuesto = 'iibb' THEN importe_retenido ELSE 0 END), 0) as percepciones
        FROM retenciones
        WHERE estudio_id = %s AND cliente_id = %s
          AND TO_CHAR(fecha, 'YYYY-MM') = %s
    """, (estudio_id, cliente_id, periodo))
    ret_row = cursor.fetchone()
    retenciones = Decimal(str(ret_row['retenciones'])) if ret_row else Decimal('0')
    percepciones = Decimal(str(ret_row['percepciones'])) if ret_row else Decimal('0')

    saldo_a_pagar = total_impuesto - retenciones - percepciones

    return {
        'periodo': periodo,
        'tipo': 'CM03',
        'detalle': detalle,
        'base_imponible': float(total_base),
        'impuesto': float(total_impuesto),
        'retenciones': float(retenciones),
        'percepciones': float(percepciones),
        'total_a_pagar': float(max(saldo_a_pagar, Decimal('0'))),
        'saldo_a_favor': float(abs(saldo_a_pagar)) if saldo_a_pagar < 0 else 0,
    }


def generar_xml_sifere(declaracion: dict) -> str:
    """Genera XML compatible con SIFERE para upload."""
    root = ET.Element('DDJJ')
    root.set('tipo', declaracion.get('tipo', 'CM03'))
    root.set('periodo', declaracion.get('periodo', ''))

    for item in declaracion.get('detalle', []):
        juris = ET.SubElement(root, 'Jurisdiccion')
        juris.set('codigo', item['jurisdiccion'])
        ET.SubElement(juris, 'BaseImponible').text = str(item['base_imponible'])
        ET.SubElement(juris, 'Alicuota').text = str(item['alicuota'])
        ET.SubElement(juris, 'Impuesto').text = str(item['impuesto'])

    totales = ET.SubElement(root, 'Totales')
    ET.SubElement(totales, 'BaseImponible').text = str(declaracion.get('base_imponible', 0))
    ET.SubElement(totales, 'Impuesto').text = str(declaracion.get('impuesto', 0))
    ET.SubElement(totales, 'Retenciones').text = str(declaracion.get('retenciones', 0))
    ET.SubElement(totales, 'APagar').text = str(declaracion.get('total_a_pagar', 0))

    return ET.tostring(root, encoding='unicode', xml_declaration=True)
