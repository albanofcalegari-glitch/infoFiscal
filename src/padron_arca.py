# -*- coding: utf-8 -*-
"""
Consulta al Padrón Extendido de ARCA (ex AFIP).

Dos fuentes:
  1. API pública de ARCA (no requiere certificado) — datos básicos
  2. Web Service ws_sr_padron_a13 (requiere certificado) — datos extendidos

La fuente 1 siempre se intenta primero por ser más rápida y sin auth.
La fuente 2 se usa como complemento si hay certificado disponible.
"""

from __future__ import annotations

import re
import requests
from datetime import datetime


# Mapeos de códigos
CONDICIONES_IVA = {
    1: 'IVA Responsable Inscripto',
    2: 'IVA Responsable No Inscripto',
    3: 'IVA No Responsable',
    4: 'IVA Sujeto Exento',
    5: 'Consumidor Final',
    6: 'Responsable Monotributo',
    7: 'Sujeto No Categorizado',
    8: 'Proveedor del Exterior',
    9: 'Cliente del Exterior',
    10: 'IVA Liberado - Ley Nº 19.640',
    11: 'IVA Responsable Inscripto - Agente de Percepción',
    12: 'Pequeño Contribuyente Eventual',
    13: 'Monotributista Social',
    14: 'Pequeño Contribuyente Eventual Social',
    15: 'IVA No Alcanzado',
}

TIPOS_PERSONA = {
    'F': 'Física',
    'J': 'Jurídica',
}

CATEGORIAS_MONOTRIBUTO = {
    1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E',
    6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K',
}


def validar_cuit(cuit: str) -> str | None:
    """Valida y limpia un CUIT. Retorna el CUIT limpio (11 dígitos) o None si es inválido."""
    cuit_clean = re.sub(r'[^0-9]', '', cuit)
    if len(cuit_clean) != 11:
        return None
    multiplicadores = [5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    suma = sum(int(cuit_clean[i]) * multiplicadores[i] for i in range(10))
    resto = suma % 11
    dv = 11 - resto
    if dv == 11:
        dv = 0
    elif dv == 10:
        dv = 9
    if dv != int(cuit_clean[10]):
        return None
    return cuit_clean


def formatear_cuit(cuit: str) -> str:
    """20-12345678-9"""
    c = re.sub(r'[^0-9]', '', cuit)
    if len(c) == 11:
        return f"{c[:2]}-{c[2:10]}-{c[10]}"
    return cuit


def consultar_padron_publico(cuit: str) -> dict:
    """
    Consulta la API pública de ARCA para obtener datos del contribuyente.
    No requiere autenticación.

    Retorna dict con los datos o {'error': '...'} si falla.
    """
    cuit_clean = validar_cuit(cuit)
    if not cuit_clean:
        return {'error': 'CUIT inválido'}

    url = f"https://soa.afip.gob.ar/sr-padron/v2/persona/{cuit_clean}"

    try:
        resp = requests.get(url, timeout=15, verify=True)

        if resp.status_code == 404:
            return {'error': f'CUIT {formatear_cuit(cuit_clean)} no encontrado en el padrón'}

        if resp.status_code != 200:
            return {'error': f'Error del servicio ARCA (HTTP {resp.status_code})'}

        data = resp.json()

        if not data.get('success', True):
            return {'error': data.get('error', {}).get('mensaje', 'Error desconocido')}

        persona = data.get('data', data)

        resultado = _parsear_persona(persona, cuit_clean)
        resultado['fuente'] = 'Padrón Público ARCA'
        resultado['consultado_at'] = datetime.now().isoformat()
        return resultado

    except requests.exceptions.Timeout:
        return {'error': 'Timeout conectando con ARCA (>15s)'}
    except requests.exceptions.ConnectionError:
        return {'error': 'No se pudo conectar con el servicio de ARCA'}
    except Exception as e:
        return {'error': f'Error consultando padrón: {str(e)}'}


def _parsear_persona(data: dict, cuit: str) -> dict:
    """Parsea la respuesta del padrón público a un formato normalizado."""
    tipo_persona = data.get('tipoPersona', '')

    # Nombre/Razón social
    if tipo_persona == 'F':
        nombre = data.get('nombre', '')
        apellido = data.get('apellido', '')
        razon_social = f"{apellido}, {nombre}" if apellido else nombre
    else:
        razon_social = data.get('razonSocial', data.get('nombre', ''))

    # Domicilio
    domicilio_data = data.get('domicilioFiscal', {})
    domicilio_parts = []
    if domicilio_data.get('direccion'):
        domicilio_parts.append(domicilio_data['direccion'])
    if domicilio_data.get('localidad'):
        domicilio_parts.append(domicilio_data['localidad'])
    if domicilio_data.get('descripcionProvincia'):
        domicilio_parts.append(domicilio_data['descripcionProvincia'])
    if domicilio_data.get('codPostal'):
        domicilio_parts.append(f"CP {domicilio_data['codPostal']}")
    domicilio = ', '.join(domicilio_parts) if domicilio_parts else 'No informado'

    # Condición IVA
    id_imp_iva = None
    condicion_iva_texto = 'No informado'
    impuestos = data.get('impuestos', [])
    for imp in impuestos:
        if imp.get('idImpuesto') == 32:  # IVA
            id_imp_iva = 32
            condicion_iva_texto = 'IVA Responsable Inscripto'
            break
        elif imp.get('idImpuesto') == 20:  # Monotributo
            id_imp_iva = 20
            condicion_iva_texto = 'Responsable Monotributo'
            break

    # Si no tiene IVA ni monotributo, puede ser exento
    if not id_imp_iva:
        for imp in impuestos:
            if imp.get('idImpuesto') == 33:  # Exento
                condicion_iva_texto = 'IVA Sujeto Exento'
                break

    # Actividades
    actividades = []
    for act in data.get('actividades', []):
        actividades.append({
            'codigo': act.get('idActividad', ''),
            'descripcion': act.get('descripcionActividad', ''),
            'periodo': act.get('periodo', ''),
            'orden': act.get('orden', 0),
        })
    actividades.sort(key=lambda a: a.get('orden', 99))

    # Categoría monotributo
    categoria_mt = None
    if id_imp_iva == 20:
        categorias = data.get('categoriasMonotributo', data.get('categoriaMonotributo', []))
        if isinstance(categorias, list) and categorias:
            cat = categorias[-1]  # última categoría (más reciente)
            cat_id = cat.get('idCategoria', cat.get('categoria', ''))
            categoria_mt = CATEGORIAS_MONOTRIBUTO.get(cat_id, str(cat_id))
        elif isinstance(categorias, dict):
            cat_id = categorias.get('idCategoria', categorias.get('categoria', ''))
            categoria_mt = CATEGORIAS_MONOTRIBUTO.get(cat_id, str(cat_id))

    # Fecha inscripción
    fecha_inscripcion = None
    mat = data.get('mesPeriodo') or data.get('fechaInscripcion')
    if mat:
        fecha_inscripcion = str(mat)

    return {
        'cuit': formatear_cuit(cuit),
        'cuit_raw': cuit,
        'tipo_persona': TIPOS_PERSONA.get(tipo_persona, tipo_persona),
        'tipo_persona_codigo': tipo_persona,
        'razon_social': razon_social,
        'condicion_iva': condicion_iva_texto,
        'categoria_monotributo': categoria_mt,
        'domicilio_fiscal': domicilio,
        'domicilio_detalle': {
            'direccion': domicilio_data.get('direccion', ''),
            'localidad': domicilio_data.get('localidad', ''),
            'provincia': domicilio_data.get('descripcionProvincia', ''),
            'codigo_postal': domicilio_data.get('codPostal', ''),
        },
        'actividades': actividades,
        'impuestos': [
            {
                'id': imp.get('idImpuesto'),
                'descripcion': imp.get('descripcionImpuesto', ''),
                'periodo': imp.get('periodo', ''),
            }
            for imp in impuestos
        ],
        'estado': data.get('estadoClave', data.get('estado', 'ACTIVO')),
        'fecha_inscripcion': fecha_inscripcion,
    }
