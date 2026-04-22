# -*- coding: utf-8 -*-
"""
Calendario impositivo — vencimientos AFIP/ARCA automáticos.

Genera fechas de vencimiento según terminación de CUIT y obligación fiscal.
Basado en las resoluciones generales de ARCA vigentes.
"""

from __future__ import annotations
from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class Vencimiento:
    fecha: date
    obligacion: str
    descripcion: str
    tipo: str  # iva, ganancias, iibb, monotributo, suss, informativa
    terminacion_cuit: str
    prioridad: str = 'normal'  # normal, alta, critica


# Vencimientos fijos mensuales (día del mes según terminación de CUIT)
# Fuente: RG ARCA - calendario fiscal
VENCIMIENTOS_BASE = {
    'iva': {
        'nombre': 'IVA - DDJJ mensual (F.2002)',
        'tipo': 'iva',
        'dias': {
            '0-1': 18, '2-3': 19, '4-5': 20, '6-7': 21, '8-9': 22,
        },
    },
    'sicore': {
        'nombre': 'SICORE - Retenciones y percepciones',
        'tipo': 'iva',
        'dias': {
            '0-1': 18, '2-3': 19, '4-5': 20, '6-7': 21, '8-9': 22,
        },
    },
    'monotributo': {
        'nombre': 'Monotributo - Pago mensual',
        'tipo': 'monotributo',
        'dias': {
            '0-1': 20, '2-3': 20, '4-5': 20, '6-7': 20, '8-9': 20,
        },
    },
    'iibb_cm03': {
        'nombre': 'IIBB - CM03 Convenio Multilateral',
        'tipo': 'iibb',
        'dias': {
            '0-1': 15, '2-3': 15, '4-5': 16, '6-7': 16, '8-9': 17,
        },
    },
    'suss_931': {
        'nombre': 'SUSS - F.931 Cargas sociales',
        'tipo': 'suss',
        'dias': {
            '0-1': 9, '2-3': 10, '4-5': 11, '6-7': 12, '8-9': 13,
        },
    },
    'libro_iva': {
        'nombre': 'Libro IVA Digital',
        'tipo': 'iva',
        'dias': {
            '0-1': 14, '2-3': 14, '4-5': 15, '6-7': 15, '8-9': 16,
        },
    },
}

# Vencimientos anuales (mes y día)
VENCIMIENTOS_ANUALES = [
    {
        'nombre': 'Ganancias PH - DDJJ Anual',
        'tipo': 'ganancias',
        'mes': 6, 'dia': 30,
        'aplica_a': 'persona_humana',
    },
    {
        'nombre': 'Ganancias PJ - DDJJ Anual (cierre dic)',
        'tipo': 'ganancias',
        'mes': 5, 'dia': 25,
        'aplica_a': 'persona_juridica',
    },
    {
        'nombre': 'Bienes Personales - DDJJ Anual',
        'tipo': 'informativa',
        'mes': 6, 'dia': 30,
        'aplica_a': 'persona_humana',
    },
    {
        'nombre': 'IIBB - CM05 Declaración Anual',
        'tipo': 'iibb',
        'mes': 6, 'dia': 30,
        'aplica_a': 'todos',
    },
]


def _terminacion_cuit(cuit: str) -> str:
    """Obtiene el último dígito del CUIT."""
    cuit_clean = cuit.replace('-', '').replace(' ', '')
    if len(cuit_clean) >= 11:
        return cuit_clean[-1]
    return '0'


def _dia_vencimiento(terminacion: str, dias_map: dict) -> int:
    """Busca el día de vencimiento según la terminación del CUIT."""
    t = int(terminacion)
    for rango, dia in dias_map.items():
        inicio, fin = rango.split('-')
        if int(inicio) <= t <= int(fin):
            return dia
    return 20  # fallback


def generar_vencimientos_mes(cuit: str, year: int, month: int,
                              condicion_iva: str = 'RI') -> list[Vencimiento]:
    """
    Genera los vencimientos de un mes para un CUIT dado.

    Args:
        cuit: CUIT del contribuyente
        year, month: año y mes
        condicion_iva: 'RI' (Responsable Inscripto), 'MT' (Monotributo), etc.
    """
    term = _terminacion_cuit(cuit)
    hoy = date.today()
    vencimientos = []

    for key, config in VENCIMIENTOS_BASE.items():
        # Filtrar por condición IVA
        if key == 'monotributo' and condicion_iva != 'MT':
            continue
        if key in ('iva', 'sicore', 'libro_iva', 'suss_931') and condicion_iva == 'MT':
            continue

        dia = _dia_vencimiento(term, config['dias'])
        try:
            fecha_vto = date(year, month, min(dia, 28))
        except ValueError:
            fecha_vto = date(year, month, 28)

        # Ajustar si cae en fin de semana
        while fecha_vto.weekday() >= 5:  # sáb=5, dom=6
            fecha_vto += timedelta(days=1)

        prioridad = 'normal'
        if fecha_vto <= hoy:
            prioridad = 'critica'  # ya venció
        elif (fecha_vto - hoy).days <= 5:
            prioridad = 'alta'

        vencimientos.append(Vencimiento(
            fecha=fecha_vto,
            obligacion=key,
            descripcion=config['nombre'],
            tipo=config['tipo'],
            terminacion_cuit=term,
            prioridad=prioridad,
        ))

    # Vencimientos anuales si corresponde al mes
    for v_anual in VENCIMIENTOS_ANUALES:
        if v_anual['mes'] != month:
            continue
        if v_anual['aplica_a'] == 'persona_humana' and condicion_iva == 'MT':
            continue

        try:
            fecha_vto = date(year, month, v_anual['dia'])
        except ValueError:
            fecha_vto = date(year, month, 28)

        while fecha_vto.weekday() >= 5:
            fecha_vto += timedelta(days=1)

        prioridad = 'normal'
        if fecha_vto <= hoy:
            prioridad = 'critica'
        elif (fecha_vto - hoy).days <= 5:
            prioridad = 'alta'

        vencimientos.append(Vencimiento(
            fecha=fecha_vto,
            obligacion=v_anual['nombre'].lower().replace(' ', '_'),
            descripcion=v_anual['nombre'],
            tipo=v_anual['tipo'],
            terminacion_cuit=term,
            prioridad=prioridad,
        ))

    vencimientos.sort(key=lambda v: v.fecha)
    return vencimientos


def generar_calendario(cuit: str, meses_adelante: int = 3,
                        condicion_iva: str = 'RI') -> list[Vencimiento]:
    """Genera vencimientos para los próximos N meses."""
    hoy = date.today()
    todos = []

    for i in range(meses_adelante + 1):
        mes = hoy.month + i
        year = hoy.year
        while mes > 12:
            mes -= 12
            year += 1
        todos.extend(generar_vencimientos_mes(cuit, year, mes, condicion_iva))

    return sorted(todos, key=lambda v: v.fecha)
