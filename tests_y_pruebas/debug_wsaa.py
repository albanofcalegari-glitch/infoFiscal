#!/usr/bin/env python3
"""
Debug específico de WSAA - ver respuesta detallada de AFIP
"""

import sys
import os
from pathlib import Path
import base64

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def debug_wsaa_completo():
    """Debug completo del proceso WSAA"""
    
    print("🔍 DEBUG WSAA DETALLADO")
    print("=" * 40)
    
    try:
        from arca_service_simple import ARCAServiceSimple, crear_session_afip
        
        # Paso 1: Crear servicio
        print("🔧 Creando servicio AFIP...")
        service = ARCAServiceSimple(
            cuit="20321518045",
            cert_path="certs/certificado.crt", 
            key_path="certs/clave_privada.key",
            testing=False
        )
        
        # Paso 2: Crear TRA manualmente
        print("\n📝 Creando TRA...")
        tra_xml = service._crear_tra()
        print(f"✅ TRA creado ({len(tra_xml)} caracteres)")
        print(f"TRA preview: {tra_xml[:200]}...")
        
        # Paso 3: Firmar TRA
        print("\n🔐 Firmando TRA...")
        cms_data = service._firmar_tra(tra_xml)
        
        if cms_data:
            print(f"✅ TRA firmado ({len(cms_data)} bytes)")
            cms_b64 = base64.b64encode(cms_data).decode('utf-8')
            print(f"CMS Base64 preview: {cms_b64[:100]}...")
        else:
            print("❌ Error firmando TRA")
            return False
        
        # Paso 4: Preparar request SOAP
        print("\n📡 Preparando request SOAP...")
        soap_request = f'''<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
    <soap:Body>
        <loginCms xmlns="http://ar.gov.afip.dif.FEV1/">
            <in0>{cms_b64}</in0>
        </loginCms>
    </soap:Body>
</soap:Envelope>'''
        
        print(f"✅ SOAP request preparado ({len(soap_request)} caracteres)")
        print(f"SOAP preview: {soap_request[:200]}...")
        
        # Paso 5: Enviar request a WSAA
        print(f"\n🌐 Enviando request a WSAA...")
        wsaa_url = service.wsaa_url
        print(f"URL: {wsaa_url}")
        
        session = crear_session_afip()
        
        # Headers detallados
        headers = {
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPAction': '',
            'Content-Length': str(len(soap_request)),
            'User-Agent': 'InfoFiscal-AFIP/1.0'
        }
        
        print(f"Headers: {headers}")
        
        try:
            response = session.post(
                wsaa_url,
                data=soap_request,
                headers=headers,
                timeout=30
            )
            
            print(f"\n📥 Respuesta recibida:")
            print(f"Status code: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
            print(f"Contenido ({len(response.text)} chars):")
            print("=" * 50)
            print(response.text[:2000])  # Primeros 2000 caracteres
            print("=" * 50)
            
            if response.status_code == 200:
                print("✅ Respuesta HTTP exitosa")
                
                # Intentar parsear respuesta
                print(f"\n🔍 Analizando respuesta...")
                
                # Buscar indicadores de error o éxito
                if "fault" in response.text.lower():
                    print("❌ Respuesta contiene SOAP Fault")
                    
                    # Extraer detalles del error
                    import re
                    fault_match = re.search(r'<faultstring>(.*?)</faultstring>', response.text, re.IGNORECASE | re.DOTALL)
                    if fault_match:
                        print(f"Error SOAP: {fault_match.group(1)}")
                    
                elif "loginticketresponse" in response.text.lower():
                    print("✅ Respuesta contiene LoginTicketResponse")
                    
                    # Intentar extraer token y sign
                    result = service._parsear_respuesta_wsaa(response.text)
                    if result:
                        print(f"✅ Token extraído: {result['token'][:50]}...")
                        print(f"✅ Sign extraído: {result['sign'][:50]}...")
                        return True
                    else:
                        print("❌ No se pudo parsear token/sign")
                        
                else:
                    print("❓ Respuesta no reconocida")
                    
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error enviando request: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal"""
    
    print("🔍 DEBUG WSAA - COMUNICACIÓN CON AFIP")
    print("=" * 50)
    
    # Configurar ambiente de producción
    os.environ['INFOFISCAL_MODE'] = 'production'
    
    print("Configuración:")
    print(f"  CUIT: 20321518045")
    print(f"  Ambiente: PRODUCCIÓN")
    print(f"  URL WSAA: https://wsaa.afip.gov.ar/ws/services/LoginCms")
    print()
    
    exito = debug_wsaa_completo()
    
    print(f"\n🎯 RESULTADO:")
    if exito:
        print("🎉 ¡WSAA FUNCIONANDO!")
        print("La autenticación con AFIP es exitosa")
    else:
        print("⚠️ WSAA CON PROBLEMAS")
        print("Ver detalles arriba para diagnosticar")

if __name__ == "__main__":
    main()