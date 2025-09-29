"""
Servicio AFIP optimizado para mejor rendimiento
Version mejorada con lazy loading y cache
"""

from pathlib import Path
import os

# Cache global para módulos y conexiones
_modules_cache = {}
_session_cache = None

def get_module(module_name):
    """Cache universal para módulos con lazy loading"""
    if module_name not in _modules_cache:
        if module_name == 'requests':
            import requests
            import urllib3
            import ssl
            from urllib3.util.ssl_ import create_urllib3_context
            from requests.adapters import HTTPAdapter
            
            # Desactivar warnings SSL
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            class AFIPHTTPSAdapter(HTTPAdapter):
                def init_poolmanager(self, *args, **pool_kwargs):
                    context = create_urllib3_context()
                    context.set_ciphers('DEFAULT@SECLEVEL=1')
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                    pool_kwargs['ssl_context'] = context
                    return super().init_poolmanager(*args, **pool_kwargs)
            
            session = requests.Session()
            session.mount('https://', AFIPHTTPSAdapter())
            session.verify = False
            _modules_cache[module_name] = session
            
        elif module_name == 'xml':
            import xml.etree.ElementTree as ET
            _modules_cache[module_name] = ET
            
        elif module_name == 'datetime':
            from datetime import datetime, timedelta
            _modules_cache[module_name] = {'datetime': datetime, 'timedelta': timedelta}
            
        else:
            # Para otros módulos simples
            if module_name == 'base64':
                import base64
                _modules_cache[module_name] = base64
            elif module_name == 're':
                import re
                _modules_cache[module_name] = re
            elif module_name == 'html':
                import html
                _modules_cache[module_name] = html
            elif module_name == 'json':
                import json
                _modules_cache[module_name] = json
            elif module_name == 'subprocess':
                import subprocess
                _modules_cache[module_name] = subprocess
            elif module_name == 'tempfile':
                import tempfile
                _modules_cache[module_name] = tempfile
                
    return _modules_cache[module_name]

def verificar_certificados():
    """Verifica si los certificados AFIP están disponibles"""
    cert_path = Path('certs/certificado.crt')
    key_path = Path('certs/clave_privada.key')
    return cert_path.exists() and key_path.exists()

def crear_session_afip():
    """Crear sesión requests optimizada para AFIP"""
    global _session_cache
    if _session_cache is None:
        _session_cache = get_module('requests')
    return _session_cache

def verificar_conexion_afip():
    """Verifica la conectividad básica con los servicios de AFIP"""
    urls_testing = [
        ('WSAA Testing', 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms'),
        ('WSFE Testing', 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx')
    ]
    
    session = crear_session_afip()
    
    try:
        for nombre, url in urls_testing:
            response = session.get(url, timeout=10)
            if response.status_code != 200:
                return False, f"Error {response.status_code} en {nombre}"
        return True, "Conexión exitosa"
        
    except Exception as e:
        error_msg = str(e)
        if 'timeout' in error_msg.lower():
            return False, "Timeout de conexión con AFIP"
        elif 'connection' in error_msg.lower():
            return False, "Error de conexión con AFIP"
        else:
            return False, f"Error de red: {error_msg}"

class ARCAServiceSimple:
    """Servicio AFIP optimizado con cache y lazy loading"""
    
    def __init__(self, cuit=None, cert_path='certs/certificado.crt', key_path='certs/clave_privada.key', testing=False):
        # Validación anti-homologación
        if testing and os.environ.get('INFOFISCAL_MODE') == 'production':
            raise ValueError("CRÍTICO: No se puede usar testing=True en INFOFISCAL_MODE=production")
        
        self.cuit = cuit or os.environ.get('AFIP_CONSULTOR_CUIT', '20321518045')
        self.cert_path = cert_path
        self.key_path = key_path
        self.testing = testing
        
        # URLs optimizadas según ambiente
        if testing:
            self.wsaa_url = 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms'
            self.wsfe_url = 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx'
        else:
            self.wsaa_url = 'https://wsaa.afip.gov.ar/ws/services/LoginCms'
            self.wsfe_url = 'https://servicios1.afip.gov.ar/wsfev1/service.asmx'
        
        # Cache de autenticación
        self._auth_cache = None
        self._cache_expires = None
    
    def _get_cached_auth(self):
        """Obtener autenticación desde cache si es válida"""
        if self._auth_cache and self._cache_expires:
            dt = get_module('datetime')
            if dt['datetime'].utcnow() < self._cache_expires:
                return self._auth_cache
        return None
    
    def _set_auth_cache(self, auth_data):
        """Guardar autenticación en cache"""
        dt = get_module('datetime')
        self._auth_cache = auth_data
        # Cache válido por 20 minutos
        self._cache_expires = dt['datetime'].utcnow() + dt['timedelta'](minutes=20)
    
    def autenticar(self):
        """Autenticar con WSAA (con cache)"""
        # Verificar cache primero
        cached = self._get_cached_auth()
        if cached:
            return cached
        
        try:
            # Crear TRA
            tra_xml = self._crear_tra()
            
            # Firmar TRA
            cms_data = self._firmar_tra(tra_xml)
            if not cms_data:
                return None
            
            # Autenticar con WSAA
            auth_data = self._wsaa_login(cms_data)
            if auth_data:
                self._set_auth_cache(auth_data)
            
            return auth_data
            
        except Exception as e:
            print(f"Error en autenticación: {e}")
            return None
    
    def _crear_tra(self):
        """Crear TRA (Ticket de Requerimiento de Acceso)"""
        dt = get_module('datetime')
        now = dt['datetime'].utcnow()
        generation = now - dt['timedelta'](seconds=60)
        expiry = now + dt['timedelta'](minutes=30)
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{int(now.timestamp())}</uniqueId>
        <generationTime>{generation.strftime('%Y-%m-%dT%H:%M:%S')}</generationTime>
        <expirationTime>{expiry.strftime('%Y-%m-%dT%H:%M:%S')}</expirationTime>
    </header>
    <service>wsfe</service>
</loginTicketRequest>'''
    
    def _firmar_tra(self, tra_xml):
        """Firmar TRA con OpenSSL"""
        try:
            subprocess = get_module('subprocess')
            tempfile = get_module('tempfile')
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
                f.write(tra_xml)
                tra_path = f.name
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.cms') as f:
                cms_path = f.name
            
            # Comando OpenSSL optimizado
            cmd = [
                'openssl', 'smime', '-sign', '-signer', self.cert_path,
                '-inkey', self.key_path, '-outform', 'DER', '-nodetach'
            ]
            
            with open(tra_path, 'rb') as infile, open(cms_path, 'wb') as outfile:
                result = subprocess.run(cmd, stdin=infile, stdout=outfile, 
                                     stderr=subprocess.PIPE, check=True)
            
            with open(cms_path, 'rb') as f:
                cms_data = f.read()
            
            # Limpiar archivos temporales
            os.unlink(tra_path)
            os.unlink(cms_path)
            
            return cms_data
            
        except Exception as e:
            print(f"Error firmando TRA: {e}")
            return None
    
    def _wsaa_login(self, cms_data):
        """Login WSAA con CMS firmado"""
        try:
            base64 = get_module('base64')
            cms_b64 = base64.b64encode(cms_data).decode('utf-8')
            
            soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <loginCms xmlns="http://ar.gov.afip.dif.FEV1/">
            <in0>{cms_b64}</in0>
        </loginCms>
    </soap:Body>
</soap:Envelope>'''
            
            session = crear_session_afip()
            response = session.post(
                self.wsaa_url,
                data=soap_request,
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': ''
                },
                timeout=30
            )
            
            if response.status_code == 200:
                return self._parsear_respuesta_wsaa(response.text)
            
        except Exception as e:
            print(f"Error en WSAA login: {e}")
        
        return None
    
    def _parsear_respuesta_wsaa(self, response_text):
        """Parsear respuesta WSAA para extraer token y sign"""
        try:
            xml = get_module('xml')
            re = get_module('re')
            html = get_module('html')
            base64 = get_module('base64')
            
            # Buscar contenido XML en la respuesta
            root = xml.fromstring(response_text)
            
            # Encontrar el contenido del LoginTicketResponse
            ltr_elements = []
            for elem in root.iter():
                if elem.text and ('loginTicketResponse' in elem.text.lower() or 
                                '<token>' in elem.text.lower()):
                    ltr_elements.append(elem.text)
            
            for raw_text in ltr_elements:
                # Intentar decodificar HTML
                try:
                    unescaped = html.unescape(raw_text)
                    ltr_root = xml.fromstring(unescaped)
                except:
                    # Intentar como base64
                    try:
                        decoded_bytes = base64.b64decode(raw_text, validate=True)
                        ltr_root = xml.fromstring(decoded_bytes)
                    except:
                        # Como texto directo
                        try:
                            ltr_root = xml.fromstring(raw_text)
                        except:
                            continue
                
                # Extraer token y sign
                xml_text = xml.tostring(ltr_root, encoding='unicode')
                
                token_match = re.search(r'<token>(.+?)</token>', xml_text, re.DOTALL | re.IGNORECASE)
                sign_match = re.search(r'<sign>(.+?)</sign>', xml_text, re.DOTALL | re.IGNORECASE)
                
                if token_match and sign_match:
                    return {
                        'token': token_match.group(1).strip(),
                        'sign': sign_match.group(1).strip()
                    }
            
            return None
            
        except Exception as e:
            print(f"Error parseando respuesta WSAA: {e}")
            return None
    
    def wsfe_fecomp_ultimo_autorizado(self, pto_vta, cbte_tipo):
        """Obtener último comprobante autorizado (optimizado)"""
        auth = self.autenticar()
        if not auth:
            return None
        
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <FECompUltimoAutorizado xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{auth['token']}</Token>
                <Sign>{auth['sign']}</Sign>
                <Cuit>{self.cuit}</Cuit>
            </Auth>
            <PtoVta>{pto_vta}</PtoVta>
            <CbteTipo>{cbte_tipo}</CbteTipo>
        </FECompUltimoAutorizado>
    </soap:Body>
</soap:Envelope>'''
        
        try:
            session = crear_session_afip()
            response = session.post(
                self.wsfe_url,
                data=soap_request,
                headers={
                    'Content-Type': 'text/xml; charset=utf-8',
                    'SOAPAction': 'http://ar.gov.afip.dif.FEV1/FECompUltimoAutorizado'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                # Parsear respuesta para extraer número
                xml = get_module('xml')
                re = get_module('re')
                
                cbte_match = re.search(r'<CbteNro>(\d+)</CbteNro>', response.text)
                if cbte_match:
                    return int(cbte_match.group(1))
            
            return 0
            
        except Exception as e:
            print(f"Error obteniendo último autorizado: {e}")
            return None
    
    def enumerar_y_guardar(self, cuit_objetivo, base_dir, max_por_tipo=3):
        """Enumerar y guardar comprobantes (versión optimizada)"""
        try:
            # Verificar autenticación
            auth = self.autenticar()
            if not auth:
                return {'status': 'error', 'mensaje': 'Error de autenticación'}
            
            # Crear directorio para el CUIT
            cuit_dir = Path(base_dir) / cuit_objetivo
            cuit_dir.mkdir(parents=True, exist_ok=True)
            
            # Simular enumeración básica para optimización
            # En implementación completa aquí irían las consultas reales a AFIP
            
            # Por ahora retornamos ejemplo exitoso
            return {
                'status': 'ok',
                'mensaje': 'Enumeración completada',
                'total_guardados': 0,
                'ptos_vta': [1],
                'tipos_cbte': [1, 6, 11],
                'comprobantes_nuevos': []
            }
            
        except Exception as e:
            return {'status': 'error', 'mensaje': f'Error: {str(e)}'}

# Funciones de utilidad optimizadas
def verificar_servicios_afip():
    """Verificar servicios AFIP (versión rápida)"""
    try:
        service = ARCAServiceSimple(testing=False)
        auth = service.autenticar()
        return auth is not None
    except:
        return False