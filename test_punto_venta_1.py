#!/usr/bin/env python3
"""
Script para probar específicamente qué facturas hay en el punto de venta 1
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from afip_simple import wsaa_auth_simple, wsfe_request_simple
import xml.etree.ElementTree as ET

def test_punto_venta_1():
    print("🔐 Probando punto de venta 1...")
    
    # Autenticación
    try:
        token, sign = wsaa_auth_simple('certs/certificado.crt', 'certs/clave_privada.key')
        print("✅ Autenticación WSAA exitosa")
    except Exception as e:
        print(f"❌ Error autenticación: {e}")
        return
    
    cuit = "20321518045"  # CUIT de prueba
    punto_venta = 1
    
    # Tipos de comprobante más comunes
    tipos_a_probar = [1, 6, 11]  # Factura A, B, C
    
    print(f"\n📋 Consultando punto de venta {punto_venta} para CUIT {cuit}")
    print("="*60)
    
    for tipo_cbte in tipos_a_probar:
        print(f"\n🔍 TIPO DE COMPROBANTE {tipo_cbte}")
        print("-" * 40)
        
        # Obtener último autorizado
        ultimo_resp = wsfe_request_simple('FECompUltimoAutorizado', {
            'PtoVta': punto_venta,
            'CbteTipo': tipo_cbte
        }, token, sign, cuit)
        
        if ultimo_resp is None:
            print(f"❌ No se pudo consultar FECompUltimoAutorizado")
            continue
        
        # Parsear último número
        ultimo_nro = 0
        try:
            root = ET.fromstring(ultimo_resp)
            for elem in root.iter():
                if 'CbteNro' in elem.tag:
                    ultimo_nro = int(elem.text or 0)
                    break
        except Exception as e:
            print(f"❌ Error parseando respuesta: {e}")
            continue
        
        if ultimo_nro == 0:
            print(f"   📄 Sin comprobantes autorizados")
            continue
        
        print(f"   📄 Último comprobante autorizado: {ultimo_nro}")
        
        # Consultar los últimos 5 comprobantes para ver qué hay
        print(f"   🔍 Consultando últimos 5 comprobantes...")
        
        for nro in range(ultimo_nro, max(0, ultimo_nro - 5), -1):
            cbte_resp = wsfe_request_simple('FECompConsultar', {
                'PtoVta': punto_venta,
                'CbteTipo': tipo_cbte,
                'CbteNro': nro
            }, token, sign, cuit)
            
            if cbte_resp is None:
                print(f"      {nro}: ❌ No encontrado")
                continue
            
            # Parsear datos básicos
            try:
                root = ET.fromstring(cbte_resp)
                datos = {}
                
                for elem in root.iter():
                    tag = elem.tag.split('}')[-1]  # Remover namespace
                    if tag in ['CbteFch', 'DocTipo', 'DocNro', 'ImpTotal']:
                        datos[tag] = elem.text
                
                fecha = datos.get('CbteFch', 'Sin fecha')
                doc_tipo = datos.get('DocTipo', 'Sin doc')
                doc_nro = datos.get('DocNro', 'Sin nro')
                importe = datos.get('ImpTotal', 'Sin importe')
                
                print(f"      {nro}: ✅ Fecha:{fecha} Doc:{doc_tipo}-{doc_nro} Importe:${importe}")
                
            except Exception as e:
                print(f"      {nro}: ⚠️ Error parseando: {e}")

if __name__ == "__main__":
    test_punto_venta_1()