#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente para WSFEv1 - Facturación Electrónica (incluye Monotributistas)
Autor: InfoFiscal
Fecha: 2025

WSFEv1: Para mercado interno - Facturas A, B, C, M (monotributo)
WSFEXv1: Solo para exportación - Facturas E
"""

import os
import sys
import time
import base64
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime, timedelta
import requests
import subprocess
import urllib3

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
        
        # Configurar sesión con SSL permisivo
        self._session = requests.Session()
        self._session.verify = False  # Desactivar verificación SSL estricta
        
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
        
        print(f"🔧 Cliente WSFEv1 inicializado - Ambiente: {ambiente.upper()}")
        print(f"📄 Certificado: {cert_path}")
        print(f"🔑 Clave: {key_path}")

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
            except:
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
                print(f"✅ Token WSFEv1 desde cache")
                return cached['token'], cached['sign']
        
        print(f"🔐 Autenticando WSAA para WSFEv1...")
        print(f"   CUIT: {cuit_clean}")
        print(f"   Ambiente: {self.ambiente}")
        
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
        
        print(f"   📊 WSAA Response: HTTP {response.status_code}")
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
        import html
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
        
        print(f"✅ Autenticación WSFEv1 exitosa")
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
            
        elif method == 'FEParamGetTiposDoc':
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
        
        # Configurar SSL con cipher más permisivo para AFIP
        import ssl
        import urllib3
        from requests.adapters import HTTPAdapter
        
        # Deshabilitar advertencias SSL
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # Crear sesión con configuración SSL personalizada
        session = requests.Session()
        
        class CustomHTTPAdapter(HTTPAdapter):
            def init_poolmanager(self, *args, **kwargs):
                ctx = ssl.create_default_context()
                ctx.set_ciphers('DEFAULT@SECLEVEL=1')
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kwargs['ssl_context'] = ctx
                return super().init_poolmanager(*args, **kwargs)
        
        session.mount('https://', CustomHTTPAdapter())
        
        response = session.post(
            self.urls[self.ambiente]['wsfe'],
            data=soap_request,
            headers=headers,
            timeout=30,
            verify=False
        )
        
        response.raise_for_status()
        return response.text

    def obtener_ultimo_comprobante(self, cuit, tipo_comprobante, punto_venta):
        """Obtener el último número de comprobante autorizado"""
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
            print(f"❌ Error obteniendo último comprobante: {str(e)}")
            return None

    def consultar_comprobante(self, cuit, tipo_comprobante, punto_venta, numero):
        """Consultar un comprobante específico"""
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
            
            print(f"🔍 XML Response (primeros 500 chars): {xml_response[:500]}...")
            
            # Parsear respuesta
            root = ET.fromstring(xml_response)
            
            # Extraer datos del comprobante - buscar todos los campos posibles
            comprobante = {}
            
            # Mapear todos los elementos encontrados
            for elem in root.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if elem.text and elem.text.strip():
                    comprobante[tag] = elem.text.strip()
            
            print(f"🔍 Elementos XML encontrados: {list(comprobante.keys())}")
            
            # Si encontramos datos, construir respuesta estructurada
            if comprobante and ('CbteNro' in comprobante or 'Cbte' in str(comprobante)):
                resultado = {
                    # Datos básicos
                    'CbteTipo': comprobante.get('CbteTipo'),
                    'CbteNro': comprobante.get('CbteNro'), 
                    'PtoVta': comprobante.get('PtoVta'),
                    'CbteFch': comprobante.get('CbteFch'),
                    'CAE': comprobante.get('CAE'),
                    'CAEFchVto': comprobante.get('CAEFchVto'),
                    
                    # Importes
                    'ImpTotal': comprobante.get('ImpTotal'),
                    'ImpNeto': comprobante.get('ImpNeto'),
                    'ImpIVA': comprobante.get('ImpIVA'),
                    'ImpTrib': comprobante.get('ImpTrib'),
                    'ImpOpEx': comprobante.get('ImpOpEx'),
                    
                    # Datos del receptor
                    'DocTipo': comprobante.get('DocTipo'),
                    'DocNro': comprobante.get('DocNro'),
                    'Concepto': comprobante.get('Concepto'),
                    
                    # Moneda
                    'MonId': comprobante.get('MonId'),
                    'MonCotiz': comprobante.get('MonCotiz'),
                    
                    # Campos con nombres alternativos
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
                    
                    # Campos adicionales encontrados
                    **{k: v for k, v in comprobante.items() if k not in [
                        'CbteTipo', 'CbteNro', 'PtoVta', 'CbteFch', 'CAE', 'CAEFchVto',
                        'ImpTotal', 'ImpNeto', 'ImpIVA', 'DocTipo', 'DocNro', 'Concepto',
                        'MonId', 'MonCotiz'
                    ]}
                }
                
                print(f"✅ Comprobante encontrado con {len(resultado)} campos")
                return resultado
            else:
                print(f"📭 Comprobante no encontrado o datos incompletos")
                return None
                
        except Exception as e:
            print(f"❌ Error consultando comprobante: {str(e)}")
            import traceback
            print(f"🔍 Traceback: {traceback.format_exc()}")
            return None

    def buscar_comprobantes_rango(self, cuit, tipos_comprobante=None, puntos_venta=None, limite_por_tipo=50):
        """Buscar comprobantes en un rango para encontrar los existentes"""
        
        if tipos_comprobante is None:
            # Incluir Factura C (11) y Factura B (6) que son los más comunes
            tipos_comprobante = [11, 6, 1, 51, 2, 3]  
        
        if puntos_venta is None:
            puntos_venta = [1, 2, 3, 4, 5]  # Incluir más puntos de venta
        
        resultados = []
        
        print(f"🔍 Buscando comprobantes WSFEv1...")
        print(f"   CUIT: {cuit}")
        print(f"   Tipos: {tipos_comprobante}")
        print(f"   Puntos de venta: {puntos_venta}")
        print(f"   Límite por tipo: {limite_por_tipo}")
        
        for tipo in tipos_comprobante:
            for pv in puntos_venta:
                print(f"   📋 Tipo {tipo} ({self.tipos_comprobante.get(tipo, 'Desconocido')}) PV{pv:04d}...")
                
                # Obtener último número autorizado
                ultimo = self.obtener_ultimo_comprobante(cuit, tipo, pv)
                
                if ultimo and ultimo > 0:
                    print(f"      ✅ Último autorizado: {ultimo}")
                    
                    # Consultar desde el último hacia atrás
                    inicio = max(1, ultimo - limite_por_tipo + 1)
                    encontrados_tipo = 0
                    
                    for num in range(ultimo, inicio - 1, -1):
                        try:
                            comp = self.consultar_comprobante(cuit, tipo, pv, num)
                            
                            # FIX CRÍTICO: Cambiar la validación
                            if comp is not None:  # ✅ CORRECTO: verificar si no es None
                                # Agregar información de la consulta
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
                                
                                print(f"         ✓ {pv:04d}-{num:08d}: CAE {comp.get('CAE', comp.get('cae', 'N/A'))}")
                            
                            # Limitar consultas por tipo/PV
                            if encontrados_tipo >= 10:
                                print(f"         (Limitado a 10 comprobantes por tipo/PV)")
                                break
                                
                        except Exception as e:
                            print(f"         ✗ Error consultando {pv:04d}-{num:08d}: {str(e)}")
                            continue
                            
                    if encontrados_tipo == 0:
                        print(f"      📭 No se encontraron comprobantes")
                else:
                    print(f"      📭 No hay comprobantes autorizados o error al consultar")
        
        print(f"\n✅ Búsqueda completada: {len(resultados)} comprobantes encontrados")
        return resultados
    
    def obtener_puntos_venta(self, cuit):
        """Obtener puntos de venta usando FEParamGetPtosVenta"""
        try:
            token, sign = self.autenticar_wsaa(cuit)
            
            # SOAP request para FEParamGetPtosVenta
            soap_body = f"""
            <FEParamGetPtosVenta xmlns="http://ar.gov.afip.dif.FEV1/">
                <Auth>
                    <Token>{token}</Token>
                    <Sign>{sign}</Sign>
                    <Cuit>{cuit}</Cuit>
                </Auth>
            </FEParamGetPtosVenta>"""
            
            soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    {soap_body}
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://ar.gov.afip.dif.FEV1/FEParamGetPtosVenta'
            }
            
            response = self._session.post(
                self.urls[self.ambiente]['wsfe'],
                data=soap_envelope,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Error HTTP {response.status_code}")
            
            # Parse response
            root = ET.fromstring(response.text)
            puntos_venta = []
            
            for elem in root.iter():
                if 'PtoVenta' in elem.tag and elem.text:
                    # Buscar elementos hermanos para obtener más info
                    parent = elem.getparent()
                    if parent is not None:
                        punto_info = {'numero': int(elem.text)}
                        
                        # Buscar descripción si existe
                        for sibling in parent:
                            tag_name = sibling.tag.split('}')[-1] if '}' in sibling.tag else sibling.tag
                            if 'Desc' in tag_name and sibling.text:
                                punto_info['descripcion'] = sibling.text
                            elif 'EmisionTipo' in tag_name and sibling.text:
                                punto_info['tipo_emision'] = sibling.text
                        
                        puntos_venta.append(punto_info)
            
            # Remover duplicados y ordenar
            puntos_unicos = {}
            for punto in puntos_venta:
                numero = punto['numero']
                if numero not in puntos_unicos:
                    puntos_unicos[numero] = punto
            
            resultado = sorted(puntos_unicos.values(), key=lambda x: x['numero'])
            return resultado
            
        except Exception as e:
            print(f"❌ Error obteniendo puntos de venta: {e}")
            return []
    
    def obtener_tipos_comprobante(self, cuit):
        """Obtener tipos de comprobante usando FEParamGetTiposCbte"""
        try:
            token, sign = self.autenticar_wsaa(cuit)
            
            # SOAP request para FEParamGetTiposCbte
            soap_body = f"""
            <FEParamGetTiposCbte xmlns="http://ar.gov.afip.dif.FEV1/">
                <Auth>
                    <Token>{token}</Token>
                    <Sign>{sign}</Sign>
                    <Cuit>{cuit}</Cuit>
                </Auth>
            </FEParamGetTiposCbte>"""
            
            soap_envelope = f"""<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
                <soap:Body>
                    {soap_body}
                </soap:Body>
            </soap:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'http://ar.gov.afip.dif.FEV1/FEParamGetTiposCbte'
            }
            
            response = self._session.post(
                self.urls[self.ambiente]['wsfe'],
                data=soap_envelope,
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"Error HTTP {response.status_code}")
            
            # Parse response
            root = ET.fromstring(response.text)
            tipos = []
            
            # Buscar elementos CbteTipo
            for elem in root.iter():
                tag_name = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                if tag_name == 'Id' and elem.text and elem.text.isdigit():
                    # Buscar el elemento padre que contiene toda la info del tipo
                    parent = elem.getparent()
                    if parent is not None:
                        tipo_info = {'id': int(elem.text)}
                        
                        # Buscar descripción
                        for sibling in parent:
                            sibling_tag = sibling.tag.split('}')[-1] if '}' in sibling.tag else sibling.tag
                            if sibling_tag == 'Desc' and sibling.text:
                                tipo_info['descripcion'] = sibling.text
                            elif sibling_tag == 'FchDesde' and sibling.text:
                                tipo_info['fecha_desde'] = sibling.text
                            elif sibling_tag == 'FchHasta' and sibling.text:
                                tipo_info['fecha_hasta'] = sibling.text
                        
                        if 'descripcion' in tipo_info:  # Solo agregar si tiene descripción
                            tipos.append(tipo_info)
            
            # Remover duplicados y ordenar
            tipos_unicos = {}
            for tipo in tipos:
                tipo_id = tipo['id']
                if tipo_id not in tipos_unicos:
                    tipos_unicos[tipo_id] = tipo
            
            resultado = sorted(tipos_unicos.values(), key=lambda x: x['id'])
            return resultado
            
        except Exception as e:
            print(f"❌ Error obteniendo tipos de comprobante: {e}")
            return []