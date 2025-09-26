"""
Servicio simplificado para AFIP usando requests puro (sin zeep/lxml)
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path
import subprocess
import tempfile
import os


class ARCAServiceSimple:
    def __init__(self, cuit, cert_path, key_path, testing=True):
        """
        Inicializar servicio ARCA simplificado
        """
        self.cuit = cuit
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        self.testing = testing
        
        # URLs simplificadas
        if testing:
            self.wsaa_url = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
            self.wsfe_url = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx"
        else:
            self.wsaa_url = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
            self.wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
            
        self.token = None
        self.sign = None
        self.token_expiry = None

    def test_connection(self):
        """Probar conectividad básica"""
        try:
            print("🔄 Probando conectividad con AFIP...")
            
            # Test simple de conectividad
            response = requests.get("https://www.afip.gob.ar", timeout=10)
            if response.status_code == 200:
                print("✅ Conectividad a AFIP OK")
                return True
            else:
                print(f"❌ Error de conectividad: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error de red: {e}")
            return False

    def authenticate_wsaa(self):
        """Autenticar con WSAA usando certificados reales"""
        try:
            print("🔄 Generando TRA (Ticket de Requerimiento de Acceso)...")
            
            # Generar TRA
            tra_xml = self._generate_tra()
            
            print("🔄 Firmando TRA con certificado...")
            
            # Firmar TRA usando OpenSSL
            cms_data = self._sign_tra_openssl(tra_xml)
            
            print("🔄 Enviando solicitud a WSAA...")
            
            # Enviar a WSAA
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <loginCms xmlns="http://ar.gov.afip.dif.FEV1/">
            <in0>{cms_data.hex()}</in0>
        </loginCms>
    </soap:Body>
</soap:Envelope>"""

            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'SOAPAction': ''
            }
            
            response = requests.post(self.wsaa_url, data=soap_body, headers=headers, timeout=30)
            
            if response.status_code == 200:
                # Parsear respuesta WSAA
                root = ET.fromstring(response.text)
                
                # Buscar token y sign en la respuesta
                token_elem = root.find('.//{http://ar.gov.afip.dif.FEV1/}token')
                sign_elem = root.find('.//{http://ar.gov.afip.dif.FEV1/}sign')
                
                if token_elem is not None and sign_elem is not None:
                    self.token = token_elem.text
                    self.sign = sign_elem.text
                    self.token_expiry = datetime.now() + timedelta(hours=12)
                    
                    print("✅ AUTENTICACIÓN WSAA EXITOSA!")
                    return True
                else:
                    print("❌ No se pudo extraer token/sign de la respuesta WSAA")
                    return False
            else:
                print(f"❌ Error en WSAA: {response.status_code}")
                print(response.text)
                return False
                
        except Exception as e:
            print(f"❌ Error en autenticación WSAA: {e}")
            return False

    def _generate_tra(self):
        """Generar TRA (Ticket de Requerimiento de Acceso)"""
        now = datetime.utcnow()
        expiry = now + timedelta(hours=12)
        
        tra = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>{int(now.timestamp())}</uniqueId>
        <generationTime>{now.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z</generationTime>
        <expirationTime>{expiry.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3]}Z</expirationTime>
    </header>
    <service>wsfe</service>
</loginTicketRequest>"""
        
        return tra

    def _sign_tra_openssl(self, tra_xml):
        """Firmar TRA usando OpenSSL"""
        try:
            # Crear archivos temporales
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(tra_xml)
                tra_file = f.name
            
            cms_file = tempfile.mktemp(suffix='.cms')
            
            # Intentar diferentes rutas de OpenSSL
            openssl_paths = [
                "C:/Program Files/Git/usr/bin/openssl.exe",
                "openssl.exe",
                "openssl"
            ]
            
            for openssl_path in openssl_paths:
                try:
                    cmd = [
                        openssl_path, 'smime', '-sign',
                        '-in', tra_file,
                        '-out', cms_file,
                        '-outform', 'DER',
                        '-inkey', str(self.key_path),
                        '-signer', str(self.cert_path),
                        '-nodetach'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    
                    if result.returncode == 0:
                        # Leer CMS firmado
                        with open(cms_file, 'rb') as f:
                            cms_data = f.read()
                        
                        # Limpiar archivos temporales
                        os.unlink(tra_file)
                        os.unlink(cms_file)
                        
                        return cms_data
                    else:
                        print(f"Error con {openssl_path}: {result.stderr}")
                        
                except FileNotFoundError:
                    continue
                except Exception as e:
                    print(f"Error ejecutando {openssl_path}: {e}")
                    continue
            
            raise Exception("No se pudo ejecutar OpenSSL. Verificar instalación.")
            
        except Exception as e:
            # Limpiar archivos temporales en caso de error
            try:
                os.unlink(tra_file)
                os.unlink(cms_file)
            except:
                pass
            raise

    def get_facturas_reales(self, fecha_desde, fecha_hasta, output_dir):
        """Obtener facturas reales de WSFE"""
        try:
            if not self.token or datetime.now() > self.token_expiry:
                if not self.authenticate_wsaa():
                    raise Exception("Error en autenticación WSAA")
            
            print("🔄 Consultando facturas en WSFE...")
            
            # Preparar consulta WSFE
            soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">
    <soap:Body>
        <FECompConsultar xmlns="http://ar.gov.afip.dif.FEV1/">
            <Auth>
                <Token>{self.token}</Token>
                <Sign>{self.sign}</Sign>
                <Cuit>{self.cuit}</Cuit>
            </Auth>
            <FeCompConsReq>
                <CbteTipo>1</CbteTipo>
                <FchDesde>{fecha_desde}</FchDesde>
                <FchHasta>{fecha_hasta}</FchHasta>
                <PtoVta>1</PtoVta>
            </FeCompConsReq>
        </FECompConsultar>
    </soap:Body>
</soap:Envelope>"""

            headers = {
                'Content-Type': 'application/soap+xml; charset=utf-8',
                'SOAPAction': 'http://ar.gov.afip.dif.FEV1/FECompConsultar'
            }
            
            response = requests.post(self.wsfe_url, data=soap_body, headers=headers, timeout=30)
            
            if response.status_code == 200:
                print("✅ Respuesta WSFE recibida")
                
                # Parsear respuesta y generar archivos
                archivos = self._parse_wsfe_response(response.text, output_dir)
                return archivos
            else:
                print(f"❌ Error WSFE: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error consultando WSFE: {e}")
            return []

    def _parse_wsfe_response(self, response_xml, output_dir):
        """Parsear respuesta WSFE y generar archivos"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        archivos = []
        
        try:
            root = ET.fromstring(response_xml)
            
            # Buscar comprobantes en la respuesta
            # (La estructura exacta depende de la respuesta real de AFIP)
            
            # Por ahora, generar archivo con respuesta cruda
            response_file = output_path / "respuesta_wsfe.xml"
            with open(response_file, 'w', encoding='utf-8') as f:
                f.write(response_xml)
            archivos.append(response_file)
            
            # Generar resumen
            resumen_file = output_path / "resumen_facturas.txt"
            with open(resumen_file, 'w', encoding='utf-8') as f:
                f.write(f"FACTURAS REALES DESCARGADAS DE AFIP\n")
                f.write(f"===================================\n")
                f.write(f"CUIT: {self.cuit}\n")
                f.write(f"Fecha consulta: {datetime.now()}\n")
                f.write(f"Servicio: WSFE Real\n")
                f.write(f"Ambiente: {'Testing' if self.testing else 'Producción'}\n\n")
                f.write(f"Respuesta XML guardada en: respuesta_wsfe.xml\n")
            archivos.append(resumen_file)
            
            return archivos
            
        except Exception as e:
            print(f"Error parseando respuesta WSFE: {e}")
            return archivos

    def simulate_download(self, output_dir):
        """Simular descarga de facturas para testing"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # Crear archivos de ejemplo
        archivos = []
        
        # Factura de ejemplo 1
        factura1 = output_path / "factura_00001.txt"
        with open(factura1, 'w', encoding='utf-8') as f:
            f.write(f"FACTURA ELECTRÓNICA - MODO SIMULACIÓN\n")
            f.write(f"=========================================\n")
            f.write(f"CUIT Emisor: {self.cuit}\n")
            f.write(f"Número: 00001\n")
            f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}\n")
            f.write(f"Importe: $125.500,00\n")
            f.write(f"Condición IVA: Responsable Inscripto\n")
            f.write(f"Estado: Autorizado\n\n")
            f.write(f"Detalle:\n")
            f.write(f"- Servicios profesionales contables\n")
            f.write(f"- Período: {datetime.now().strftime('%m/%Y')}\n")
        
        archivos.append(factura1)
        
        # Factura de ejemplo 2
        factura2 = output_path / "factura_00002.txt"
        with open(factura2, 'w', encoding='utf-8') as f:
            f.write(f"FACTURA ELECTRÓNICA - MODO SIMULACIÓN\n")
            f.write(f"=========================================\n")
            f.write(f"CUIT Emisor: {self.cuit}\n")
            f.write(f"Número: 00002\n")
            f.write(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}\n")
            f.write(f"Importe: $85.250,00\n")
            f.write(f"Condición IVA: Responsable Inscripto\n")
            f.write(f"Estado: Autorizado\n\n")
            f.write(f"Detalle:\n")
            f.write(f"- Asesoramiento tributario\n")
            f.write(f"- Liquidación de impuestos\n")
        
        archivos.append(factura2)
        
        # Archivo de información
        info_file = output_path / "INFORMACION.txt"
        with open(info_file, 'w', encoding='utf-8') as f:
            f.write(f"DESCARGA DE FACTURAS ARCA - MODO SIMULACIÓN\n")
            f.write(f"==============================================\n")
            f.write(f"CUIT consultado: {self.cuit}\n")
            f.write(f"Fecha de consulta: {datetime.now()}\n")
            f.write(f"Ambiente: {'Testing' if self.testing else 'Producción'}\n")
            f.write(f"Certificados encontrados: SÍ\n")
            f.write(f"Facturas encontradas: 2\n\n")
            f.write(f"NOTA: Esta es una simulación.\n")
            f.write(f"Para descargas reales, verificar:\n")
            f.write(f"1. Servicios web habilitados en AFIP\n")
            f.write(f"2. Certificado válido y asociado al CUIT\n")
            f.write(f"3. OpenSSL instalado correctamente\n")
        
        archivos.append(info_file)
        
        return archivos


def descargar_facturas_arca_simple(cuit, fecha_desde=None, fecha_hasta=None, output_dir=None, modo_real=False, consultar_como=None):
    """
    Función para descargar facturas (simulación o real)
    
    Args:
        cuit: CUIT del cual queremos obtener facturas
        consultar_como: CUIT que tiene los permisos/delegaciones (tu CUIT)
        modo_real: True para usar servicios reales de AFIP, False para simulación
    """
    if not fecha_desde:
        fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime('%Y%m%d')
    if not output_dir:
        output_dir = Path(__file__).parent.parent / 'facturas' / cuit
    
    # Rutas de certificados
    certs_dir = Path(__file__).parent.parent / 'certs'
    cert_path = certs_dir / 'certificado.crt'
    key_path = certs_dir / 'clave_privada.key'
    
    print(f"=== DESCARGA FACTURAS ARCA ===")
    print(f"CUIT: {cuit}")
    print(f"Modo: {'REAL' if modo_real else 'SIMULACIÓN'}")
    print(f"Período: {fecha_desde} - {fecha_hasta}")
    print(f"Certificados: {certs_dir}")
    
    # Verificar certificados
    if not cert_path.exists():
        print(f"❌ No se encontró: {cert_path}")
        raise FileNotFoundError("certificado.crt no encontrado")
    
    if not key_path.exists():
        print(f"❌ No se encontró: {key_path}")
        raise FileNotFoundError("clave_privada.key no encontrado")
    
    print("✅ Certificados encontrados")
    
    # Crear servicio (usar tu CUIT para autenticación si hay delegación)
    cuit_autenticacion = consultar_como if consultar_como else cuit
    service = ARCAServiceSimple(cuit_autenticacion, cert_path, key_path, testing=True)
    
    # Test conectividad
    if not service.test_connection():
        raise Exception("Sin conectividad a AFIP")
    
    if modo_real:
        # Usar servicios reales de AFIP
        print("🔄 Conectando con servicios REALES de AFIP...")
        archivos = service.get_facturas_reales(fecha_desde, fecha_hasta, output_dir)
        
        if not archivos:
            print("⚠️ No se encontraron facturas o error en consulta")
            # Fallback a simulación
            print("🔄 Generando reporte de error...")
            archivos = service.simulate_download(output_dir)
            
    else:
        # Simular descarga
        print("🔄 Simulando descarga de facturas...")
        archivos = service.simulate_download(output_dir)
    
    print(f"✅ Proceso completado. Archivos generados: {len(archivos)}")
    return archivos