#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente para WSFEv1 - Facturación Electrónica (incluye Monotributistas)
Autor: InfoFiscal
Fecha: 2025

WSFEv1: Para mercado interno - Facturas A, B, C, M (monotributo)
"""

import os
import sys
import ssl
import time
import html
import base64
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import requests
import subprocess
import urllib3
from requests.adapters import HTTPAdapter

# Configuración SSL más permisiva para AFIP
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WSFEv1Client:
    """Cliente para WSFEv1 (Factura Electrónica tradicional)"""

    def __init__(self, cert_path, key_path, ambiente='prod'):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ambiente = ambiente

        # URLs de AFIP
        self.urls = {
            'prod': {
                'wsaa': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
                'wsfe': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx'
            },
            'homo': {
                'wsaa': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
                'wsfe': 'https://wswhomo.afip.gob.ar/wsfev1/service.asmx'
            }
        }

        # Cache para tokens
        self._token_cache = {}

        # Configurar sesión con SSL permisivo (SECLEVEL=1 para AFIP)
        from src.ssl_afip_config import crear_session_afip
        self._session = crear_session_afip()

        # Tipos de comprobante WSFEv1
        self.tipos_comprobante = {
            1: "Factura A",
            2: "Nota de Débito A",
            3: "Nota de Crédito A",
            4: "Recibo A",
            5: "Nota de Venta al Contado A",
            6: "Factura B",
            7: "Nota de Débito B",
            8: "Nota de Crédito B",
            9: "Recibo B",
            10: "Nota de Venta al Contado B",
            11: "Factura C",
            12: "Nota de Débito C",
            13: "Nota de Crédito C",
            15: "Recibo C",
            51: "Factura M",
            52: "Nota de Débito M",
            53: "Nota de Crédito M"
        }

        print(f"Cliente WSFEv1 inicializado - Ambiente: {ambiente.upper()}")

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

    def _crear_tra(self):
        """Crear TRA para WSFEv1"""
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
<service>wsfe</service>
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

    def autenticar_wsaa(self, cuit_representada):
        """Autenticar con WSAA para WSFEv1"""
        cuit_clean = str(cuit_representada).replace('-', '').replace(' ', '')

        # Verificar cache
        cache_key = f"wsfe_{cuit_clean}_{self.ambiente}"
        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if cached['expires'] > datetime.now():
                return cached['token'], cached['sign']

        # Crear y firmar TRA
        tra_xml = self._crear_tra()
        signed_tra = self._firmar_tra(tra_xml)
        tra_b64 = base64.b64encode(signed_tra).decode('utf-8')

        # Request SOAP
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

        # Parsear respuesta
        root = ET.fromstring(response.text)
        login_return = None

        for elem in root.iter():
            if 'loginCmsReturn' in elem.tag:
                login_return = elem.text
                break

        if not login_return:
            raise Exception("loginCmsReturn no encontrado")

        # Decodificar credentials
        login_xml = html.unescape(login_return)
        login_root = ET.fromstring(login_xml)

        credentials = {}
        for child in login_root.iter():
            if child.tag in ['token', 'sign']:
                credentials[child.tag] = child.text

        if 'token' not in credentials or 'sign' not in credentials:
            raise Exception("Token/Sign no encontrados")

        # Cachear
        expires = datetime.now() + timedelta(hours=11, minutes=50)
        self._token_cache[cache_key] = {
            'token': credentials['token'],
            'sign': credentials['sign'],
            'expires': expires
        }

        return credentials['token'], credentials['sign']

    def _wsfe_request(self, method, params, token, sign, cuit):
        """Realizar request a WSFEv1"""

        # Construir parámetros Auth
        auth_params = f"""
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit}</Cuit>
        </Auth>"""

        # Construir SOAP según el método
        if method == 'FECompUltimoAutorizado':
            soap_body = f"""
            <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
                {auth_params}
                <PtoVta>{params['punto_venta']}</PtoVta>
                <CbteTipo>{params['tipo_comprobante']}</CbteTipo>
            </{method}>"""

        elif method == 'FECompConsultar':
            soap_body = f"""
            <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
                {auth_params}
                <FeCompConsReq>
                    <CbteTipo>{params['tipo_comprobante']}</CbteTipo>
                    <CbteNro>{params['numero']}</CbteNro>
                    <PtoVta>{params['punto_venta']}</PtoVta>
                </FeCompConsReq>
            </{method}>"""

        elif method == 'FEParamGetPtosVenta':
            soap_body = f"""
            <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
                {auth_params}
            </{method}>"""

        elif method == 'FEParamGetTiposCbte':
            soap_body = f"""
            <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
                {auth_params}
            </{method}>"""

        else:
            raise ValueError(f"Método no soportado: {method}")

        soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    {soap_body}
</soap:Body>
</soap:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': f'"http://ar.gov.afip.dif.FEV1/{method}"'
        }

        response = self._session.post(
            self.urls[self.ambiente]['wsfe'],
            data=soap_request,
            headers=headers,
            timeout=30
        )

        response.raise_for_status()
        return response.text

    def _fecha_comprobante(self, cuit, tipo, pv, num):
        """Obtener solo la fecha de un comprobante (para búsqueda binaria)."""
        try:
            comp = self.consultar_comprobante(cuit, tipo, pv, num)
            if comp:
                return comp.get('CbteFch') or comp.get('fecha_emision') or ''
        except Exception:
            pass
        return ''

    def buscar_rango_por_fecha(self, cuit, tipo, pv, ultimo, fecha_desde, fecha_hasta):
        """Búsqueda binaria para encontrar el rango de números que caen en [fecha_desde, fecha_hasta].

        Retorna (num_inicio, num_fin) o None si no hay comprobantes en el rango.
        Usa ~24 llamadas SOAP en vez de recorrer linealmente miles.
        """
        cuit = str(cuit).replace('-', '').replace(' ', '')

        # Buscar num_fin: último comprobante con fecha <= fecha_hasta
        lo, hi = 1, ultimo
        num_fin = 0
        while lo <= hi:
            mid = (lo + hi) // 2
            f = self._fecha_comprobante(cuit, tipo, pv, mid)
            if not f:
                hi = mid - 1
                continue
            if f <= fecha_hasta:
                num_fin = mid
                lo = mid + 1
            else:
                hi = mid - 1

        if num_fin == 0:
            return None

        # Buscar num_inicio: primer comprobante con fecha >= fecha_desde
        lo, hi = 1, num_fin
        num_inicio = None
        while lo <= hi:
            mid = (lo + hi) // 2
            f = self._fecha_comprobante(cuit, tipo, pv, mid)
            if not f:
                lo = mid + 1
                continue
            if f >= fecha_desde:
                num_inicio = mid
                hi = mid - 1
            else:
                lo = mid + 1

        if num_inicio is None:
            return None

        return (num_inicio, num_fin)

    def obtener_ultimo_comprobante(self, cuit, tipo_comprobante, punto_venta):
        """Obtener el último número de comprobante autorizado"""
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self.autenticar_wsaa(cuit)

            params = {
                'tipo_comprobante': tipo_comprobante,
                'punto_venta': punto_venta
            }

            xml_response = self._wsfe_request(
                'FECompUltimoAutorizado',
                params,
                token,
                sign,
                cuit
            )

            # Parsear respuesta
            root = ET.fromstring(xml_response)

            # Buscar el número
            for elem in root.iter():
                if 'CbteNro' in elem.tag:
                    return int(elem.text) if elem.text else 0

            return 0

        except Exception as e:
            print(f"Error obteniendo ultimo comprobante: {str(e)}")
            return None

    def consultar_comprobante(self, cuit, tipo_comprobante, punto_venta, numero):
        """Consultar un comprobante específico"""
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self.autenticar_wsaa(cuit)

            params = {
                'tipo_comprobante': tipo_comprobante,
                'punto_venta': punto_venta,
                'numero': numero
            }

            xml_response = self._wsfe_request(
                'FECompConsultar',
                params,
                token,
                sign,
                cuit
            )

            # Parsear respuesta
            root = ET.fromstring(xml_response)

            # Namespace helper: extrae tag sin namespace
            def _tag(elem):
                t = elem.tag
                return t.split('}')[-1] if '}' in t else t

            # ── Extraer campos escalares ─────────────────────────────
            comprobante = {}
            for elem in root.iter():
                tag = _tag(elem)
                if elem.text and elem.text.strip():
                    comprobante[tag] = elem.text.strip()

            if not comprobante or ('CbteNro' not in comprobante and 'Cbte' not in str(comprobante)):
                return None

            # ── Extraer array IVA (alícuotas) ────────────────────────
            iva_array = []
            for alic in root.iter():
                if _tag(alic) == 'AlicIva':
                    item = {}
                    for child in alic:
                        item[_tag(child)] = (child.text or '').strip()
                    if item:
                        iva_array.append(item)

            # ── Extraer array Tributos (IIBB, municipal, etc.) ───────
            tributos_array = []
            for trib in root.iter():
                if _tag(trib) == 'Tributo':
                    item = {}
                    for child in trib:
                        item[_tag(child)] = (child.text or '').strip()
                    if item:
                        tributos_array.append(item)

            resultado = {
                # Datos básicos
                'CbteTipo': comprobante.get('CbteTipo'),
                'CbteNro': comprobante.get('CbteNro'),
                'PtoVta': comprobante.get('PtoVta'),
                'CbteFch': comprobante.get('CbteFch'),
                'CAE': comprobante.get('CAE'),
                'CAEFchVto': comprobante.get('CAEFchVto'),

                # Importes totales
                'ImpTotal': comprobante.get('ImpTotal'),
                'ImpNeto': comprobante.get('ImpNeto'),
                'ImpIVA': comprobante.get('ImpIVA'),
                'ImpTrib': comprobante.get('ImpTrib'),
                'ImpOpEx': comprobante.get('ImpOpEx'),

                # Desglose impositivo
                'IvaDetalle': iva_array,       # [{Id, BaseImp, Importe}, ...]
                'TributosDetalle': tributos_array,  # [{Id, Desc, BaseImp, Alic, Importe}, ...]

                # Datos del receptor
                'DocTipo': comprobante.get('DocTipo'),
                'DocNro': comprobante.get('DocNro'),
                'Concepto': comprobante.get('Concepto'),

                # Moneda
                'MonId': comprobante.get('MonId'),
                'MonCotiz': comprobante.get('MonCotiz'),

                # Aliases para la UI
                'fecha_emision': comprobante.get('CbteFch'),
                'cae': comprobante.get('CAE'),
                'fecha_vto_cae': comprobante.get('CAEFchVto'),
                'importe_total': comprobante.get('ImpTotal'),
                'punto_venta': comprobante.get('PtoVta'),
                'numero': comprobante.get('CbteNro'),
                'receptor_tipo_doc': comprobante.get('DocTipo'),
                'receptor_nro_doc': comprobante.get('DocNro'),
                'concepto': comprobante.get('Concepto'),
                'moneda': comprobante.get('MonId'),
                'cotizacion': comprobante.get('MonCotiz'),
            }

            return resultado

        except Exception as e:
            print(f"Error consultando comprobante: {str(e)}")
            return None

    def buscar_comprobantes_rango(self, cuit, tipos_comprobante=None, puntos_venta=None, limite_por_tipo=50, fecha_desde=None, fecha_hasta=None):
        """Buscar comprobantes en un rango para encontrar los existentes.

        Args:
            fecha_desde: str YYYYMMDD — no traer comprobantes anteriores (early stop)
            fecha_hasta: str YYYYMMDD — no traer comprobantes posteriores
        """
        cuit = str(cuit).replace('-', '').replace(' ', '')

        if tipos_comprobante is None:
            tipos_comprobante = [11, 6, 1, 51, 2, 3]

        if puntos_venta is None:
            puntos_venta = [1, 2, 3, 4, 5]

        # Si hay filtro de fecha, no limitar por cantidad (traer todo el rango)
        if fecha_desde:
            limite_por_tipo = 999999

        resultados = []

        for tipo in tipos_comprobante:
            for pv in puntos_venta:
                # Obtener último número autorizado
                ultimo = self.obtener_ultimo_comprobante(cuit, tipo, pv)

                if ultimo and ultimo > 0:
                    # Consultar desde el último hacia atrás
                    inicio = max(1, ultimo - limite_por_tipo + 1)
                    encontrados_tipo = 0

                    for num in range(ultimo, inicio - 1, -1):
                        try:
                            comp = self.consultar_comprobante(cuit, tipo, pv, num)

                            if comp is not None:
                                fecha_cbte = comp.get('CbteFch') or comp.get('fecha_emision') or ''

                                # Early stop: si la fecha es anterior al desde, frenar
                                if fecha_desde and fecha_cbte < fecha_desde:
                                    break

                                # Filtrar: si la fecha es posterior al hasta, saltear
                                if fecha_hasta and fecha_cbte > fecha_hasta:
                                    continue

                                comp['consulta'] = {
                                    'cuit': cuit,
                                    'tipo': tipo,
                                    'tipo_descripcion': self.tipos_comprobante.get(tipo, f'Tipo {tipo}'),
                                    'punto_venta': pv,
                                    'numero': num,
                                    'numero_formateado': f"{pv:04d}-{num:08d}"
                                }
                                resultados.append(comp)
                                encontrados_tipo += 1

                            # Limitar consultas por tipo/PV (solo sin filtro de fecha)
                            if not fecha_desde and encontrados_tipo >= 10:
                                break

                        except Exception:
                            continue

        return resultados

    def obtener_puntos_venta(self, cuit):
        """Obtener puntos de venta usando FEParamGetPtosVenta"""
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self.autenticar_wsaa(cuit)

            xml_response = self._wsfe_request(
                'FEParamGetPtosVenta',
                {},
                token,
                sign,
                cuit
            )

            root = ET.fromstring(xml_response)
            puntos_venta = []

            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'Nro' and elem.text and elem.text.isdigit():
                    puntos_venta.append(int(elem.text))

            return sorted(set(puntos_venta))

        except Exception as e:
            print(f"Error obteniendo puntos de venta: {e}")
            return []

    def obtener_tipos_comprobante(self, cuit):
        """Obtener tipos de comprobante usando FEParamGetTiposCbte"""
        try:
            token, sign = self.autenticar_wsaa(cuit)

            xml_response = self._wsfe_request(
                'FEParamGetTiposCbte',
                {},
                token,
                sign,
                cuit
            )

            root = ET.fromstring(xml_response)
            tipos = []

            current_tipo = {}
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'Id' and elem.text and elem.text.isdigit():
                    current_tipo = {'id': int(elem.text)}
                elif tag == 'Desc' and elem.text and current_tipo:
                    current_tipo['descripcion'] = elem.text
                    tipos.append(current_tipo)
                    current_tipo = {}

            # Dedup
            tipos_unicos = {}
            for tipo in tipos:
                if tipo['id'] not in tipos_unicos:
                    tipos_unicos[tipo['id']] = tipo

            return sorted(tipos_unicos.values(), key=lambda x: x['id'])

        except Exception as e:
            print(f"Error obteniendo tipos de comprobante: {e}")
            return []
