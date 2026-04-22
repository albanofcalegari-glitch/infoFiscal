# -*- coding: utf-8 -*-
"""
Módulo de retenciones — calculadora y consulta de padrones provinciales.

Padrones soportados:
  - AGIP (CABA): alícuotas de retención/percepción IIBB
  - ARBA (PBA): alícuotas de retención/percepción IIBB
  - LUA (Córdoba): futuro

Las alícuotas se cachean en padron_retenciones_cache.
"""

from __future__ import annotations
from decimal import Decimal
from datetime import date

REGIMENES_RETENCION = {
    'iva': {
        'codigo': '767',
        'descripcion': 'Retención IVA (RG 2854)',
        'alicuota_inscripto': Decimal('6'),
        'alicuota_no_inscripto': Decimal('10.5'),
        'minimo_no_sujeto': Decimal('200000'),
    },
    'ganancias': {
        'codigo': '830',
        'descripcion': 'Retención Ganancias (RG 830)',
        'escalas': True,
    },
    'suss': {
        'codigo': '3726',
        'descripcion': 'Retención SUSS (RG 3726)',
        'alicuota': Decimal('11'),
    },
}


def calcular_retencion_iva(
    importe_base: Decimal,
    condicion_receptor: str = 'inscripto',
    alicuota_override: Decimal | None = None,
) -> dict:
    """Calcula retención de IVA según RG 2854."""
    reg = REGIMENES_RETENCION['iva']
    minimo = reg['minimo_no_sujeto']

    if importe_base < minimo:
        return {
            'retencion': Decimal('0'),
            'motivo': f'Importe menor al mínimo no sujeto a retención (${minimo})',
        }

    if alicuota_override:
        alicuota = alicuota_override
    elif condicion_receptor == 'inscripto':
        alicuota = reg['alicuota_inscripto']
    else:
        alicuota = reg['alicuota_no_inscripto']

    retencion = (importe_base * alicuota / 100).quantize(Decimal('0.01'))

    return {
        'retencion': retencion,
        'base_imponible': importe_base,
        'alicuota': float(alicuota),
        'regimen': reg['codigo'],
        'descripcion': reg['descripcion'],
    }


ESCALAS_GANANCIAS_2025 = [
    (Decimal('0'),       Decimal('45000'),    Decimal('0'),    Decimal('10')),
    (Decimal('45000'),   Decimal('90000'),    Decimal('4500'), Decimal('14')),
    (Decimal('90000'),   Decimal('150000'),   Decimal('10800'), Decimal('18')),
    (Decimal('150000'),  Decimal('250000'),   Decimal('21600'), Decimal('22')),
    (Decimal('250000'),  Decimal('500000'),   Decimal('43600'), Decimal('26')),
    (Decimal('500000'),  Decimal('1000000'),  Decimal('108600'), Decimal('28')),
    (Decimal('1000000'), Decimal('999999999'), Decimal('248600'), Decimal('30')),
]


def calcular_retencion_ganancias(
    importe_base: Decimal,
    tipo_renta: str = 'servicios',
) -> dict:
    """Calcula retención de Ganancias según RG 830 (simplificado)."""
    for desde, hasta, fijo, porc in ESCALAS_GANANCIAS_2025:
        if desde <= importe_base < hasta:
            excedente = importe_base - desde
            retencion = fijo + (excedente * porc / 100)
            return {
                'retencion': retencion.quantize(Decimal('0.01')),
                'base_imponible': importe_base,
                'alicuota': float(porc),
                'fijo': float(fijo),
                'regimen': '830',
                'descripcion': f'Retención Ganancias - {tipo_renta}',
            }

    return {'retencion': Decimal('0'), 'motivo': 'Fuera de escala'}


def consultar_padron_agip(cuit: str) -> dict | None:
    """
    Consulta el padrón de AGIP (CABA) para obtener alícuotas.
    Retorna dict con alicuota_ret y alicuota_perc, o None si no se encuentra.
    """
    import requests
    cuit_clean = cuit.replace('-', '').replace(' ', '')

    try:
        resp = requests.get(
            f"https://www.agip.gob.ar/agentes/api/padron/{cuit_clean}",
            timeout=10,
            headers={'Accept': 'application/json'},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'cuit': cuit_clean,
                'jurisdiccion': 'AGIP',
                'alicuota_ret': data.get('alicuotaRetencion'),
                'alicuota_perc': data.get('alicuotaPercepcion'),
                'grupo': data.get('grupo', ''),
            }
    except Exception:
        pass
    return None


def consultar_padron_arba(cuit: str) -> dict | None:
    """
    Consulta el padrón de ARBA (PBA) para obtener alícuotas.
    Retorna dict con alicuota_ret y alicuota_perc, o None.
    """
    import requests
    cuit_clean = cuit.replace('-', '').replace(' ', '')

    try:
        resp = requests.get(
            f"https://dfrweb.arba.gov.ar/agentes/api/padron/{cuit_clean}",
            timeout=10,
            headers={'Accept': 'application/json'},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                'cuit': cuit_clean,
                'jurisdiccion': 'ARBA',
                'alicuota_ret': data.get('alicuotaRetencion'),
                'alicuota_perc': data.get('alicuotaPercepcion'),
                'grupo': data.get('grupo', ''),
            }
    except Exception:
        pass
    return None
