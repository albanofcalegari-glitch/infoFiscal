#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente para WSFEXv1 - Facturación Electrónica de Exportación
Autor: InfoFiscal
Fecha: 2025

WSFEXv1: Para operaciones de exportación - Facturas E (tipo 19, 20, 21)
También consulta facturas de monotributo cuando están registradas aquí.
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

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WSFEXv1Client:
    """Cliente para WSFEXv1 (Factura Electrónica de Exportación)"""

    def __init__(self, cert_path, key_path, ambiente='prod'):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ambiente = ambiente

        # URLs de AFIP
        self.urls = {
            'prod': {
                'wsaa': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
                'wsfex': 'https://servicios1.afip.gov.ar/wsfexv1/service.asmx'
            },
            'homo': {
                'wsaa': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
                'wsfex': 'https://wswhomo.afip.gob.ar/wsfexv1/service.asmx'
            }
        }

        # Cache para tokens
        self._token_cache = {}

        # Sesión HTTP con SSL permisivo (SECLEVEL=1 para AFIP)
        from src.ssl_afip_config import crear_session_afip
        self._session = crear_session_afip()

        # Tipos de comprobante WSFEXv1
        self.tipos_comprobante = {
            19: "Factura de Exportación E",
            20: "Nota de Débito de Exportación E",
            21: "Nota de Crédito de Exportación E",
        }

        print(f"Cliente WSFEXv1 inicializado - Ambiente: {ambiente.upper()}")

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

    def _crear_tra(self):
        """Crear TRA para WSFEXv1"""
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
<service>wsfex</service>
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

    def _obtener_token_wsaa(self):
        """Obtener token WSAA (con cache)."""
        cache_key = f"wsfex_{self.ambiente}"
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
    # Requests WSFEXv1
    # ------------------------------------------------------------------

    def _wsfex_request(self, method, soap_body):
        """Enviar request SOAP a WSFEXv1"""
        soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    {soap_body}
</soap:Body>
</soap:Envelope>"""

        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': f'"http://ar.gov.afip.dif.fexv1/{method}"'
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
            self.urls[self.ambiente]['wsfex'],
            data=soap_envelope,
            headers=headers,
            timeout=30,
            verify=False
        )

        response.raise_for_status()
        return response.text

    # ------------------------------------------------------------------
    # Operaciones
    # ------------------------------------------------------------------

    def consultar_comprobante(self, cuit, tipo_comprobante, punto_venta, numero):
        """Consultar un comprobante específico en WSFEXv1.

        Retorna dict con datos del comprobante, o None si no existe.
        """
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self._obtener_token_wsaa()
            cuit_clean = str(cuit).replace('-', '').replace(' ', '')

            soap_body = f"""
    <FEXGetCMP xmlns="http://ar.gov.afip.dif.fexv1/">
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit_clean}</Cuit>
        </Auth>
        <Cmp>
            <Cbte_tipo>{tipo_comprobante}</Cbte_tipo>
            <Punto_vta>{punto_venta}</Punto_vta>
            <Cbte_nro>{numero}</Cbte_nro>
        </Cmp>
    </FEXGetCMP>"""

            xml_response = self._wsfex_request('FEXGetCMP', soap_body)

            root = ET.fromstring(xml_response)
            campos = {}
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem.text and elem.text.strip():
                    campos[tag] = elem.text.strip()

            # Verificar errores
            err_code = campos.get('ErrCode', '')
            if err_code and err_code != '0':
                return None

            # Verificar que hay datos
            has_data = any(k in campos for k in [
                'Cbte_nro', 'Fecha_cbte', 'Imp_total', 'Cae'
            ])
            if not has_data:
                return None

            return {
                'tipo_comprobante': campos.get('Cbte_tipo', str(tipo_comprobante)),
                'descripcion_tipo': self.tipos_comprobante.get(
                    int(campos.get('Cbte_tipo', tipo_comprobante)),
                    f'Tipo {tipo_comprobante}'
                ),
                'punto_venta': campos.get('Punto_vta', str(punto_venta)),
                'numero': campos.get('Cbte_nro', str(numero)),
                'fecha_emision': campos.get('Fecha_cbte', ''),
                'importe_total': campos.get('Imp_total', '0'),
                'moneda': campos.get('Mon_id', ''),
                'cotizacion': campos.get('Mon_cotiz', '1'),
                'cae': campos.get('Cae', ''),
                'fecha_vto_cae': campos.get('Fch_venc_Cae', ''),
                'pais_destino': campos.get('Dst_cmp', ''),
                'id_impositivo_receptor': campos.get('Cuit_pais_cliente', ''),
                'denominacion_receptor': campos.get('Cliente', ''),
                'incoterms': campos.get('Incoterms', ''),
                'idioma': campos.get('Idioma_cbte', ''),
                'observaciones': campos.get('Obs', ''),
                # Campos extra
                **{k: v for k, v in campos.items() if k not in [
                    'Cbte_tipo', 'Punto_vta', 'Cbte_nro', 'Fecha_cbte',
                    'Imp_total', 'Mon_id', 'Mon_cotiz', 'Cae', 'Fch_venc_Cae',
                    'Dst_cmp', 'Cuit_pais_cliente', 'Cliente', 'Incoterms',
                    'Idioma_cbte', 'Obs', 'Token', 'Sign', 'Cuit',
                    'ErrCode', 'ErrMsg'
                ]}
            }

        except Exception as e:
            print(f"Error consultando comprobante WSFEXv1: {e}")
            return None

    def obtener_ultimo_autorizado(self, cuit, punto_venta, tipo_comprobante):
        """Obtener el último comprobante autorizado."""
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self._obtener_token_wsaa()
            cuit_clean = str(cuit).replace('-', '').replace(' ', '')

            soap_body = f"""
    <FEXGetLast_CMP xmlns="http://ar.gov.afip.dif.fexv1/">
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit_clean}</Cuit>
        </Auth>
        <Pto_venta>{punto_venta}</Pto_venta>
        <Cbte_Tipo>{tipo_comprobante}</Cbte_Tipo>
    </FEXGetLast_CMP>"""

            xml_response = self._wsfex_request('FEXGetLast_CMP', soap_body)

            root = ET.fromstring(xml_response)
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'Cbte_nro' and elem.text:
                    return int(elem.text)

            return 0

        except Exception as e:
            print(f"Error obteniendo ultimo autorizado WSFEXv1: {e}")
            return 0

    def obtener_puntos_venta(self, cuit):
        """Obtener puntos de venta habilitados."""
        cuit = str(cuit).replace('-', '').replace(' ', '')
        try:
            token, sign = self._obtener_token_wsaa()
            cuit_clean = str(cuit).replace('-', '').replace(' ', '')

            soap_body = f"""
    <FEXGetPARAM_PtoVenta xmlns="http://ar.gov.afip.dif.fexv1/">
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit_clean}</Cuit>
        </Auth>
    </FEXGetPARAM_PtoVenta>"""

            xml_response = self._wsfex_request('FEXGetPARAM_PtoVenta', soap_body)

            root = ET.fromstring(xml_response)
            puntos = []
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'Pto_venta' and elem.text and elem.text.isdigit():
                    puntos.append(int(elem.text))

            return sorted(set(puntos))

        except Exception as e:
            print(f"Error obteniendo puntos de venta WSFEXv1: {e}")
            return []

    def obtener_tipos_comprobante(self, cuit):
        """Obtener tipos de comprobante disponibles."""
        try:
            token, sign = self._obtener_token_wsaa()
            cuit_clean = str(cuit).replace('-', '').replace(' ', '')

            soap_body = f"""
    <FEXGetPARAM_Cbte_Tipo xmlns="http://ar.gov.afip.dif.fexv1/">
        <Auth>
            <Token>{token}</Token>
            <Sign>{sign}</Sign>
            <Cuit>{cuit_clean}</Cuit>
        </Auth>
    </FEXGetPARAM_Cbte_Tipo>"""

            xml_response = self._wsfex_request('FEXGetPARAM_Cbte_Tipo', soap_body)

            root = ET.fromstring(xml_response)
            tipos = []
            current = {}
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag == 'Cbte_Id' and elem.text:
                    current = {'id': int(elem.text)}
                elif tag == 'Cbte_Ds' and elem.text and current:
                    current['descripcion'] = elem.text
                    tipos.append(current)
                    current = {}

            # Dedup
            tipos_unicos = {}
            for t in tipos:
                if t['id'] not in tipos_unicos:
                    tipos_unicos[t['id']] = t

            return sorted(tipos_unicos.values(), key=lambda x: x['id'])

        except Exception as e:
            print(f"Error obteniendo tipos de comprobante WSFEXv1: {e}")
            return []

    def buscar_comprobantes_rango(self, cuit, tipos_comprobante=None, puntos_venta=None, limite_por_tipo=10, fecha_desde=None, fecha_hasta=None):
        """Buscar comprobantes en un rango (compatible con interfaz WSFEv1Client).

        Args:
            fecha_desde: str YYYYMMDD — no traer comprobantes anteriores (early stop)
            fecha_hasta: str YYYYMMDD — no traer comprobantes posteriores
        """
        cuit = str(cuit).replace('-', '').replace(' ', '')

        if tipos_comprobante is None:
            tipos_comprobante = [19, 20, 21]

        if puntos_venta is None:
            puntos_venta = [1, 2, 3, 4, 5]

        if fecha_desde:
            limite_por_tipo = 999999

        resultados = []

        for tipo in tipos_comprobante:
            for pv in puntos_venta:
                ultimo = self.obtener_ultimo_autorizado(cuit, pv, tipo)

                if ultimo and ultimo > 0:
                    inicio = max(1, ultimo - limite_por_tipo + 1)

                    for num in range(ultimo, inicio - 1, -1):
                        try:
                            comp = self.consultar_comprobante(cuit, tipo, pv, num)
                            if comp is not None:
                                fecha_cbte = comp.get('CbteFch') or comp.get('fecha_emision') or ''

                                if fecha_desde and fecha_cbte < fecha_desde:
                                    break

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
                        except Exception:
                            continue

        return resultados

    def buscar_facturas_monotributo(self, cuit, max_por_punto=5):
        """Buscar facturas de monotributo (tipos 51, 52, 53) en WSFEXv1."""
        tipos_mono = [51, 52, 53]
        resultados = []

        puntos = self.obtener_puntos_venta(cuit)
        if not puntos:
            puntos = [1, 2, 3, 4, 5]

        for pv in puntos:
            for tipo in tipos_mono:
                ultimo = self.obtener_ultimo_autorizado(cuit, pv, tipo)
                if ultimo and ultimo > 0:
                    inicio = max(1, ultimo - max_por_punto + 1)
                    for num in range(ultimo, inicio - 1, -1):
                        comp = self.consultar_comprobante(cuit, tipo, pv, num)
                        if comp:
                            resultados.append(comp)

        return resultados


def crear_cliente_wsfexv1(ambiente='prod'):
    """Factory: crear un WSFEXv1Client auto-detectando certificados."""
    if os.path.basename(os.getcwd()) == 'src':
        base_dir = Path(os.getcwd()).parent
    else:
        base_dir = Path(os.getcwd())

    cert_path = base_dir / 'certs' / 'certificado.crt'
    key_path = base_dir / 'certs' / 'clave_privada.key'

    if not cert_path.exists():
        base_dir = Path(__file__).parent
        cert_path = base_dir / 'certs' / 'certificado.crt'
        key_path = base_dir / 'certs' / 'clave_privada.key'

    if not cert_path.exists():
        raise FileNotFoundError(
            f"Certificado no encontrado en {cert_path}. "
            "Copiar certificado.crt y clave_privada.key a la carpeta certs/"
        )

    return WSFEXv1Client(str(cert_path), str(key_path), ambiente=ambiente)
