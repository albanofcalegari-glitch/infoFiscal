"""
Servicio para consumir web services de ARCA/AFIP
Requiere certificados digitales y configuración previa
"""

import os
from pathlib import Path
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from zeep import Client, wsse
from zeep.transports import Transport
import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12


class ARCAService:
    def __init__(self, cuit, cert_path, key_path, testing=True):
        """
        Inicializar servicio ARCA
        
        Args:
            cuit: CUIT del contribuyente
            cert_path: Ruta al certificado .crt
            key_path: Ruta a la clave privada .key
            testing: True para ambiente de testing, False para producción
        """
        self.cuit = cuit
        self.cert_path = Path(cert_path)
        self.key_path = Path(key_path)
        self.testing = testing
        
        # URLs de AFIP
        if testing:
            self.wsaa_url = "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"
            self.wsfe_url = "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
        else:
            self.wsaa_url = "https://wsaa.afip.gov.ar/ws/services/LoginCms"
            self.wsfe_url = "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
            
        self.token = None
        self.sign = None
        self.token_expiry = None
    
    def authenticate(self):
        """Autenticar con WSAA y obtener token y sign"""
        try:
            # Generar TRA (Ticket de Requerimiento de Acceso)
            tra = self._generate_tra()
            
            # Firmar TRA con certificado
            cms = self._sign_tra(tra)
            
            # Llamar a WSAA
            client = Client(self.wsaa_url)
            response = client.service.loginCms(cms)
            
            # Parsear respuesta
            root = ET.fromstring(response)
            self.token = root.find('credentials/token').text
            self.sign = root.find('credentials/sign').text
            
            # Establecer expiración (generalmente 12 horas)
            self.token_expiry = datetime.now() + timedelta(hours=12)
            
            return True
        except Exception as e:
            print(f"Error en autenticación WSAA: {e}")
            return False
    
    def _generate_tra(self):
        """Generar Ticket de Requerimiento de Acceso"""
        now = datetime.utcnow()
        expiry = now + timedelta(hours=12)
        
        tra = f"""<?xml version="1.0" encoding="UTF-8"?>
        <loginTicketRequest version="1.0">
            <header>
                <uniqueId>{int(now.timestamp())}</uniqueId>
                <generationTime>{now.strftime('%Y-%m-%dT%H:%M:%S.000Z')}</generationTime>
                <expirationTime>{expiry.strftime('%Y-%m-%dT%H:%M:%S.000Z')}</expirationTime>
            </header>
            <service>wsfe</service>
        </loginTicketRequest>"""
        
        return tra
    
    def _sign_tra(self, tra):
        """Firmar TRA con certificado digital"""
        try:
            # Leer certificado y clave privada
            with open(self.cert_path, 'rb') as f:
                cert_data = f.read()
            
            with open(self.key_path, 'rb') as f:
                key_data = f.read()
            
            # Usar OpenSSL para firmar (requiere instalación separada)
            # Alternativamente, usar cryptography library
            import subprocess
            import tempfile
            
            # Crear archivo temporal para TRA
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(tra)
                tra_file = f.name
            
            # Crear archivo temporal para CMS
            cms_file = tempfile.mktemp(suffix='.cms')
            
            # Comando OpenSSL para firmar
            cmd = [
                'openssl', 'smime', '-sign', '-in', tra_file,
                '-out', cms_file, '-outform', 'DER',
                '-inkey', str(self.key_path),
                '-signer', str(self.cert_path)
            ]
            
            subprocess.run(cmd, check=True)
            
            # Leer CMS firmado
            with open(cms_file, 'rb') as f:
                cms_data = f.read()
            
            # Limpiar archivos temporales
            os.unlink(tra_file)
            os.unlink(cms_file)
            
            return cms_data
            
        except Exception as e:
            print(f"Error al firmar TRA: {e}")
            raise
    
    def get_facturas_emitidas(self, fecha_desde, fecha_hasta):
        """
        Obtener facturas emitidas en un rango de fechas
        
        Args:
            fecha_desde: fecha inicio (YYYYMMDD)
            fecha_hasta: fecha fin (YYYYMMDD)
        """
        if not self.token or datetime.now() > self.token_expiry:
            if not self.authenticate():
                raise Exception("No se pudo autenticar con AFIP")
        
        try:
            # Crear cliente WSFE
            client = Client(self.wsfe_url)
            
            # Preparar parámetros de autenticación
            auth = {
                'Token': self.token,
                'Sign': self.sign,
                'Cuit': self.cuit
            }
            
            # Obtener comprobantes emitidos
            response = client.service.FECompConsultar(
                Auth=auth,
                FeCompConsReq={
                    'CbteTipo': 1,  # Factura A
                    'FchDesde': fecha_desde,
                    'FchHasta': fecha_hasta,
                    'PtoVta': 1
                }
            )
            
            return response
            
        except Exception as e:
            print(f"Error al consultar facturas: {e}")
            raise
    
    def descargar_facturas_pdf(self, facturas_data, output_dir):
        """
        Descargar PDFs de las facturas (simulado - AFIP no provee PDFs directamente)
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        archivos_descargados = []
        
        for factura in facturas_data:
            # Simular generación de PDF con datos de la factura
            filename = f"factura_{factura.get('CbteDesde', 'N/A')}_{factura.get('CbteTipo', 'N/A')}.pdf"
            filepath = output_path / filename
            
            # En la realidad, aquí generarías el PDF o lo descargarías de otro servicio
            self._generar_pdf_factura(factura, filepath)
            archivos_descargados.append(filepath)
        
        return archivos_descargados
    
    def _generar_pdf_factura(self, factura_data, filepath):
        """Generar PDF de factura (placeholder - requiere librería como reportlab)"""
        # Crear un archivo de texto como ejemplo
        with open(filepath.with_suffix('.txt'), 'w', encoding='utf-8') as f:
            f.write(f"FACTURA ELECTRÓNICA\n")
            f.write(f"========================\n")
            f.write(f"CUIT: {self.cuit}\n")
            f.write(f"Tipo: {factura_data.get('CbteTipo', 'N/A')}\n")
            f.write(f"Número: {factura_data.get('CbteDesde', 'N/A')}\n")
            f.write(f"Fecha: {factura_data.get('CbteFch', 'N/A')}\n")
            f.write(f"Importe: ${factura_data.get('ImpTotal', '0.00')}\n")


# Función de conveniencia para usar desde Flask
def descargar_facturas_arca(cuit, fecha_desde=None, fecha_hasta=None, output_dir=None):
    """
    Función para integrar con Flask app
    
    Args:
        cuit: CUIT del cliente
        fecha_desde: fecha inicio (opcional, default: último mes)
        fecha_hasta: fecha fin (opcional, default: hoy)
        output_dir: directorio de salida (opcional)
    """
    if not fecha_desde:
        fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
    if not fecha_hasta:
        fecha_hasta = datetime.now().strftime('%Y%m%d')
    if not output_dir:
        output_dir = Path(__file__).parent.parent / 'facturas' / cuit
    
    # Buscar certificados específicos para este CUIT o usar genérico
    certs_dir = Path(__file__).parent.parent / 'certs'
    
    # Opción 1: Certificado específico para este CUIT
    cert_path = certs_dir / f'{cuit}_certificado.crt'
    key_path = certs_dir / f'{cuit}_clave_privada.key'
    
    # Opción 2: Si no existe específico, usar genérico
    if not (cert_path.exists() and key_path.exists()):
        cert_path = certs_dir / 'certificado.crt'
        key_path = certs_dir / 'clave_privada.key'
    
    if not cert_path.exists() or not key_path.exists():
        raise FileNotFoundError("No se encontraron los certificados AFIP. Colócalos en la carpeta 'certs/'")
    
    # Crear servicio y descargar
    service = ARCAService(cuit, cert_path, key_path, testing=True)
    
    try:
        # Obtener datos de facturas
        facturas = service.get_facturas_emitidas(fecha_desde, fecha_hasta)
        
        # Descargar archivos
        if facturas and facturas.FECompConsultaResponse and facturas.FECompConsultaResponse.ResultGet:
            archivos = service.descargar_facturas_pdf(
                facturas.FECompConsultaResponse.ResultGet, 
                output_dir
            )
            return archivos
        else:
            return []
            
    except Exception as e:
        print(f"Error al descargar facturas: {e}")
        raise