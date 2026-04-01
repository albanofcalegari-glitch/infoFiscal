#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simulador de WSMTXCA para probar la interfaz web
"""

from flask import Flask, jsonify, render_template, request
from pathlib import Path
import random
from datetime import datetime, timedelta

app = Flask(__name__)

def generar_datos_simulados():
    """Generar datos simulados de comprobantes WSMTXCA"""
    
    # Datos base simulados
    comprobantes_ejemplo = [
        {
            'tipo': 11, 'punto_venta': 1, 'numero': 1,
            'cae': '74123456789012', 'fecha_emision': '2025-09-15',
            'importe_total': '15750.00', 'receptor_denominacion': 'ACME Corporation SA',
            'items': [
                {'codigo_mtx': 'MTX001', 'descripcion': 'Producto Premium', 'cantidad': 2, 'precio_unitario': '5000.00', 'importe_total': '10000.00'},
                {'codigo_mtx': 'MTX002', 'descripcion': 'Servicio Especializado', 'cantidad': 1, 'precio_unitario': '5750.00', 'importe_total': '5750.00'}
            ]
        },
        {
            'tipo': 11, 'punto_venta': 1, 'numero': 2,
            'cae': '74123456789013', 'fecha_emision': '2025-09-20',
            'importe_total': '8900.00', 'receptor_denominacion': 'Distribuidora XYZ SRL',
            'items': [
                {'codigo_mtx': 'MTX003', 'descripcion': 'Insumo Industrial', 'cantidad': 10, 'precio_unitario': '890.00', 'importe_total': '8900.00'}
            ]
        },
        {
            'tipo': 51, 'punto_venta': 1, 'numero': 1,
            'cae': '74123456789014', 'fecha_emision': '2025-09-25',
            'importe_total': '3500.00', 'receptor_denominacion': 'Cliente Final',
            'items': [
                {'codigo_mtx': 'MTX004', 'descripcion': 'Servicio Monotributo', 'cantidad': 1, 'precio_unitario': '3500.00', 'importe_total': '3500.00'}
            ]
        },
        {
            'tipo': 1, 'punto_venta': 2, 'numero': 1,
            'cae': '74123456789015', 'fecha_emision': '2025-09-30',
            'importe_total': '25600.00', 'receptor_denominacion': 'Empresa Grande SA',
            'items': [
                {'codigo_mtx': 'MTX005', 'descripcion': 'Equipo Especializado', 'cantidad': 1, 'precio_unitario': '21487.60', 'importe_total': '21487.60'},
                {'codigo_mtx': 'MTX006', 'descripcion': 'Instalación', 'cantidad': 1, 'precio_unitario': '4112.40', 'importe_total': '4112.40'}
            ]
        }
    ]
    
    return comprobantes_ejemplo

@app.route('/')
def index():
    return render_template('consulta_wsmtxca.html')

@app.route('/buscar-wsmtxca-completo')
def buscar_wsmtxca_completo():
    """Simulador del endpoint de búsqueda completa"""
    
    # Obtener parámetros
    cuit = request.args.get('cuit', '').strip()
    punto_venta = request.args.get('punto_venta', '').strip()
    limite = int(request.args.get('limite', 25))
    
    if not cuit:
        return jsonify({
            'success': False,
            'error': 'CUIT es requerido'
        }), 400
    
    # Simular datos
    comprobantes = generar_datos_simulados()
    
    # Convertir a formato de respuesta
    resultados = []
    for comp in comprobantes:
        resultado = {
            'status': 'encontrado',
            'datos': {
                'tipo_comprobante': f"Tipo {comp['tipo']}",
                'punto_venta': comp['punto_venta'],
                'numero_comprobante': comp['numero'],
                'cae': comp['cae'],
                'fecha_emision': comp['fecha_emision'],
                'importe_total': comp['importe_total'],
                'receptor_denominacion': comp['receptor_denominacion'],
                'cantidad_items': len(comp['items'])
            },
            'items': comp['items'],
            'consulta': {
                'cuit': cuit,
                'tipo': comp['tipo'],
                'punto_venta': comp['punto_venta'],
                'numero': comp['numero']
            }
        }
        resultados.append(resultado)
    
    return jsonify({
        'success': True,
        'cuit': cuit,
        'consultas_realizadas': len(resultados),
        'total_encontrados': len(resultados),
        'resultados': resultados,
        'puntos_venta_consultados': [1, 2],
        'limite_aplicado': limite
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001)