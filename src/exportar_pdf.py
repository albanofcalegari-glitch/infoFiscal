# -*- coding: utf-8 -*-
"""
Exportación PDF de comprobantes emitidos.

Genera un PDF con formato fiscal estándar usando solo la biblioteca estándar
(sin dependencias externas como reportlab). Produce HTML y lo convierte
a PDF con weasyprint si está disponible, o devuelve HTML para impresión.
"""

from __future__ import annotations
from datetime import datetime
from io import BytesIO

TIPOS_COMPROBANTE = {
    1: 'Factura A', 2: 'Nota de Débito A', 3: 'Nota de Crédito A',
    6: 'Factura B', 7: 'Nota de Débito B', 8: 'Nota de Crédito B',
    11: 'Factura C', 12: 'Nota de Débito C', 13: 'Nota de Crédito C',
    51: 'Factura M',
}

LETRA_COMPROBANTE = {
    1: 'A', 2: 'A', 3: 'A',
    6: 'B', 7: 'B', 8: 'B',
    11: 'C', 12: 'C', 13: 'C',
    51: 'M',
}


def _formato_moneda(valor) -> str:
    try:
        return f"$ {float(valor):,.2f}"
    except (ValueError, TypeError):
        return "$ 0.00"


def _formato_cuit(cuit: str) -> str:
    c = str(cuit).replace('-', '').replace(' ', '')
    if len(c) == 11:
        return f"{c[:2]}-{c[2:10]}-{c[10]}"
    return cuit


def _generar_html_factura(comprobante: dict, estudio: dict) -> str:
    tipo = comprobante.get('tipo_comprobante', 0)
    letra = LETRA_COMPROBANTE.get(tipo, '?')
    nombre_tipo = TIPOS_COMPROBANTE.get(tipo, f'Comprobante tipo {tipo}')
    pto_vta = comprobante.get('punto_venta', 0)
    nro = comprobante.get('nro_comprobante', 0)

    fecha_emision = comprobante.get('fecha_emision', '')
    if hasattr(fecha_emision, 'strftime'):
        fecha_emision = fecha_emision.strftime('%d/%m/%Y')

    cae = comprobante.get('cae', '')
    cae_vto = comprobante.get('cae_vto', '')
    if hasattr(cae_vto, 'strftime'):
        cae_vto = cae_vto.strftime('%d/%m/%Y')

    emisor_nombre = estudio.get('nombre', '') if estudio else ''
    emisor_cuit = _formato_cuit(estudio.get('cuit', '')) if estudio else ''
    emisor_domicilio = estudio.get('domicilio_fiscal', '') if estudio else ''

    receptor_nombre = comprobante.get('receptor_nombre', '')
    receptor_cuit = _formato_cuit(comprobante.get('cuit_receptor', ''))

    neto = _formato_moneda(comprobante.get('importe_neto', 0))
    iva = _formato_moneda(comprobante.get('importe_iva', 0))
    total = _formato_moneda(comprobante.get('importe_total', 0))

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
    @page {{ size: A4; margin: 15mm; }}
    body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11px; color: #333; margin: 0; padding: 0; }}
    .header {{ display: flex; justify-content: space-between; border: 2px solid #333; padding: 10px; }}
    .header-left, .header-right {{ width: 45%; }}
    .letra {{ display: flex; align-items: center; justify-content: center; width: 50px; height: 50px;
              border: 2px solid #333; font-size: 28px; font-weight: bold; margin: 0 auto; }}
    .tipo-cbte {{ text-align: center; font-size: 14px; font-weight: bold; margin-top: 5px; }}
    .info-row {{ display: flex; justify-content: space-between; border: 1px solid #ccc; padding: 8px; margin-top: 5px; }}
    .receptor {{ border: 1px solid #ccc; padding: 10px; margin-top: 10px; }}
    .detalle {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
    .detalle th {{ background: #f0f0f0; border: 1px solid #ccc; padding: 6px; text-align: left; }}
    .detalle td {{ border: 1px solid #ccc; padding: 6px; }}
    .totales {{ margin-top: 15px; text-align: right; }}
    .totales table {{ margin-left: auto; border-collapse: collapse; }}
    .totales td {{ padding: 4px 10px; }}
    .totales .total {{ font-size: 14px; font-weight: bold; border-top: 2px solid #333; }}
    .cae-box {{ border: 1px solid #ccc; padding: 10px; margin-top: 20px; text-align: center; font-size: 10px; }}
    .cae-num {{ font-size: 14px; font-weight: bold; letter-spacing: 2px; }}
</style>
</head>
<body>
    <div class="header">
        <div class="header-left">
            <div style="font-size:16px;font-weight:bold;">{emisor_nombre}</div>
            <div style="margin-top:5px;">CUIT: {emisor_cuit}</div>
            <div>{emisor_domicilio}</div>
        </div>
        <div style="text-align:center;">
            <div class="letra">{letra}</div>
            <div class="tipo-cbte">{nombre_tipo}</div>
        </div>
        <div class="header-right" style="text-align:right;">
            <div style="font-size:14px;font-weight:bold;">
                Punto de Venta: {pto_vta:04d} - Comp. Nro: {nro:08d}
            </div>
            <div style="margin-top:5px;">Fecha de Emision: {fecha_emision}</div>
        </div>
    </div>

    <div class="receptor">
        <div><strong>Razon Social:</strong> {receptor_nombre}</div>
        <div><strong>CUIT:</strong> {receptor_cuit}</div>
    </div>

    <table class="detalle">
        <thead>
            <tr>
                <th style="width:60%">Descripcion</th>
                <th style="text-align:right">Subtotal</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Segun comprobante electronico</td>
                <td style="text-align:right">{neto}</td>
            </tr>
        </tbody>
    </table>

    <div class="totales">
        <table>
            <tr><td>Importe Neto:</td><td style="text-align:right">{neto}</td></tr>
            {'<tr><td>IVA 21%:</td><td style="text-align:right">' + iva + '</td></tr>' if tipo not in (11, 12, 13) else ''}
            <tr class="total"><td>Total:</td><td style="text-align:right">{total}</td></tr>
        </table>
    </div>

    <div class="cae-box">
        <div>CAE N&deg;: <span class="cae-num">{cae}</span></div>
        <div>Fecha de Vto. de CAE: {cae_vto}</div>
    </div>
</body>
</html>"""


def generar_pdf_factura(comprobante: dict, estudio: dict) -> bytes:
    html = _generar_html_factura(comprobante, estudio)

    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        return pdf
    except ImportError:
        pass

    return html.encode('utf-8')
