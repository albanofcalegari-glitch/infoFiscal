#!/usr/bin/env python3
"""
Script para extraer comprobantes electrónicos de AFIP WSFEv1 por rango de fechas.

Funcionalidades:
- Autenticación WSAA con certificados PKCS#7 (OpenSSL)
- Consulta WSFEv1 para obtener comprobantes filtrados por fecha
- Exportación a CSV (campos planos) y JSON (con datos _raw completos)
- CLI configurable para rangos de fecha y tipos de comprobante
- Logging estructurado y manejo robusto de errores
- Recorrido inteligente hacia atrás con cortes por fecha y huecos

Ejemplos de uso:
    python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-12-31
    python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-01-31 --incluir-tipos 11,13,15 --out facturas_enero
    python afip_extract_by_date.py --desde 2025-01-01 --hasta 2025-01-31 --excluir-tipos 201,202 --sleep-ms 50 --max-vacios 100

Configuración requerida (.env):
    AFIP_ENV=prod|homo
    AFIP_CUIT=<CUIT numérico>
    AFIP_CERT_PATH=<ruta al certificado.pem>
    AFIP_KEY_PATH=<ruta a clave_privada.pem>
    LOG_LEVEL=INFO|DEBUG (opcional)

Autor: infoFiscal - Optimizado para producción AFIP
"""

# =============================================================================
# IMPORTS Y DEPENDENCIAS
# =============================================================================
import argparse
import base64
import csv
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import requests
from dateutil.parser import parse as parse_date
from dotenv import load_dotenv
from zeep import Client, Transport
from zeep.exceptions import Fault
import sys
import csv
import json
import time
import uuid
import base64
import logging
import argparse
import tempfile
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from dateutil import parser as dateparser
from dotenv import load_dotenv
import requests
from zeep import Client, Settings
from zeep.transports import Transport

# =============================================================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================================================

# Cargar variables de entorno
load_dotenv()

# URLs de servicios AFIP según entorno
AFIP_URLS = {
    'prod': {
        'wsaa': 'https://wsaa.afip.gov.ar/ws/services/LoginCms',
        'wsfe_wsdl': 'https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL'
    },
    'homo': {
        'wsaa': 'https://wsaahomo.afip.gov.ar/ws/services/LoginCms',
        'wsfe_wsdl': 'https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL'
    }
}

# Variables de configuración desde .env
AFIP_ENV = os.getenv('AFIP_ENV', 'prod').lower()
AFIP_CUIT = os.getenv('AFIP_CUIT')
AFIP_CERT_PATH = os.getenv('AFIP_CERT_PATH')
AFIP_KEY_PATH = os.getenv('AFIP_KEY_PATH')

# URLs según entorno
WSAA_URL = AFIP_URLS[AFIP_ENV]['wsaa']
WSFE_WSDL = AFIP_URLS[AFIP_ENV]['wsfe_wsdl']

# Configuración de logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =================== UTILIDADES DE FECHA ===================

def yyyymmdd(dt: datetime) -> str:
    return dt.strftime('%Y%m%d')

def parse_afip_date(s: str) -> datetime:
    return datetime.strptime(s, '%Y%m%d')

def dentro_de_rango(cbte: dict, desde: datetime, hasta: datetime) -> Optional[bool]:
    fch = cbte.get('CbteFch')
    if not fch:
        return None
    try:
        dt = parse_afip_date(fch)
        return desde <= dt <= hasta
    except Exception:
        return None

# =================== DATACLASSES ===================

@dataclass
class WsaaCredentials:
    token: str
    sign: str
    generation_time: datetime
    expiration_time: datetime

@dataclass
class ExtractConfig:
    desde: datetime
    hasta: datetime
    incluir_tipos: List[int] = field(default_factory=list)
    excluir_tipos: List[int] = field(default_factory=list)
    max_vacios_en_rama: int = 80
    sleep_ms: int = 40

# =================== WSAA ===================

def build_login_ticket_request(service: str, ttl_seconds: int = 3600) -> str:
    now = datetime.utcnow()
    gen = now - timedelta(seconds=60)
    exp = now + timedelta(seconds=ttl_seconds)
    return f'''<?xml version="1.0" encoding="UTF-8"?>\n<loginTicketRequest version="1.0">\n  <header>\n    <uniqueId>{int(now.timestamp())}</uniqueId>\n    <generationTime>{gen.strftime('%Y-%m-%dT%H:%M:%S')}.000Z</generationTime>\n    <expirationTime>{exp.strftime('%Y-%m-%dT%H:%M:%S')}.000Z</expirationTime>\n  </header>\n  <service>{service}</service>\n</loginTicketRequest>'''

def sign_tra_pkcs7_openssl(tra_xml: str, cert_path: str, key_path: str) -> bytes:
    with tempfile.NamedTemporaryFile('w', delete=False, suffix='.xml') as f:
        f.write(tra_xml)
        tra_file = f.name
    cms_file = tempfile.mktemp(suffix='.cms')
    try:
        cmd = [
            'openssl', 'smime', '-sign',
            '-in', tra_file,
            '-out', cms_file,
            '-outform', 'DER',
            '-inkey', key_path,
            '-signer', cert_path,
            '-nodetach',
            '-binary'
        ]
        result = subprocess.run(cmd, capture_output=True, timeout=30)
        if result.returncode != 0:
            logger.error(f"OpenSSL error: {result.stderr}")
            raise RuntimeError(f"OpenSSL smime failed: {result.stderr}")
        with open(cms_file, 'rb') as f:
            return f.read()
    finally:
        os.unlink(tra_file)
        if os.path.exists(cms_file):
            os.unlink(cms_file)

def wsaa_login(service: str, cert_path: str, key_path: str) -> WsaaCredentials:
    tra = build_login_ticket_request(service)
    cms_der = sign_tra_pkcs7_openssl(tra, cert_path, key_path)
    cms_b64 = base64.b64encode(cms_der).decode()
    soap = f'''<?xml version="1.0" encoding="UTF-8"?>\n<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:wsaa="http://wsaa.view.sua.dvadac.desein.afip.gov">\n  <soapenv:Header/>\n  <soapenv:Body>\n    <wsaa:loginCms>\n      <wsaa:in0>{cms_b64}</wsaa:in0>\n    </wsaa:loginCms>\n  </soapenv:Body>\n</soapenv:Envelope>'''
    headers = {'Content-Type': 'text/xml; charset=UTF-8', 'SOAPAction': ''}
    resp = requests.post(WSAA_URL, data=soap, headers=headers, timeout=45, verify=True)
    if resp.status_code != 200:
        logger.error(f"WSAA HTTP error: {resp.status_code} {resp.text[:200]}")
        raise RuntimeError(f"WSAA HTTP error: {resp.status_code}")
    from xml.etree import ElementTree as ET
    root = ET.fromstring(resp.text)
    login_return = None
    for elem in root.iter():
        if elem.tag.lower().endswith('logincmsreturn'):
            login_return = elem
            break
    if login_return is None:
        raise RuntimeError("No se encontró <loginCmsReturn> en respuesta WSAA")
    import html
    raw = (login_return.text or '').strip()
    unescaped = html.unescape(raw)
    if '<loginTicketResponse' in unescaped:
        ltr_root = ET.fromstring(unescaped)
    else:
        import base64 as b64
        decoded = b64.b64decode(raw)
        ltr_root = ET.fromstring(decoded)
    token = sign = None
    gen = exp = None
    for elem in ltr_root.iter():
        tag = elem.tag.lower()
        if tag.endswith('token'):
            token = elem.text
        elif tag.endswith('sign'):
            sign = elem.text
        elif tag.endswith('generationtime'):
            gen = dateparser.parse(elem.text)
        elif tag.endswith('expirationtime'):
            exp = dateparser.parse(elem.text)
    if not (token and sign and gen and exp):
        raise RuntimeError("No se pudo extraer token/sign/generation/expiration de loginTicketResponse")
    logger.info(f"WSAA OK. Token expira: {exp}")
    return WsaaCredentials(token, sign, gen, exp)

# =================== CLIENTE WSFE ===================

class WsfeClient:
    """Cliente para AFIP WSFEv1 usando zeep."""
    def __init__(self, cuit: int, token: str, sign: str, wsdl_url: str, timeout: int = 30):
        self.cuit = int(cuit)
        self.token = token
        self.sign = sign
        self.wsdl_url = wsdl_url
        self.timeout = timeout
        session = requests.Session()
        session.verify = True
        self.client = Client(wsdl_url, transport=Transport(session=session, timeout=timeout), settings=Settings(strict=False, xml_huge_tree=True))
    @property
    def auth(self) -> dict:
        return {'Token': self.token, 'Sign': self.sign, 'Cuit': self.cuit}
    def get_ptos_venta(self) -> List[int]:
        res = self.client.service.FEParamGetPtosVenta(Auth=self.auth)
        return [int(pv['Nro']) for pv in getattr(res, 'PtoVenta', []) if 'Nro' in pv]
    def get_tipos_cbte(self) -> List[int]:
        res = self.client.service.FEParamGetTiposCbte(Auth=self.auth)
        return [int(t['Id']) for t in getattr(res, 'ResultGet', []) if 'Id' in t]
    def get_ultimo_autorizado(self, pto_vta: int, tipo_cbte: int) -> int:
        res = self.client.service.FECompUltimoAutorizado(Auth=self.auth, PtoVta=pto_vta, CbteTipo=tipo_cbte)
        return int(getattr(res, 'CbteNro', 0))
    def consultar_cbte(self, pto_vta: int, tipo_cbte: int, nro: int) -> Optional[dict]:
        try:
            res = self.client.service.FECompConsultar(Auth=self.auth, FeCompConsReq={'CbteTipo': tipo_cbte, 'PtoVta': pto_vta, 'CbteNro': nro})
            if hasattr(res, 'ResultGet') and res.ResultGet:
                d = dict(res.ResultGet)
                d['_raw'] = res
                return d
            return None
        except Exception as e:
            logger.debug(f"Cbte {pto_vta}-{tipo_cbte}-{nro} no encontrado: {e}")
            return None

# =================== EXTRACCIÓN POR RANGO ===================

def extraer_comprobantes(wsfe: WsfeClient, cfg: ExtractConfig) -> List[dict]:
    resultados = []
    ptos = wsfe.get_ptos_venta()
    logger.info(f"Puntos de venta detectados: {ptos}")
    tipos = wsfe.get_tipos_cbte()
    logger.info(f"Tipos de comprobante detectados: {tipos}")
    tipos = [t for t in tipos if (not cfg.incluir_tipos or t in cfg.incluir_tipos) and t not in cfg.excluir_tipos]
    logger.info(f"Tipos a consultar: {tipos}")
    for pto in ptos:
        for tipo in tipos:
            ultimo = wsfe.get_ultimo_autorizado(pto, tipo)
            logger.info(f"PtoVta {pto} Tipo {tipo}: último autorizado {ultimo}")
            vacios = 0
            for nro in range(ultimo, 0, -1):
                cbte = wsfe.consultar_cbte(pto, tipo, nro)
                if not cbte:
                    vacios += 1
                    if vacios >= cfg.max_vacios_en_rama:
                        logger.info(f"Corte por {vacios} huecos consecutivos en {pto}-{tipo}")
                        break
                    continue
                vacios = 0
                if not dentro_de_rango(cbte, cfg.desde, cfg.hasta):
                    fch = cbte.get('CbteFch')
                    if fch and parse_afip_date(fch) < cfg.desde:
                        logger.info(f"Corte por fecha en {pto}-{tipo}: {fch} < {yyyymmdd(cfg.desde)}")
                        break
                    continue
                resultados.append(cbte)
                time.sleep(cfg.sleep_ms / 1000.0)
    logger.info(f"Total comprobantes extraídos: {len(resultados)}")
    return resultados

# =================== EXPORTACIÓN ===================

def export_csv_json(rows: List[dict], basepath: str) -> Tuple[str, str]:
    campos = ['PtoVta','CbteTipo','CbteNro','CbteFch','DocTipo','DocNro','ImpTotal','ImpNeto','ImpOpEx','ImpIVA','MonId','MonCotiz','CAE','CAEFchVto']
    csv_path = f"{basepath}.csv"
    json_path = f"{basepath}.json"
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for row in rows:
            plano = {k: row.get(k, '') for k in campos}
            writer.writerow(plano)
    with open(json_path, 'w', encoding='utf-8') as f:
        for row in rows:
            if '_raw' in row:
                row['_raw'] = str(row['_raw'])
        json.dump(rows, f, indent=2, ensure_ascii=False)
    return csv_path, json_path

# =================== CLI Y MAIN ===================

def main():
    parser = argparse.ArgumentParser(description="Extrae comprobantes AFIP WSFEv1 por rango de fechas.")
    parser.add_argument('--desde', required=True, help='Fecha desde (YYYY-MM-DD)')
    parser.add_argument('--hasta', required=True, help='Fecha hasta (YYYY-MM-DD)')
    parser.add_argument('--incluir-tipos', type=str, default='', help='Tipos de comprobante a incluir (ej: 11,13,15)')
    parser.add_argument('--excluir-tipos', type=str, default='', help='Tipos de comprobante a excluir (ej: 201,202)')
    parser.add_argument('--out', type=str, default='afip_extract', help='Base path de salida')
    parser.add_argument('--sleep-ms', type=int, default=40, help='Sleep entre requests (ms)')
    parser.add_argument('--max-vacios', type=int, default=80, help='Máx. huecos consecutivos por rama')
    args = parser.parse_args()
    try:
        desde = dateparser.parse(args.desde)
        hasta = dateparser.parse(args.hasta)
    except Exception:
        logger.error('Fechas inválidas. Formato esperado: YYYY-MM-DD')
        sys.exit(1)
    incluir = [int(x) for x in args.incluir_tipos.split(',') if x.strip().isdigit()]
    excluir = [int(x) for x in args.excluir_tipos.split(',') if x.strip().isdigit()]
    
    # Validar configuración
    if not all([AFIP_CUIT, AFIP_CERT_PATH, AFIP_KEY_PATH]):
        logger.error("Faltan variables de entorno: AFIP_CUIT, AFIP_CERT_PATH, AFIP_KEY_PATH")
        sys.exit(1)
    
    config = ExtractConfig(
        desde=desde,
        hasta=hasta, 
        incluir_tipos=incluir,
        excluir_tipos=excluir,
        max_vacios_en_rama=args.max_vacios,
        sleep_ms=args.sleep_ms
    )
    
    logger.info(f"=== Extrayendo comprobantes AFIP desde {desde.date()} hasta {hasta.date()} ===")
    logger.info(f"Entorno: {AFIP_ENV.upper()}")
    logger.info(f"CUIT: {AFIP_CUIT}")
    
    # Autenticación WSAA
    try:
        credentials = wsaa_login('wsfe', AFIP_CERT_PATH, AFIP_KEY_PATH)
    except Exception as e:
        logger.error(f"Error autenticación WSAA: {e}")
        sys.exit(1)
    
    # Cliente WSFE
    try:
        wsfe = WsfeClient(int(AFIP_CUIT), credentials.token, credentials.sign, WSFE_WSDL)
    except Exception as e:
        logger.error(f"Error inicializando cliente WSFE: {e}")
        sys.exit(1)
    
    # Extracción
    try:
        comprobantes = extraer_comprobantes(wsfe, config)
    except Exception as e:
        logger.error(f"Error extrayendo comprobantes: {e}")
        sys.exit(1)
    
    # Export
    try:
        csv_file, json_file = export_csv_json(comprobantes, args.out)
        logger.info(f"Archivos generados:")
        logger.info(f"  CSV: {csv_file}")
        logger.info(f"  JSON: {json_file}")
        logger.info(f"=== Proceso completado exitosamente ===")
    except Exception as e:
        logger.error(f"Error exportando: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
