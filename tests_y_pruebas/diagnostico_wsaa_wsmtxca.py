#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnóstico del problema de autenticación WSAA para WSMTXCA y WSFEXv1
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from wsmtxca_client import WSMTXCAClient
import xml.etree.ElementTree as ET
import requests
import tempfile

def diagnosticar_wsaa_wsmtxca():
    """Diagnóstico detallado del problema WSAA en WSMTXCA"""
    
    CUIT = "27312238018"
    
    print(f"🔍 DIAGNÓSTICO WSAA DETALLADO - WSMTXCA")
    print("=" * 50)
    
    try:
        client = WSMTXCAClient('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        print("1️⃣ Verificando certificados...")
        cert_path = client.cert_path
        key_path = client.key_path
        print(f"   📄 Certificado: {cert_path}")
        print(f"   🔑 Clave: {key_path}")
        
        # Verificar que existen
        import os
        if os.path.exists(cert_path):
            print(f"   ✅ Certificado existe")
        else:
            print(f"   ❌ Certificado NO existe")
            return
            
        if os.path.exists(key_path):
            print(f"   ✅ Clave privada existe")
        else:
            print(f"   ❌ Clave privada NO existe")
            return
        
        print("\n2️⃣ Creando TRA para WSMTXCA...")
        
        # Crear TRA manualmente paso a paso
        try:
            tra_xml = client._crear_tra('wsmtxca')  # Servicio específico para WSMTXCA
            print(f"   ✅ TRA creado correctamente")
            print(f"   📄 TRA (primeros 200 chars): {tra_xml.decode('utf-8')[:200]}...")
            
        except Exception as e:
            print(f"   ❌ Error creando TRA: {e}")
            return
        
        print("\n3️⃣ Firmando TRA...")
        
        try:
            cms_firmado = client._firmar_tra(tra_xml)
            print(f"   ✅ TRA firmado correctamente")
            print(f"   📝 CMS (primeros 100 chars): {cms_firmado[:100]}...")
            
        except Exception as e:
            print(f"   ❌ Error firmando TRA: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print("\n4️⃣ Enviando a WSAA...")
        
        try:
            # Envío manual a WSAA
            wsaa_url = 'https://wsaa.afip.gov.ar/ws/services/LoginCms'
            
            soap_request = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:log="http://wsaa.view.sua.dvadac.desein.afip.gov">
    <soapenv:Header/>
    <soapenv:Body>
        <log:loginCms>
            <log:in0>{cms_firmado}</log:in0>
        </log:loginCms>
    </soapenv:Body>
</soapenv:Envelope>"""
            
            headers = {
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': ''
            }
            
            print(f"   📤 URL: {wsaa_url}")
            print(f"   📤 Request (primeros 300 chars): {soap_request[:300]}...")
            
            response = requests.post(wsaa_url, data=soap_request, headers=headers, timeout=30)
            
            print(f"   📥 Status Code: {response.status_code}")
            print(f"   📥 Response (primeros 500 chars): {response.text[:500]}...")
            
            if response.status_code == 500:
                print(f"\n   ❌ ERROR 500 DETECTADO!")
                print(f"   🔍 Analizando respuesta de error...")
                
                # Intentar parsear el error
                try:
                    root = ET.fromstring(response.text)
                    
                    # Buscar faultstring
                    for elem in root.iter():
                        if 'faultstring' in elem.tag.lower():
                            print(f"      Error: {elem.text}")
                        elif 'faultcode' in elem.tag.lower():
                            print(f"      Código: {elem.text}")
                            
                except Exception as parse_e:
                    print(f"      No se pudo parsear el error: {parse_e}")
                
                return False
                
            elif response.status_code == 200:
                print(f"   ✅ Respuesta exitosa!")
                
                # Parsear token
                try:
                    root = ET.fromstring(response.text)
                    login_return = None
                    
                    for elem in root.iter():
                        if 'loginCmsReturn' in elem.tag:
                            login_return = elem.text
                            break
                    
                    if login_return:
                        print(f"   ✅ Token obtenido!")
                        return True
                    else:
                        print(f"   ❌ No se encontró loginCmsReturn")
                        return False
                        
                except Exception as e:
                    print(f"   ❌ Error parseando respuesta exitosa: {e}")
                    return False
            
        except Exception as e:
            print(f"   ❌ Error enviando a WSAA: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

def probar_facturas_wsmtxca():
    """Probar las facturas específicas en WSMTXCA si la autenticación funciona"""
    
    CUIT = "27312238018"
    FACTURAS = [235, 236, 237, 238]
    
    print(f"\n🎯 PROBANDO FACTURAS EN WSMTXCA")
    print("=" * 40)
    
    try:
        client = WSMTXCAClient('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        for num in FACTURAS:
            print(f"\n📄 Probando factura {num}:")
            
            try:
                # Probar tipo 51 (Factura M) que es el más común en WSMTXCA
                comp = client.consultar_comprobante(CUIT, 51, 2, num)
                
                if comp:
                    print(f"   🎉 ¡ENCONTRADA!")
                    print(f"      CAE: {comp.get('cae', 'N/A')}")
                    print(f"      Fecha: {comp.get('fecha', 'N/A')}")
                    print(f"      Total: ${comp.get('total', 'N/A')}")
                else:
                    print(f"   📭 No encontrada")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    except Exception as e:
        print(f"❌ Error creando cliente WSMTXCA: {e}")

if __name__ == "__main__":
    # Primero diagnosticar WSAA
    wsaa_ok = diagnosticar_wsaa_wsmtxca()
    
    # Si WSAA funciona, probar las facturas
    if wsaa_ok:
        probar_facturas_wsmtxca()
    else:
        print(f"\n💡 CONCLUSIÓN:")
        print(f"   El problema está en la autenticación WSAA para WSMTXCA")
        print(f"   Posibles causas:")
        print(f"   • Certificado sin permisos para servicio 'wsmtxca'")
        print(f"   • Servicio 'wsmtxca' mal especificado en TRA")
        print(f"   • Formato del CMS incorrecto")
        print(f"   • Problema temporal de AFIP")
    
    print(f"\n✅ DIAGNÓSTICO COMPLETADO")