#!/usr/bin/env python3
"""
Consulta todos los puntos de venta disponibles para el CUIT
"""

from afip_simple import wsaa_auth_simple, wsfe_request_simple
import xml.etree.ElementTree as ET

def consultar_puntos_venta():
    print("🎯 === CONSULTANDO PUNTOS DE VENTA DISPONIBLES ===")
    print("CUIT: 20321518045 - CALEGARI ALBANO FEDERICO")
    print("------------------------------------------------------------")
    
    cert_path = r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\certificado.crt"
    key_path = r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\clave_privada.key"
    
    print(f"📄 Certificado: {cert_path}")
    print(f"🔑 Clave: {key_path}")
    
    cuit = "20321518045"
    
    try:
        # Autenticar
        print(f"\n🔐 Autenticando con AFIP...")
        token, sign = wsaa_auth_simple(cert_path, key_path)
        print(f"✅ Autenticación WSAA exitosa")
        
        # Consultar puntos de venta
        print(f"\n🏪 Consultando puntos de venta disponibles...")
        
        params = {}
        ptos_venta_resp = wsfe_request_simple('FEParamGetPtosVenta', params, token, sign, cuit)
        
        if ptos_venta_resp is None:
            print("❌ No se pudo obtener puntos de venta")
            return
        
        # Parsear respuesta
        puntos_venta = []
        for elem in ptos_venta_resp.iter():
            if elem.tag.endswith('PtoVenta'):
                pv_data = {}
                for child in elem:
                    if child.tag.endswith('Nro'):
                        pv_data['numero'] = child.text
                    elif child.tag.endswith('EmisionTipo'):
                        pv_data['tipo'] = child.text
                    elif child.tag.endswith('Bloqueado'):
                        pv_data['bloqueado'] = child.text
                    elif child.tag.endswith('FchBaja'):
                        pv_data['fecha_baja'] = child.text
                
                if 'numero' in pv_data:
                    puntos_venta.append(pv_data)
        
        print(f"\n📋 PUNTOS DE VENTA ENCONTRADOS: {len(puntos_venta)}")
        print("=" * 60)
        
        for pv in puntos_venta:
            numero = pv.get('numero', 'N/A')
            tipo = pv.get('tipo', 'N/A')
            bloqueado = pv.get('bloqueado', 'N/A')
            fecha_baja = pv.get('fecha_baja', 'N/A')
            
            estado = "🟢 ACTIVO" if bloqueado == "N" else "🔴 BLOQUEADO"
            if fecha_baja and fecha_baja != "None":
                estado = "❌ DADO DE BAJA"
            
            print(f"🏪 PV {numero:>3} | Tipo: {tipo} | {estado}")
        
        print(f"\n💡 PRÓXIMOS PASOS:")
        print(f"   • Probar extracción en cada punto de venta activo")
        print(f"   • Verificar tipos de comprobante disponibles") 
        print(f"   • Consultar rangos de fechas específicos")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Necesitas instalar OpenSSL para que funcione la autenticación")

if __name__ == "__main__":
    consultar_puntos_venta()