"""
Alternativa simple a afip_extract_by_date.py sin dependencias complejas.
Usa solo requests y xml.etree para evitar problemas con lxml/zeep.
"""

import os
import json
import csv
import base64
import subprocess
import tempfile
import uuid
import time
import requests
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import requests
import xml.etree.ElementTree as ET


def build_simple_tra(service='wsfe'):
    """Construir TRA según especificaciones exactas de AFIP"""
    now = datetime.now()
    gen_time = now - timedelta(minutes=10)
    exp_time = now + timedelta(hours=12)
    
    # Usar timestamp como unique_id (más simple y confiable)
    unique_id = int(time.time())
    
    # Formato ISO con zona horaria Argentina
    gen_time_str = gen_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '-03:00'
    exp_time_str = exp_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + '-03:00'
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
<uniqueId>{unique_id}</uniqueId>
<generationTime>{gen_time_str}</generationTime>
<expirationTime>{exp_time_str}</expirationTime>
</header>
<service>{service}</service>
</loginTicketRequest>"""


def sign_tra_simple(tra_xml, cert_path, key_path):
    """Firmar TRA usando OpenSSL"""
    
    # Detectar OpenSSL disponible
    openssl_paths = [
        'C:\\Program Files\\Git\\mingw64\\bin\\openssl.exe',  # Git mingw64
        'C:\\Program Files\\Git\\usr\\bin\\openssl.exe',  # Git para Windows
        'C:\\Program Files\\OpenSSL-Win64\\bin\\openssl.exe',  # Instalación estándar
        'C:\\OpenSSL-Win64\\bin\\openssl.exe',  # Instalación alternativa
        'openssl'  # Si está en PATH
    ]
    
    openssl_cmd = None
    for path in openssl_paths:
        try:
            result = subprocess.run([path, 'version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                openssl_cmd = path
                break
        except:
            continue
    
    if not openssl_cmd:
        raise Exception("OpenSSL no encontrado en el sistema")
    
    print(f"   🔧 Usando OpenSSL: {openssl_cmd}")
    
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
            '-inkey', key_path,
            '-signer', cert_path,
            '-nodetach'
        ]
        
        print(f"   🔐 Firmando TRA con OpenSSL...")
        result = subprocess.run(cmd, capture_output=True, check=True)
        print(f"   ✅ TRA firmado exitosamente")
        
        with open(cms_file, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(tra_file):
            os.unlink(tra_file)
        if os.path.exists(cms_file):
            os.unlink(cms_file)
def wsaa_auth_simple(cert_path, key_path):
    """Autenticación WSAA simplificada"""
    # URLs según entorno
    afip_env = os.environ.get('AFIP_ENV', 'prod')
    wsaa_urls = {
        'prod': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
        'homo': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms'
    }
    
    # Crear y firmar TRA
    tra_xml = build_simple_tra('wsfe')
    signed_tra = sign_tra_simple(tra_xml, cert_path, key_path)
    tra_b64 = base64.b64encode(signed_tra).decode('utf-8')
    
    # Construir SOAP request
    soap_request = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
<soap:Body>
    <loginCms xmlns="http://wsaa.view.sua.dvadac.desein.afip.gov">
        <in0>{tra_b64}</in0>
    </loginCms>
</soap:Body>
</soap:Envelope>"""
    
    # Enviar request
    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': ''
    }
    
    print(f"   📡 Enviando request WSAA a: {wsaa_urls[afip_env]}")
    
    try:
        response = requests.post(wsaa_urls[afip_env], data=soap_request, headers=headers, timeout=30)
        print(f"   📊 Respuesta HTTP: {response.status_code}")
        
        if response.status_code != 200:
            print(f"   ❌ Error HTTP {response.status_code}: {response.text[:500]}")
            
    except Exception as e:
        print(f"   ❌ Error de conexión: {e}")
        raise
        
    response.raise_for_status()
    
    # Parsear respuesta con manejo de encoding
    try:
        response_text = response.text
        print(f"   📝 Respuesta AFIP recibida (primeros 200 chars): {response_text[:200]}")
        
        # Guardar respuesta completa para debug
        with open('debug_wsaa/WSAA_response.xml', 'w', encoding='utf-8') as f:
            f.write(response_text)
        print(f"   💾 Respuesta completa guardada en debug_wsaa/WSAA_response.xml")
        
        root = ET.fromstring(response_text)
        login_return = None
        
        for elem in root.iter():
            if 'loginCmsReturn' in elem.tag:
                login_return = elem.text
                break
        
        if not login_return:
            raise Exception("No se encontró loginCmsReturn en la respuesta")
        
        print(f"   🔓 Decodificando credenciales...")
        
        # El loginCmsReturn contiene XML escapado, necesitamos desenscaparlo
        import html
        login_xml = html.unescape(login_return)
        
        # Guardar el XML desenscapado para debug
        with open('debug_wsaa/loginCmsReturn.unescaped.xml', 'w', encoding='utf-8') as f:
            f.write(login_xml)
        
        print(f"   📝 XML credentials (primeros 200 chars): {login_xml[:200]}")
        login_root = ET.fromstring(login_xml)
        
        credentials = {}
        for child in login_root.iter():
            if child.tag in ['token', 'sign']:
                credentials[child.tag] = child.text
        
        if 'token' not in credentials or 'sign' not in credentials:
            raise Exception("No se encontraron token y sign en la respuesta")
        
        print(f"   ✅ Credenciales obtenidas: Token presente, Sign presente")
        return credentials['token'], credentials['sign']
        
    except Exception as e:
        print(f"   ❌ Error parseando respuesta AFIP: {e}")
        raise


def wsfe_request_simple(method, params, token, sign, cuit):
    """Request WSFE simplificado"""
    afip_env = os.environ.get('AFIP_ENV', 'prod')
    wsfe_urls = {
        'prod': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx',
        'homo': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx'
    }
    
    # Construir SOAP según método
    if method == 'FEParamGetPtosVenta':
        soap_body = f"""
        <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{token}</Token>
                <Sign>{sign}</Sign>
                <Cuit>{cuit}</Cuit>
            </Auth>
        </{method}>"""
    
    elif method == 'FECompConsultar':
        soap_body = f"""
        <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{token}</Token>
                <Sign>{sign}</Sign>
                <Cuit>{cuit}</Cuit>
            </Auth>
            <FeCompConsReq>
                <PtoVta>{params['PtoVta']}</PtoVta>
                <CbteTipo>{params['CbteTipo']}</CbteTipo>
                <CbteNro>{params['CbteNro']}</CbteNro>
            </FeCompConsReq>
        </{method}>"""
    
    elif method == 'FECompUltimoAutorizado':
        soap_body = f"""
        <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{token}</Token>
                <Sign>{sign}</Sign>
                <Cuit>{cuit}</Cuit>
            </Auth>
            <PtoVta>{params['PtoVta']}</PtoVta>
            <CbteTipo>{params['CbteTipo']}</CbteTipo>
        </{method}>"""
    
    elif method in ['FEParamGetTiposCbte', 'FEParamGetTiposDoc', 'FEParamGetTiposIva', 'FEParamGetMonedas']:
        # Métodos de parámetros sin parámetros adicionales
        soap_body = f"""
        <{method} xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{token}</Token>
                <Sign>{sign}</Sign>
                <Cuit>{cuit}</Cuit>
            </Auth>
        </{method}>"""
    
    else:
        # Método no soportado
        raise Exception(f"Método WSFE no soportado: {method}")
    
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
    
    # Configuración SSL para AFIP
    import ssl
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Crear sesión con configuración SSL relajada para AFIP
    session = requests.Session()
    
    # Configurar adapter con SSL context personalizado
    class AFIPHTTPSAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            context = ssl.create_default_context()
            context.set_ciphers('DEFAULT:@SECLEVEL=1')  # Permite DH keys pequeñas
            kwargs['ssl_context'] = context
            return super().init_poolmanager(*args, **kwargs)
    
    session.mount('https://', AFIPHTTPSAdapter())
    
    response = session.post(wsfe_urls[afip_env], data=soap_request, headers=headers, timeout=30)
    
    if response.status_code != 200:
        return None
    
    # Parsear respuesta XML
    try:
        root = ET.fromstring(response.text)
        return root
    except:
        return None


def extraer_facturas_simple(cuit, desde=None, hasta=None, punto_venta=None, fecha_desde=None, fecha_hasta=None, cert_path=None, key_path=None, max_por_tipo=50, cuit_consultor=None):
    """Extracción simplificada de facturas con lógica FE completa
    
    Args:
        cuit: CUIT del cliente a consultar (facturas a extraer)
        cuit_consultor: CUIT del consultor/contador (para autenticación). Si no se especifica, usa el mismo que 'cuit'
    """
    
    # Si no se especifica consultor, usar el mismo CUIT para auth y consulta
    if cuit_consultor is None:
        cuit_consultor = cuit
    
    print(f"🔐 Autenticando con AFIP...")
    print(f"   Consultor (certificado): {cuit_consultor}")
    print(f"   Cliente a consultar: {cuit}")
    
    # Normalizar parámetros de fecha (compatibilidad con diferentes llamadas)
    if desde is None and fecha_desde is not None:
        desde = fecha_desde
    if hasta is None and fecha_hasta is not None:
        hasta = fecha_hasta
        
    if desde is None or hasta is None:
        print("❌ Se requieren fechas desde y hasta")
        return []
    
    # Autenticación (siempre con el certificado del consultor)
    try:
        # Usar rutas absolutas para los certificados
        import os
        from pathlib import Path
        
        # Si estamos en src/, subir un nivel para encontrar certs/
        if os.path.basename(os.getcwd()) == 'src':
            base_dir = Path(os.getcwd()).parent
        else:
            base_dir = Path(os.getcwd())
        
        cert_path = base_dir / 'certs' / 'certificado.crt'
        key_path = base_dir / 'certs' / 'clave_privada.key'
        
        print(f"   Usando certificado: {cert_path}")
        print(f"   Usando clave: {key_path}")
        
        if not cert_path.exists():
            raise FileNotFoundError(f"No se encontró {cert_path}")
        if not key_path.exists():
            raise FileNotFoundError(f"No se encontró {key_path}")
        
        token, sign = wsaa_auth_simple(str(cert_path), str(key_path))
        print("✅ Autenticación WSAA exitosa")
    except Exception as e:
        print(f"❌ Error autenticación: {e}")
        return []
    
    consultor_cuit = cuit_consultor  # Para auth
    cliente_cuit = cuit              # Para consultar facturas
    comprobantes = []
    
    # PASO 1: Obtener puntos de venta → FEParamGetPtosVenta
    print(f"📋 Consultando puntos de venta del cliente {cliente_cuit}...")
    ptos_venta_resp = wsfe_request_simple('FEParamGetPtosVenta', {}, token, sign, consultor_cuit)
    
    ptos_venta = [1, 2, 3, 4, 5]  # Probar múltiples PV por defecto
    if ptos_venta_resp:
        try:
            # ptos_venta_resp ya es un ElementTree
            pts = []
            print("📋 Respuesta FEParamGetPtosVenta recibida:")
            for pto in ptos_venta_resp.findall('.//PtoVenta'):
                id_elem = pto.find('Id')
                bloq_elem = pto.find('Bloqueado')
                if id_elem is not None and bloq_elem is not None:
                    pto_id = int(id_elem.text)
                    bloqueado = bloq_elem.text == 'S'
                    print(f"   PV {pto_id}: {'🔒 Bloqueado' if bloqueado else '✅ Disponible'}")
                    if not bloqueado:  # No bloqueado
                        pts.append(pto_id)
            if pts:
                ptos_venta = pts
            else:
                print("   ⚠️ No se encontraron puntos de venta disponibles, usando defaults")
        except Exception as e:
            print(f"⚠️ Error parseando puntos de venta: {e}")
            print("   Usando puntos de venta por defecto")
    else:
        print("📋 No se pudo obtener lista de puntos de venta, usando defaults")
    
    print(f"📋 Puntos de venta a consultar: {ptos_venta}")
    
    # PASO 2: Obtener tipos de comprobante → FEParamGetTiposCbte
    print(f"📄 Consultando tipos de comprobante...")
    tipos_cbte_resp = wsfe_request_simple('FEParamGetTiposCbte', {}, token, sign, consultor_cuit)
    
    # Ampliar tipos para incluir más posibilidades (monotributo)
    tipos_cbte = [1, 6, 11, 51, 52, 53]  # Facturas A,B,C + Monotributo
    if tipos_cbte_resp:
        try:
            # Parsear XML response para extraer tipos
            root = ET.fromstring(tipos_cbte_resp)
            tipos = []
            print("📄 Respuesta FEParamGetTiposCbte recibida:")
            for tipo in root.findall('.//CbteTipo'):
                id_elem = tipo.find('Id')
                desc_elem = tipo.find('Desc')
                if id_elem is not None:
                    tipo_id = int(id_elem.text)
                    desc = desc_elem.text if desc_elem is not None else f'Tipo {tipo_id}'
                    print(f"   Tipo {tipo_id}: {desc}")
                    # Incluir más tipos, especialmente monotributo
                    if tipo_id in [1, 2, 3, 6, 7, 8, 11, 12, 13, 51, 52, 53, 201, 202, 203, 206, 207, 208, 211, 212, 213]:
                        tipos.append(tipo_id)
            if tipos:
                tipos_cbte = tipos
            else:
                print("   ⚠️ No se encontraron tipos válidos, usando defaults")
        except Exception as e:
            print(f"⚠️ Error parseando tipos de comprobante: {e}")
            print("   Usando tipos por defecto")
    else:
        print("📄 No se pudo obtener lista de tipos, usando defaults")
    
    print(f"📄 Tipos de comprobante a consultar: {tipos_cbte}")
    
    total_encontrados = 0
    
    for pto_vta in ptos_venta:
        print(f"\n🏪 === PROCESANDO PUNTO DE VENTA {pto_vta} ===")
        for tipo_cbte in tipos_cbte:
            print(f"🔍 Consultando PV{pto_vta} Tipo{tipo_cbte}...")
            
            # Obtener último autorizado
            ultimo_resp = wsfe_request_simple('FECompUltimoAutorizado', {
                'PtoVta': pto_vta,
                'CbteTipo': tipo_cbte
            }, token, sign, consultor_cuit)
            
            if ultimo_resp is None:
                print(f"   ❌ No se pudo consultar FECompUltimoAutorizado")
                continue
            
            # Parsear último número
            ultimo_nro = 0
            for elem in ultimo_resp.iter():
                if 'CbteNro' in elem.tag:
                    ultimo_nro = int(elem.text or 0)
                    break
            
            if ultimo_nro == 0:
                print(f"   📄 Sin comprobantes en PV{pto_vta} Tipo{tipo_cbte}")
                continue
            
            print(f"   📄 Último autorizado: {ultimo_nro}")
            print(f"   🔍 Buscando desde {ultimo_nro} hasta {max(0, ultimo_nro - max_por_tipo)}")
            
            # Recorrer hacia atrás (limitado)
            encontrados_rama = 0
            vacios_consecutivos = 0
            
            # Buscar hacia atrás más agresivamente
            rango_busqueda = min(200, ultimo_nro)  # Buscar hasta 200 comprobantes hacia atrás
            for nro in range(ultimo_nro, max(0, ultimo_nro - rango_busqueda), -1):
                if vacios_consecutivos >= 20:  # Permitir más huecos consecutivos
                    print(f"      ⏹️ Demasiados vacíos consecutivos ({vacios_consecutivos}), cortando búsqueda")
                    break
                
                cbte_resp = wsfe_request_simple('FECompConsultar', {
                    'PtoVta': pto_vta,
                    'CbteTipo': tipo_cbte,
                    'CbteNro': nro
                }, token, sign, consultor_cuit)
                
                if cbte_resp is None:
                    vacios_consecutivos += 1
                    print(f"      ❌ Comprobante {nro}: No encontrado (vacío {vacios_consecutivos}/10)")
                    continue
                
                # Parsear comprobante
                vacios_consecutivos = 0
                cbte_data = {}
                
                for elem in cbte_resp.iter():
                    tag = elem.tag.split('}')[-1]  # Remover namespace
                    if tag in ['PtoVta', 'CbteTipo', 'CbteNro', 'CbteFch', 'DocTipo', 'DocNro', 
                              'ImpTotal', 'ImpNeto', 'ImpOpEx', 'ImpIVA', 'MonId', 'MonCotiz']:
                        cbte_data[tag] = elem.text
                
                print(f"      📄 Comprobante {nro} encontrado: Fecha={cbte_data.get('CbteFch','?')}")
                
                # Verificar fecha
                if 'CbteFch' in cbte_data:
                    try:
                        fecha_cbte = cbte_data['CbteFch']  # Formato YYYYMMDD
                        fecha_desde_str = desde.replace('-', '') if isinstance(desde, str) else desde.strftime('%Y%m%d')
                        fecha_hasta_str = hasta.replace('-', '') if isinstance(hasta, str) else hasta.strftime('%Y%m%d')
                        
                        print(f"      🔍 Comparando fecha {fecha_cbte} con rango {fecha_desde_str}-{fecha_hasta_str}")
                        
                        if fecha_desde_str <= fecha_cbte <= fecha_hasta_str:
                            cbte_data['PtoVta'] = pto_vta
                            cbte_data['CbteTipo'] = tipo_cbte  
                            cbte_data['CbteNro'] = nro
                            comprobantes.append(cbte_data)
                            encontrados_rama += 1
                            total_encontrados += 1
                            print(f"      ✅ ¡FACTURA ENCONTRADA! Comprobante {nro} - Fecha: {fecha_cbte} - Doc: {cbte_data.get('DocTipo','?')}-{cbte_data.get('DocNro','?')} - Total: ${cbte_data.get('ImpTotal','?')}")
                        elif fecha_cbte < fecha_desde_str:
                            # Ya pasamos el rango, cortar
                            print(f"      📅 Comprobante {nro} fecha {fecha_cbte} anterior al rango {fecha_desde_str}. Cortando búsqueda en este tipo.")
                            break
                        else:
                            print(f"      📅 Comprobante {nro} fecha {fecha_cbte} posterior al rango {fecha_hasta_str}")
                    except Exception as e:
                        print(f"⚠️ Error procesando fecha {cbte_data.get('CbteFch')}: {e}")
                        # Agregar el comprobante de todas formas para debug
                        cbte_data['PtoVta'] = pto_vta
                        cbte_data['CbteTipo'] = tipo_cbte  
                        cbte_data['CbteNro'] = nro
                        comprobantes.append(cbte_data)
                        encontrados_rama += 1
                        total_encontrados += 1
                        print(f"      ⚠️ Agregando comprobante {nro} sin verificar fecha")
                
                # Pequeña pausa
                import time
                time.sleep(0.03)
            
            print(f"   📊 PV{pto_vta} Tipo{tipo_cbte}: {encontrados_rama} facturas encontradas")
    
    print(f"\n🎉 RESUMEN FINAL:")
    print(f"📊 Total encontrado: {total_encontrados} facturas")
    
    # Resumen por punto de venta
    resumen_pv = {}
    for comp in comprobantes:
        pv = comp.get('PtoVta', 'Unknown')
        if pv not in resumen_pv:
            resumen_pv[pv] = 0
        resumen_pv[pv] += 1
    
    print(f"📋 Distribución por punto de venta:")
    for pv in sorted(resumen_pv.keys()):
        print(f"   PV {pv}: {resumen_pv[pv]} facturas")
    
    if not resumen_pv:
        print(f"   (Ninguna factura encontrada en ningún punto de venta)")
        
    return comprobantes


def export_simple(comprobantes, base_path):
    """Exportación simple a CSV y JSON"""
    csv_path = f"{base_path}.csv"
    json_path = f"{base_path}.json"
    
    # CSV
    if comprobantes:
        campos = ['PtoVta', 'CbteTipo', 'CbteNro', 'CbteFch', 'DocTipo', 'DocNro', 
                 'ImpTotal', 'ImpNeto', 'ImpOpEx', 'ImpIVA', 'MonId', 'MonCotiz']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=campos)
            writer.writeheader()
            for comp in comprobantes:
                row = {campo: comp.get(campo, '') for campo in campos}
                writer.writerow(row)
    else:
        # CSV vacío
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['PtoVta', 'CbteTipo', 'CbteNro', 'CbteFch', 'DocTipo', 'DocNro', 
                           'ImpTotal', 'ImpNeto', 'ImpOpEx', 'ImpIVA', 'MonId', 'MonCotiz'])
    
    # JSON  
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(comprobantes, f, indent=2, ensure_ascii=False, default=str)
    
    return {
        'csv': csv_path,
        'json': json_path
    }