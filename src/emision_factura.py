# -*- coding: utf-8 -*-
"""
Emisión de facturas electrónicas con CAE via WSFEv1.

Flujo:
  1. FECompUltimoAutorizado → obtener siguiente número
  2. FECAESolicitar → solicitar CAE para el comprobante
  3. Guardar en DB local (comprobantes_emitidos)
"""

from __future__ import annotations

import html
import xml.etree.ElementTree as ET
from datetime import datetime, date
from decimal import Decimal
from dataclasses import dataclass, field


TIPOS_COMPROBANTE = {
    1: 'Factura A', 2: 'Nota de Débito A', 3: 'Nota de Crédito A',
    6: 'Factura B', 7: 'Nota de Débito B', 8: 'Nota de Crédito B',
    11: 'Factura C', 12: 'Nota de Débito C', 13: 'Nota de Crédito C',
    51: 'Factura M', 52: 'Nota de Débito M', 53: 'Nota de Crédito M',
}

TIPOS_CONCEPTO = {1: 'Productos', 2: 'Servicios', 3: 'Productos y Servicios'}

ALICUOTAS_IVA = {
    3: {'descripcion': '0%', 'porcentaje': Decimal('0')},
    4: {'descripcion': '10.5%', 'porcentaje': Decimal('10.5')},
    5: {'descripcion': '21%', 'porcentaje': Decimal('21')},
    6: {'descripcion': '27%', 'porcentaje': Decimal('27')},
    8: {'descripcion': '5%', 'porcentaje': Decimal('5')},
    9: {'descripcion': '2.5%', 'porcentaje': Decimal('2.5')},
}

TIPOS_DOCUMENTO = {
    80: 'CUIT', 86: 'CUIL', 96: 'DNI', 99: 'Sin identificar',
}


@dataclass
class ItemFactura:
    descripcion: str
    cantidad: Decimal = Decimal('1')
    precio_unitario: Decimal = Decimal('0')
    alicuota_iva_id: int = 5  # 21% por defecto
    bonificacion_pct: Decimal = Decimal('0')

    @property
    def subtotal(self) -> Decimal:
        base = self.cantidad * self.precio_unitario
        if self.bonificacion_pct:
            base -= base * self.bonificacion_pct / 100
        return base.quantize(Decimal('0.01'))

    @property
    def iva(self) -> Decimal:
        alicuota = ALICUOTAS_IVA.get(self.alicuota_iva_id, {}).get('porcentaje', Decimal('21'))
        return (self.subtotal * alicuota / 100).quantize(Decimal('0.01'))


@dataclass
class DatosFactura:
    tipo_comprobante: int
    punto_venta: int
    concepto: int = 1
    tipo_doc_receptor: int = 80
    nro_doc_receptor: str = ''
    receptor_nombre: str = ''
    items: list[ItemFactura] = field(default_factory=list)
    fecha_emision: date | None = None
    fecha_serv_desde: date | None = None
    fecha_serv_hasta: date | None = None
    fecha_vto_pago: date | None = None
    moneda: str = 'PES'
    cotizacion: Decimal = Decimal('1')

    @property
    def importe_neto(self) -> Decimal:
        return sum(item.subtotal for item in self.items)

    @property
    def importe_iva(self) -> Decimal:
        return sum(item.iva for item in self.items)

    @property
    def importe_total(self) -> Decimal:
        return self.importe_neto + self.importe_iva

    def iva_agrupado(self) -> list[dict]:
        """Agrupa IVA por alícuota para el request SOAP."""
        agrupado = {}
        for item in self.items:
            aid = item.alicuota_iva_id
            if aid not in agrupado:
                agrupado[aid] = {'base_imp': Decimal('0'), 'importe': Decimal('0')}
            agrupado[aid]['base_imp'] += item.subtotal
            agrupado[aid]['importe'] += item.iva
        return [
            {'id': k, 'base_imp': v['base_imp'], 'importe': v['importe']}
            for k, v in agrupado.items()
        ]


def solicitar_cae(client, cuit_emisor: str, datos: DatosFactura) -> dict:
    """
    Solicita CAE a AFIP via WSFEv1/FECAESolicitar.

    Args:
        client: instancia de WSFEv1Client (ya con cert/key)
        cuit_emisor: CUIT del emisor (contribuyente)
        datos: DatosFactura con los datos del comprobante

    Returns:
        dict con resultado: {success, cae, cae_vto, numero, observaciones, ...}
    """
    cuit = cuit_emisor.replace('-', '').replace(' ', '')

    # 1. Autenticar
    token, sign = client.autenticar_wsaa(cuit)

    # 2. Obtener último número autorizado
    ultimo_resp = client._wsfe_request('FECompUltimoAutorizado', {
        'punto_venta': datos.punto_venta,
        'tipo_comprobante': datos.tipo_comprobante,
    }, token, sign, cuit)

    root = ET.fromstring(ultimo_resp)
    ultimo_num = 0
    for elem in root.iter():
        if 'CbteNro' in elem.tag and elem.text:
            ultimo_num = int(elem.text)
            break

    siguiente = ultimo_num + 1
    fecha_emision = datos.fecha_emision or date.today()
    fecha_str = fecha_emision.strftime('%Y%m%d')

    # 3. Construir IVA array
    iva_xml = ''
    iva_items = datos.iva_agrupado()
    # Factura C no lleva detalle de IVA
    es_factura_c = datos.tipo_comprobante in (11, 12, 13)
    if not es_factura_c and iva_items:
        iva_parts = []
        for iv in iva_items:
            iva_parts.append(f"""
                <AlicIva>
                    <Id>{iv['id']}</Id>
                    <BaseImp>{iv['base_imp']}</BaseImp>
                    <Importe>{iv['importe']}</Importe>
                </AlicIva>""")
        iva_xml = f"<Iva>{''.join(iva_parts)}</Iva>"

    # 4. Importes
    if es_factura_c:
        imp_total = datos.importe_total
        imp_neto = datos.importe_total
        imp_iva = Decimal('0')
    else:
        imp_total = datos.importe_total
        imp_neto = datos.importe_neto
        imp_iva = datos.importe_iva

    # 5. Fechas de servicio (obligatorias para concepto 2 o 3)
    fechas_serv_xml = ''
    if datos.concepto in (2, 3):
        fsd = (datos.fecha_serv_desde or fecha_emision).strftime('%Y%m%d')
        fsh = (datos.fecha_serv_hasta or fecha_emision).strftime('%Y%m%d')
        fvp = (datos.fecha_vto_pago or fecha_emision).strftime('%Y%m%d')
        fechas_serv_xml = f"""
                    <FchServDesde>{fsd}</FchServDesde>
                    <FchServHasta>{fsh}</FchServHasta>
                    <FchVtoPago>{fvp}</FchVtoPago>"""

    # 6. Construir request FECAESolicitar
    soap_body = f"""
    <FECAESolicitar xmlns="http://ar.gov.afip.dif.FEV1/">
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit}</Cuit>
        </Auth>
        <FeCAEReq>
            <FeCabReq>
                <CantReg>1</CantReg>
                <PtoVta>{datos.punto_venta}</PtoVta>
                <CbteTipo>{datos.tipo_comprobante}</CbteTipo>
            </FeCabReq>
            <FeDetReq>
                <FECAEDetRequest>
                    <Concepto>{datos.concepto}</Concepto>
                    <DocTipo>{datos.tipo_doc_receptor}</DocTipo>
                    <DocNro>{datos.nro_doc_receptor}</DocNro>
                    <CbteDesde>{siguiente}</CbteDesde>
                    <CbteHasta>{siguiente}</CbteHasta>
                    <CbteFch>{fecha_str}</CbteFch>
                    <ImpTotal>{imp_total}</ImpTotal>
                    <ImpTotConc>0</ImpTotConc>
                    <ImpNeto>{imp_neto}</ImpNeto>
                    <ImpOpEx>0</ImpOpEx>
                    <ImpTrib>0</ImpTrib>
                    <ImpIVA>{imp_iva}</ImpIVA>
                    <MonId>{datos.moneda}</MonId>
                    <MonCotiz>{datos.cotizacion}</MonCotiz>{fechas_serv_xml}
                    {iva_xml}
                </FECAEDetRequest>
            </FeDetReq>
        </FeCAEReq>
    </FECAESolicitar>"""

    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    {soap_body}
</soap:Body>
</soap:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '"http://ar.gov.afip.dif.FEV1/FECAESolicitar"'
    }

    response = client._session.post(
        client.urls[client.ambiente]['wsfe'],
        data=soap_request.encode('utf-8'),
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()

    # 7. Parsear respuesta
    resp_root = ET.fromstring(response.text)
    resultado = {
        'success': False,
        'numero': siguiente,
        'punto_venta': datos.punto_venta,
        'tipo_comprobante': datos.tipo_comprobante,
        'tipo_comprobante_desc': TIPOS_COMPROBANTE.get(datos.tipo_comprobante, ''),
        'fecha_emision': fecha_str,
        'importe_total': float(imp_total),
        'importe_neto': float(imp_neto),
        'importe_iva': float(imp_iva),
        'cuit_emisor': cuit,
        'cuit_receptor': datos.nro_doc_receptor,
        'receptor_nombre': datos.receptor_nombre,
    }

    for elem in resp_root.iter():
        tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
        if tag == 'Resultado' and elem.text:
            resultado['estado'] = elem.text  # A=Aprobado, R=Rechazado, O=Observado
            resultado['success'] = elem.text in ('A', 'O')
        elif tag == 'CAE' and elem.text:
            resultado['cae'] = elem.text
        elif tag == 'CAEFchVto' and elem.text:
            resultado['cae_vto'] = elem.text
        elif tag == 'Obs' and elem.text:
            resultado.setdefault('observaciones', []).append(elem.text)
        elif tag == 'Msg' and elem.text:
            resultado.setdefault('observaciones', []).append(elem.text)
        elif tag == 'Err':
            for child in elem:
                child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                if child_tag == 'Msg' and child.text:
                    resultado.setdefault('errores', []).append(child.text)
                elif child_tag == 'Code' and child.text:
                    resultado['error_code'] = child.text

    return resultado
