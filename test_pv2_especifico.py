#!/usr/bin/env python3
"""
Búsqueda específica para PV 2 (Factura en Línea - Monotributo)
Enfocado en encontrar las facturas que generaste ahí
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from afip_simple import wsaa_auth_simple, wsfe_request_simple
import xml.etree.ElementTree as ET
from pathlib import Path

def buscar_facturas_pv2():
    print("🎯 === BÚSQUEDA ESPECÍFICA PUNTO DE VENTA 2 ===")
    print("Sistema: Factura en Línea - Monotributo")
    print("CUIT: 20321518045 - CALEGARI ALBANO FEDERICO")
    print("-" * 60)
    
    # Configurar rutas de certificado
    if os.path.basename(os.getcwd()) == 'src':
        base_dir = Path(os.getcwd()).parent
    else:
        base_dir = Path(os.getcwd())
    
    cert_path = base_dir / 'certs' / 'certificado.crt'
    key_path = base_dir / 'certs' / 'clave_privada.key'
    
    print(f"📄 Certificado: {cert_path}")
    print(f"🔑 Clave: {key_path}")
    
    if not cert_path.exists() or not key_path.exists():
        print("❌ Certificados no encontrados")
        return
    
    # Intentar autenticación
    print(f"\n🔐 Autenticando con AFIP...")
    try:
        token, sign = wsaa_auth_simple(str(cert_path), str(key_path))
        print("✅ Autenticación WSAA exitosa")
    except Exception as e:
        print(f"❌ Error autenticación: {e}")
        print("💡 Necesitas instalar OpenSSL para que funcione la autenticación")
        return
    
    cuit = "20321518045"
    punto_venta = 2  # Específicamente PV 2
    
    # Tipos específicos para monotributo
    tipos_monotributo = [51, 52, 53]  # Factura M, ND M, NC M
    tipos_adicionales = [1, 6, 11]   # Por si también usaste RI
    todos_tipos = tipos_monotributo + tipos_adicionales
    
    print(f"\n🏪 Consultando PUNTO DE VENTA {punto_venta}")
    print(f"📋 Tipos a consultar: {todos_tipos}")
    
    total_encontradas = 0
    
    for tipo_cbte in todos_tipos:
        print(f"\n📄 === TIPO {tipo_cbte} ===")
        
        # Obtener último autorizado para este tipo
        try:
            ultimo_resp = wsfe_request_simple('FECompUltimoAutorizado', {
                'PtoVta': punto_venta,
                'CbteTipo': tipo_cbte
            }, token, sign, cuit)
            
            if ultimo_resp is None:
                print(f"   ❌ No se pudo consultar último autorizado")
                continue
            
            # Parsear último número
            ultimo_nro = 0
            try:
                # ultimo_resp ya es un ElementTree, no necesita parsear otra vez
                root = ultimo_resp
                for elem in root.iter():
                    if 'CbteNro' in elem.tag:
                        ultimo_nro = int(elem.text or 0)
                        break
            except Exception as e:
                print(f"   ❌ Error parseando respuesta: {e}")
                continue
            
            if ultimo_nro == 0:
                print(f"   📭 Sin comprobantes para tipo {tipo_cbte}")
                continue
            
            print(f"   📈 Último número autorizado: {ultimo_nro}")
            
            # Buscar los últimos 10 comprobantes de este tipo
            print(f"   🔍 Consultando últimos 10 comprobantes...")
            encontrados_tipo = 0
            
            for nro in range(ultimo_nro, max(0, ultimo_nro - 10), -1):
                try:
                    cbte_resp = wsfe_request_simple('FECompConsultar', {
                        'PtoVta': punto_venta,
                        'CbteTipo': tipo_cbte,
                        'CbteNro': nro
                    }, token, sign, cuit)
                    
                    if cbte_resp is None:
                        print(f"      {nro}: ❌ No encontrado")
                        continue
                    
                    # Parsear datos del comprobante
                    try:
                        root = ET.fromstring(cbte_resp)
                        datos = {}
                        
                        for elem in root.iter():
                            tag = elem.tag.split('}')[-1]
                            if tag in ['CbteFch', 'DocTipo', 'DocNro', 'ImpTotal', 'CbteDesde', 'CbteHasta']:
                                datos[tag] = elem.text
                        
                        fecha = datos.get('CbteFch', 'Sin fecha')
                        doc_tipo = datos.get('DocTipo', '?')
                        doc_nro = datos.get('DocNro', '?')
                        importe = datos.get('ImpTotal', '0')
                        
                        print(f"      {nro}: ✅ Fecha:{fecha} Doc:{doc_tipo}-{doc_nro} Total:${importe}")
                        encontrados_tipo += 1
                        total_encontradas += 1
                        
                    except Exception as e:
                        print(f"      {nro}: ⚠️ Error parseando: {e}")
                
                except Exception as e:
                    print(f"      {nro}: ❌ Error consultando: {e}")
            
            print(f"   📊 Total encontrado tipo {tipo_cbte}: {encontrados_tipo}")
            
        except Exception as e:
            print(f"   ❌ Error general tipo {tipo_cbte}: {e}")
    
    print(f"\n🎉 === RESUMEN ===")
    print(f"🏪 Punto de venta consultado: {punto_venta}")
    print(f"📊 Total facturas encontradas: {total_encontradas}")
    
    if total_encontradas == 0:
        print(f"\n💡 POSIBLES CAUSAS:")
        print(f"   • Las facturas están en otro punto de venta")
        print(f"   • Usar tipos de comprobante diferentes")
        print(f"   • Problema de fechas o rangos")
        print(f"   • Las facturas son de talonario (no electrónicas)")

if __name__ == "__main__":
    buscar_facturas_pv2()