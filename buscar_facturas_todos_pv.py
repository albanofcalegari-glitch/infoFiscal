#!/usr/bin/env python3
"""
Buscar facturas en TODOS los puntos de venta (incluyendo dados de baja)
"""

from afip_simple import wsaa_auth_simple, wsfe_request_simple
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

def buscar_facturas_todos_pv():
    print("🎯 === BÚSQUEDA EN TODOS LOS PUNTOS DE VENTA ===")
    print("CUIT: 20321518045 - CALEGARI ALBANO FEDERICO")
    print("Incluye PV dados de baja (facturas anteriores)")
    print("------------------------------------------------------------")
    
    cert_path = r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\certificado.crt"
    key_path = r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\clave_privada.key"
    
    cuit = "20321518045"
    
    # Lista de puntos de venta a probar (1 al 10 para asegurar)
    puntos_venta = [1, 2, 3, 4, 5]
    tipos_comprobante = [1, 6, 11, 51, 52, 53]  # Facturas A, B, C y Monotributo
    
    try:
        # Autenticar
        print(f"\n🔐 Autenticando con AFIP...")
        token, sign = wsaa_auth_simple(cert_path, key_path)
        print(f"✅ Autenticación WSAA exitosa")
        
        total_facturas = 0
        
        for pv in puntos_venta:
            print(f"\n🏪 === PUNTO DE VENTA {pv} ===")
            
            for tipo_cbte in tipos_comprobante:
                print(f"   📄 Tipo {tipo_cbte}...", end="")
                
                try:
                    # Consultar último autorizado
                    params = {
                        'PtoVta': pv,
                        'CbteTipo': tipo_cbte
                    }
                    
                    ultimo_resp = wsfe_request_simple('FECompUltimoAutorizado', params, token, sign, cuit)
                    
                    if ultimo_resp is None:
                        print(f" ❌ Sin respuesta")
                        continue
                    
                    # Buscar último número
                    ultimo_nro = 0
                    for elem in ultimo_resp.iter():
                        if 'CbteNro' in elem.tag:
                            ultimo_nro = int(elem.text or 0)
                            break
                    
                    if ultimo_nro > 0:
                        print(f" ✅ Último: {ultimo_nro}")
                        total_facturas += ultimo_nro
                        
                        # Si encontramos facturas, buscar algunas específicas
                        if ultimo_nro > 0:
                            print(f"      🔍 Buscando facturas recientes...")
                            
                            # Buscar las últimas 3 facturas
                            for nro in range(max(1, ultimo_nro - 2), ultimo_nro + 1):
                                consulta_params = {
                                    'PtoVta': pv,
                                    'CbteTipo': tipo_cbte, 
                                    'CbteNro': nro
                                }
                                
                                factura_resp = wsfe_request_simple('FECompConsultar', consulta_params, token, sign, cuit)
                                
                                if factura_resp is not None:
                                    # Extraer datos de la factura
                                    fecha = total = cae = ""
                                    
                                    for elem in factura_resp.iter():
                                        if elem.tag.endswith('CbteFch'):
                                            fecha = elem.text or ""
                                        elif elem.tag.endswith('ImpTotal'):
                                            total = elem.text or "0"
                                        elif elem.tag.endswith('CodAutorizacion'):
                                            cae = elem.text or ""
                                    
                                    print(f"      📋 Factura {nro}: Fecha {fecha}, Total ${total}, CAE {cae[:10]}...")
                    else:
                        print(f" 📭 Sin facturas")
                        
                except Exception as e:
                    print(f" ❌ Error: {str(e)[:50]}...")
        
        print(f"\n🎉 === RESUMEN FINAL ===")
        print(f"📊 Facturas encontradas: {total_facturas}")
        
        if total_facturas == 0:
            print(f"\n💡 POSIBLES CAUSAS:")
            print(f"   • Las facturas son de talonario (papel)")
            print(f"   • Usar tipos de comprobante diferentes")
            print(f"   • El CUIT consultado no ha emitido facturas electrónicas")
            print(f"   • Las facturas están en otro servicio (no WSFEv1)")
            
    except Exception as e:
        print(f"❌ Error general: {e}")

if __name__ == "__main__":
    buscar_facturas_todos_pv()