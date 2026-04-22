#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente para WSMTXCA - Facturación Electrónica con Códigos MTX (detalle de items)
Autor: InfoFiscal
Fecha: 2025

WSMTXCA: Comprobantes con detalle de items y códigos MTX
A diferencia de WSFEv1, este servicio devuelve el detalle de cada item facturado.
"""

import os
import sys
import ssl
import time
import html
import json
import base64
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import requests
import subprocess
import urllib3
from requests.adapters import HTTPAdapter

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WSMTXCAClient:
    """Cliente para WSMTXCA (Comprobantes con código MTX)

    Soporta dos estilos de llamada para consultar_comprobante:
      - Estilo 1 (posicional):  consultar_comprobante(cuit, tipo, punto_venta, numero)
      - Estilo 2 (nombrado):    consultar_comprobante(cuit_representada=..., tipo_comprobante=...,
                                                       punto_venta=..., numero_comprobante=...)
    """

    def __init__(self, cert_path, key_path, ambiente='prod'):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ambiente = ambiente

        # URLs de AFIP
        self.urls = {
            'prod': {
                'wsaa': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
                'wsmtxca': 'https://serviciosjava.afip.gob.ar/wsmtxca/services/MTXCAService'
            },
            'homo': {
                'wsaa': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
                'wsmtxca': 'https://fwshomo.afip.gov.ar/wsmtxca/services/MTXCAService'
            }
        }

        # Cache para tokens
        self._token_cache = {}

        # Sesión HTTP con SSL permisivo (SECLEVEL=1 para AFIP)
        from src.ssl_afip_config import crear_session_afip
        self._session = crear_session_afip()

        # Tipos de comprobante (igual que WSFEv1 + FCE)
        self.tipos_comprobante = {
            1: "Factura A",
            2: "Nota de Débito A",
            3: "Nota de Crédito A",
            6: "Factura B",
            7: "Nota de Débito B",
            8: "Nota de Crédito B",
            11: "Factura C",
            12: "Nota de Débito C",
            13: "Nota de Crédito C",
            51: "Factura M",
            52: "Nota de Débito M",
            53: "Nota de Crédito M",
            201: "FCE Factura A",
            206: "FCE Factura B"
        }

        print(f"Cliente WSMTXCA inicializado - Ambiente: {ambiente.upper()}")

    # ------------------------------------------------------------------
    # Autenticación WSAA
    # ------------------------------------------------------------------

    def _detectar_openssl(self):
        """Detectar OpenSSL disponible"""
        paths = [
            'openssl',
            'C:\\Program Files\\Git\\usr\\bin\\openssl.exe',
            'C:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe'
        ]
        for path in paths:
            try:
                result = subprocess.run([path, 'version'],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return path
            except Exception:
                continue
        raise Exception("OpenSSL no encontrado")

    def _validar_cuit(self, cuit):
        """Validar y limpiar CUIT"""
        cuit_clean = str(cuit).replace('-', '').replace(' ', '')
        if not cuit_clean.isdigit() or len(cuit_clean) != 11:
            raise ValueError(f"CUIT inválido: {cuit} (debe tener 11 dígitos)")
        return cuit_clean

    def _crear_tra(self):
        """Crear TRA para WSMTXCA"""
        now = datetime.now()
        gen_time = now - timedelta(minutes=10)
        exp_time = now + timedelta(hours=12)

        unique_id = int(time.time())
        gen_time_str = gen_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '-03:00'
        exp_time_str = exp_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '-03:00'

        return f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
<uniqueId>{unique_id}</uniqueId>
<generationTime>{gen_time_str}</generationTime>
<expirationTime>{exp_time_str}</expirationTime>
</header>
<service>wsmtxca</service>
</loginTicketRequest>"""

    def _firmar_tra(self, tra_xml):
        """Firmar TRA con OpenSSL"""
        openssl_cmd = self._detectar_openssl()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp_xml:
            tmp_xml.write(tra_xml)
            tra_file = tmp_xml.name

        cms_file = tempfile.mktemp(suffix='.cms')

        try:
            cmd = [
                openssl_cmd, 'smime', '-sign',
                '-in', tra_file,
                '-out', cms_file,
                '-outform', 'DER',
                '-signer', self.cert_path,
                '-inkey', self.key_path,
                '-nodetach'
            ]
            subprocess.run(cmd, capture_output=True, check=True)

            with open(cms_file, 'rb') as f:
                return f.read()
        finally:
            if os.path.exists(tra_file):
                os.unlink(tra_file)
            if os.path.exists(cms_file):
                os.unlink(cms_file)

    def autenticar_wsaa(self, cuit_representada=None):
        """Autenticar con WSAA para WSMTXCA.

        Retorna (token, sign).
        """
        cache_key = f"wsmtxca_{self.ambiente}"
        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if cached['expires'] > datetime.now():
                return cached['token'], cached['sign']

        tra_xml = self._crear_tra()
        signed_tra = self._firmar_tra(tra_xml)
        tra_b64 = base64.b64encode(signed_tra).decode('utf-8')

        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    <loginCms xmlns="http://wsaa.view.sua.dvadac.desein.afip.gov">
        <in0>{tra_b64}</in0>
    </loginCms>
</soap:Body>
</soap:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        }

        response = self._session.post(
            self.urls[self.ambiente]['wsaa'],
            data=soap_request,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        login_return = None
        for elem in root.iter():
            if 'loginCmsReturn' in elem.tag:
                login_return = elem.text
                break

        if not login_return:
            raise Exception("loginCmsReturn no encontrado en respuesta WSAA")

        login_xml = html.unescape(login_return)
        login_root = ET.fromstring(login_xml)

        credentials = {}
        for child in login_root.iter():
            if child.tag in ['token', 'sign']:
                credentials[child.tag] = child.text

        if 'token' not in credentials or 'sign' not in credentials:
            raise Exception("Token/Sign no encontrados en respuesta WSAA")

        expires = datetime.now() + timedelta(hours=11, minutes=50)
        self._token_cache[cache_key] = {
            'token': credentials['token'],
            'sign': credentials['sign'],
            'expires': expires
        }

        return credentials['token'], credentials['sign']

    # ------------------------------------------------------------------
    # Requests WSMTXCA
    # ------------------------------------------------------------------

    def _wsmtxca_request(self, soap_body):
        """Enviar request SOAP a WSMTXCA"""
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:ser="http://impl.service.wsmtxca.afip.gov.ar/">
<soapenv:Body>
    {soap_body}
</soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': ''
        }

        session = requests.Session()

        class _CustomHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)

        session.mount('https://', _CustomHTTPAdapter())

        response = session.post(
            self.urls[self.ambiente]['wsmtxca'],
            data=soap_envelope,
            headers=headers,
            timeout=30,
            verify=False
        )

        response.raise_for_status()
        return response.text

    # ------------------------------------------------------------------
    # Consulta de comprobantes
    # ------------------------------------------------------------------

    def consultar_comprobante(self, cuit=None, tipo=None, punto_venta=None, numero=None,
                              *, cuit_representada=None, tipo_comprobante=None,
                              numero_comprobante=None):
        """Consultar un comprobante WSMTXCA.

        Acepta dos estilos de llamada:
          Estilo 1 (posicional): consultar_comprobante(cuit, tipo, punto_venta, numero)
          Estilo 2 (keyword):    consultar_comprobante(cuit_representada=..., tipo_comprobante=...,
                                                       punto_venta=..., numero_comprobante=...)

        Retorna dict con {'status': 'encontrado'|'no_encontrado', 'datos': {...}, 'items': [...]}
        o None si no se encontró y se llamó con estilo 2.
        """
        # Normalizar parámetros: aceptar ambos estilos
        _cuit = cuit_representada or cuit
        _tipo = tipo_comprobante or tipo
        _pv = punto_venta
        _numero = numero_comprobante or numero

        if not all([_cuit, _tipo is not None, _pv is not None, _numero is not None]):
            raise ValueError("Se requieren: cuit, tipo, punto_venta, numero")

        _cuit = self._validar_cuit(_cuit)
        _tipo = int(_tipo)
        _pv = int(_pv)
        _numero = int(_numero)

        # Determinar si la llamada vino con estilo 2 (keyword cuit_representada)
        keyword_style = cuit_representada is not None

        try:
            token, sign = self.autenticar_wsaa(_cuit)

            soap_body = f"""
    <ser:consultarComprobanteRequest>
        <authRequest>
            <token>{token}</token>
            <sign>{sign}</sign>
            <cuitRepresentada>{_cuit}</cuitRepresentada>
        </authRequest>
        <consultaComprobanteRequest>
            <codigoTipoComprobante>{_tipo}</codigoTipoComprobante>
            <numeroPuntoVenta>{_pv}</numeroPuntoVenta>
            <numeroComprobante>{_numero}</numeroComprobante>
        </consultaComprobanteRequest>
    </ser:consultarComprobanteRequest>"""

            xml_response = self._wsmtxca_request(soap_body)

            # Parsear respuesta XML
            root = ET.fromstring(xml_response)
            campos = {}
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem.text and elem.text.strip():
                    campos[tag] = elem.text.strip()

            # Detectar errores AFIP
            if 'codigoDescripcion' in str(xml_response).lower():
                for elem in root.iter():
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag == 'codigo' and elem.text:
                        error_code = elem.text.strip()
                        if error_code in ['602', '603', '1502']:
                            # Comprobante no existe
                            if keyword_style:
                                return None
                            return {'status': 'no_encontrado', 'datos': {}, 'items': []}

            # Verificar que hay datos del comprobante
            has_data = any(k in campos for k in [
                'numeroComprobante', 'codigoTipoComprobante',
                'fechaEmision', 'importeTotal'
            ])

            if not has_data:
                if keyword_style:
                    return None
                return {'status': 'no_encontrado', 'datos': {}, 'items': []}

            # Extraer items
            items = self._extraer_items(root)

            datos = {
                'tipo_comprobante': campos.get('codigoTipoComprobante', str(_tipo)),
                'punto_venta': campos.get('numeroPuntoVenta', str(_pv)),
                'numero_comprobante': campos.get('numeroComprobante', str(_numero)),
                'fecha_emision': campos.get('fechaEmision', ''),
                'importe_total': campos.get('importeTotal', '0'),
                'importe_gravado': campos.get('importeGravado',
                                    campos.get('importeSubtotal', '0')),
                'importe_iva': campos.get('importeOtrosTributos',
                                campos.get('importeGravado', '0')),
                'receptor_denominacion': campos.get('denominacionReceptor',
                                          campos.get('razonSocial', '')),
                'receptor_numero_doc': campos.get('numeroDocumento', ''),
                'cae': campos.get('CAE', campos.get('cae', '')),
                'fecha_vencimiento_cae': campos.get('fechaVencimientoCAE',
                                          campos.get('CAEFchVto', '')),
                'moneda': campos.get('codigoMoneda', 'PES'),
                'cotizacion': campos.get('cotizacionMoneda', '1'),
                'cantidad_items': len(items)
            }

            if keyword_style:
                # Estilo 2: retornar dict plano con datos + items
                result = dict(datos)
                result['items'] = items
                return result
            else:
                # Estilo 1: retornar estructura con status
                return {
                    'status': 'encontrado',
                    'datos': datos,
                    'items': items
                }

        except Exception as e:
            error_str = str(e)
            if '602' in error_str or '603' in error_str or '1502' in error_str:
                if keyword_style:
                    return None
                return {'status': 'no_encontrado', 'datos': {}, 'items': []}
            raise

    def _extraer_items(self, root):
        """Extraer items/detalle de la respuesta XML"""
        items = []

        # Buscar nodos de items en la respuesta
        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag

            if tag in ['item', 'arrayItems']:
                item_data = {}
                for child in elem:
                    child_tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if child.text and child.text.strip():
                        item_data[child_tag] = child.text.strip()

                if item_data:
                    item = {
                        'codigo_mtx': item_data.get('codigoMTX', item_data.get('codigo', '')),
                        'codigo': item_data.get('codigo', ''),
                        'descripcion': item_data.get('descripcion', ''),
                        'cantidad': item_data.get('cantidad', '0'),
                        'unidad_medida': item_data.get('codigoUnidadMedida', ''),
                        'precio_unitario': item_data.get('precioUnitario', '0'),
                        'importe_total': item_data.get('importeItem',
                                          item_data.get('importeTotal', '0')),
                        'iva_alicuota': item_data.get('codigoCondicionIVA',
                                         item_data.get('importeIVA', '')),
                    }
                    items.append(item)

        return items

    # ------------------------------------------------------------------
    # Consultas múltiples
    # ------------------------------------------------------------------

    def consultar_multiples_comprobantes(self, cuit, comprobantes):
        """Consultar múltiples comprobantes en lote.

        Args:
            cuit: CUIT representada
            comprobantes: lista de dicts {'tipo': int, 'punto_venta': int, 'numero': int}

        Returns:
            lista de dicts {'comprobante': {...}, 'success': bool, 'datos': dict|None, 'error': str|None}
        """
        resultados = []
        for cbte in comprobantes:
            try:
                resultado = self.consultar_comprobante(
                    cuit_representada=cuit,
                    tipo_comprobante=cbte['tipo'],
                    punto_venta=cbte['punto_venta'],
                    numero_comprobante=cbte['numero']
                )
                resultados.append({
                    'comprobante': cbte,
                    'success': True,
                    'datos': resultado,
                    'error': None
                })
            except Exception as e:
                resultados.append({
                    'comprobante': cbte,
                    'success': False,
                    'datos': None,
                    'error': str(e)
                })
        return resultados

    # ------------------------------------------------------------------
    # Exportación
    # ------------------------------------------------------------------

    def exportar_comprobante(self, datos, formato='json'):
        """Exportar datos de comprobante a archivo.

        Args:
            datos: dict con datos del comprobante
            formato: 'json' o 'csv'

        Returns:
            path al archivo generado
        """
        facturas_dir = Path(self.cert_path).parent.parent / 'facturas'
        facturas_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        tipo = datos.get('tipo_comprobante', datos.get('codigoTipoComprobante', 'X'))
        pv = datos.get('punto_venta', datos.get('numeroPuntoVenta', '0'))
        num = datos.get('numero_comprobante', datos.get('numeroComprobante', '0'))

        base_name = f"wsmtxca_{tipo}_{pv}_{num}_{timestamp}"

        if formato == 'json':
            file_path = facturas_dir / f"{base_name}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=2)
        elif formato == 'csv':
            import csv
            file_path = facturas_dir / f"{base_name}.csv"
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Datos principales
                flat = {k: v for k, v in datos.items() if not isinstance(v, (list, dict))}
                writer.writerow(flat.keys())
                writer.writerow(flat.values())
        else:
            raise ValueError(f"Formato no soportado: {formato}")

        return str(file_path)


def crear_cliente_wsmtxca(ambiente='prod'):
    """Factory: crear un WSMTXCAClient auto-detectando certificados.

    Busca certs/ relativo al directorio de trabajo o al directorio de este archivo.
    """
    # Auto-detectar certificados
    if os.path.basename(os.getcwd()) == 'src':
        base_dir = Path(os.getcwd()).parent
    else:
        base_dir = Path(os.getcwd())

    cert_path = base_dir / 'certs' / 'certificado.crt'
    key_path = base_dir / 'certs' / 'clave_privada.key'

    if not cert_path.exists():
        # Intentar relativo al archivo
        base_dir = Path(__file__).parent
        cert_path = base_dir / 'certs' / 'certificado.crt'
        key_path = base_dir / 'certs' / 'clave_privada.key'

    if not cert_path.exists():
        raise FileNotFoundError(
            f"Certificado no encontrado en {cert_path}. "
            "Copiar certificado.crt y clave_privada.key a la carpeta certs/"
        )

    return WSMTXCAClient(str(cert_path), str(key_path), ambiente=ambiente)


def consulta_rapida_wsmtxca(cuit, tipo, punto_venta, numero, ambiente='prod'):
    """Consulta rápida de un comprobante WSMTXCA (función de conveniencia)."""
    client = crear_cliente_wsmtxca(ambiente=ambiente)
    return client.consultar_comprobante(
        cuit_representada=cuit,
        tipo_comprobante=tipo,
        punto_venta=punto_venta,
        numero_comprobante=numero
    )
