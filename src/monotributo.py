# -*- coding: utf-8 -*-
"""
Monitor de Monotributo — categorías, límites y alertas.

Tabla de categorías vigentes 2024/2025 (actualizar cuando ARCA publique nuevos valores).
Calcula la posición del contribuyente sobre un período de 12 meses rolling
y alerta cuando supera el 80% o 90% del límite de su categoría.
"""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal

# Categorías Monotributo vigentes (actualización enero 2025)
# Fuente: RG ARCA / ex AFIP
CATEGORIAS_MONOTRIBUTO = {
    'A': {'tope_anual': Decimal('7_813_063.45'),  'tope_mensual': Decimal('651_088.62')},
    'B': {'tope_anual': Decimal('11_447_046.44'), 'tope_mensual': Decimal('953_920.54')},
    'C': {'tope_anual': Decimal('16_050_091.57'), 'tope_mensual': Decimal('1_337_507.63')},
    'D': {'tope_anual': Decimal('19_926_340.10'), 'tope_mensual': Decimal('1_660_528.34')},
    'E': {'tope_anual': Decimal('23_439_812.32'), 'tope_mensual': Decimal('1_953_317.69')},
    'F': {'tope_anual': Decimal('29_374_695.90'), 'tope_mensual': Decimal('2_447_891.33')},
    'G': {'tope_anual': Decimal('35_128_502.31'), 'tope_mensual': Decimal('2_927_375.19')},
    'H': {'tope_anual': Decimal('53_267_481.42'), 'tope_mensual': Decimal('4_438_956.79')},
    'I': {'tope_anual': Decimal('59_657_192.40'), 'tope_mensual': Decimal('4_971_432.70')},
    'J': {'tope_anual': Decimal('68_318_880.39'), 'tope_mensual': Decimal('5_693_240.03')},
    'K': {'tope_anual': Decimal('82_370_281.28'), 'tope_mensual': Decimal('6_864_190.11')},
}


@dataclass
class MonitributoStatus:
    categoria: str
    tope_anual: Decimal
    facturado_12m: Decimal
    porcentaje: float
    alerta: str | None  # None, 'warning' (80%), 'danger' (90%), 'exceeded' (100%+)
    categoria_sugerida: str | None
    meses_datos: int


def calcular_posicion(categoria: str, facturado_12m: Decimal, meses_datos: int = 12) -> MonitributoStatus:
    """
    Calcula la posición del contribuyente respecto al tope de su categoría.

    Args:
        categoria: Letra de categoría actual (A-K)
        facturado_12m: Total facturado en los últimos 12 meses
        meses_datos: Cuántos meses de datos tenemos (para proyectar si <12)
    """
    cat = categoria.upper()
    if cat not in CATEGORIAS_MONOTRIBUTO:
        return MonitributoStatus(
            categoria=cat, tope_anual=Decimal(0), facturado_12m=facturado_12m,
            porcentaje=0, alerta=None, categoria_sugerida=None, meses_datos=meses_datos
        )

    tope = CATEGORIAS_MONOTRIBUTO[cat]['tope_anual']

    # Si tenemos menos de 12 meses, proyectar
    if 0 < meses_datos < 12:
        proyectado = (facturado_12m / meses_datos) * 12
    else:
        proyectado = facturado_12m

    porcentaje = float(proyectado / tope * 100) if tope > 0 else 0

    # Determinar alerta
    alerta = None
    if porcentaje >= 100:
        alerta = 'exceeded'
    elif porcentaje >= 90:
        alerta = 'danger'
    elif porcentaje >= 80:
        alerta = 'warning'

    # Sugerir categoría si excede
    categoria_sugerida = None
    if porcentaje >= 90:
        categorias_ordenadas = sorted(CATEGORIAS_MONOTRIBUTO.items(),
                                       key=lambda x: x[1]['tope_anual'])
        for letra, limites in categorias_ordenadas:
            if limites['tope_anual'] > proyectado:
                categoria_sugerida = letra
                break
        if not categoria_sugerida and porcentaje >= 100:
            categoria_sugerida = 'Excede Monotributo - evaluar RI'

    return MonitributoStatus(
        categoria=cat,
        tope_anual=tope,
        facturado_12m=facturado_12m,
        porcentaje=round(porcentaje, 1),
        alerta=alerta,
        categoria_sugerida=categoria_sugerida,
        meses_datos=meses_datos,
    )


def get_todas_categorias() -> list[dict]:
    """Retorna todas las categorías con sus topes para mostrar en la UI."""
    return [
        {
            'letra': k,
            'tope_anual': float(v['tope_anual']),
            'tope_mensual': float(v['tope_mensual']),
        }
        for k, v in sorted(CATEGORIAS_MONOTRIBUTO.items())
    ]
