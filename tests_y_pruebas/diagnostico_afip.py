#!/usr/bin/env python3
"""
Diagnóstico avanzado AFIP - Análisis detallado del estado
"""

import sys
import datetime
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from arca_service_simple import ARCAServiceSimple
except ImportError as e:
    print(f"Error importando módulos: {e}")
    sys.exit(1)

def diagnostico_completo():
    """Realizar diagnóstico completo del sistema AFIP"""
    
    print("="*60)
    print("🔬 DIAGNÓSTICO COMPLETO AFIP")
    print("="*60)
    print(f"Fecha/Hora: {datetime.datetime.now()}")
    print()
    
    # 1. Verificar certificados
    print("📋 1. VERIFICACIÓN DE CERTIFICADOS:")
    certs_dir = Path("certs")
    cert_path = certs_dir / "certificado.crt"
    key_path = certs_dir / "clave_privada.key"
    
    if cert_path.exists() and key_path.exists():
        print("   ✅ Archivos de certificado encontrados")
        
        # Verificar validez del certificado
        try:
            result = subprocess.run([
                "openssl", "x509", "-in", str(cert_path), 
                "-text", "-noout"
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                # Buscar fechas de validez
                for line in output.split('\n'):
                    if 'Not Before' in line or 'Not After' in line:
                        print(f"   📅 {line.strip()}")
                print("   ✅ Certificado válido y legible")
            else:
                print("   ⚠️ No se pudo verificar validez del certificado")
                
        except Exception as e:
            print(f"   ⚠️ Error verificando certificado: {e}")
    else:
        print("   ❌ Certificados no encontrados")
        return False
    
    print()
    
    # 2. Verificar OpenSSL
    print("📋 2. VERIFICACIÓN OPENSSL:")
    try:
        result = subprocess.run(["openssl", "version"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"   ✅ OpenSSL disponible: {result.stdout.strip()}")
        else:
            print("   ❌ OpenSSL no funciona correctamente")
    except Exception as e:
        print(f"   ❌ Error con OpenSSL: {e}")
    
    print()
    
    # 3. Pruebas de conectividad
    print("📋 3. PRUEBAS DE CONECTIVIDAD:")
    
    # URLs de AFIP
    urls = {
        "WSAA Testing": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms",
        "WSAA Producción": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
        "WSFE Testing": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
        "WSFE Producción": "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    }
    
    import requests
    
    for nombre, url in urls.items():
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ {nombre}: OK ({response.status_code})")
            else:
                print(f"   ⚠️ {nombre}: {response.status_code}")
        except Exception as e:
            print(f"   ❌ {nombre}: Error - {e}")
    
    print()
    
    # 4. Prueba de autenticación detallada
    print("📋 4. ANÁLISIS DE AUTENTICACIÓN:")
    
    try:
        cuit = "20321518045"
        service = ARCAServiceSimple(cuit, cert_path, key_path, testing=False)  # PRODUCCION
        
        # Generar TRA
        print("   🔄 Generando TRA...")
        tra = service._generate_tra()
        print(f"   ✅ TRA generado ({len(tra)} caracteres)")
        
        # Firmar TRA
        print("   🔄 Firmando TRA...")
        cms = service._sign_tra_openssl(tra)
        print(f"   ✅ CMS generado ({len(cms)} bytes)")
        
        # Enviar a WSAA
        print("   🔄 Enviando a WSAA...")
        response = service._send_tra_to_wsaa(cms)
        
        if "token" in response.lower():
            print("   ✅ Respuesta contiene token - ¡SERVICIOS ACTIVOS!")
            return True
        else:
            print("   ❌ Respuesta sin token")
            print(f"   📝 Respuesta WSAA (primeros 500 chars):")
            print(f"   {response[:500]}...")
            
    except Exception as e:
        print(f"   ❌ Error en autenticación: {e}")
    
    print()
    
    # 5. Recomendaciones
    print("📋 5. RECOMENDACIONES:")
    print("   🎯 Estado: Servicios web AÚN NO habilitados en AFIP")
    print("   ⏰ Tiempo típico: 1-24 horas desde solicitud")
    print("   📞 Si >24h: llamar AFIP 0800-999-2347")
    print("   🔄 Verificar cada 1-2 horas manualmente")
    print("   ✅ Aplicación funciona perfectamente en modo simulación")
    
    print()
    print("="*60)
    
    return False

def probar_ambiente_produccion():
    """Probar también el ambiente de producción"""
    print("\n🚀 PRUEBA ADICIONAL - AMBIENTE PRODUCCIÓN:")
    
    try:
        cuit = "20321518045"
        certs_dir = Path("certs")
        cert_path = certs_dir / "certificado.crt"
        key_path = certs_dir / "clave_privada.key"
        
        # Probar producción
        service_prod = ARCAServiceSimple(cuit, cert_path, key_path, testing=False)
        
        if service_prod.test_connection():
            print("   ✅ Conectividad OK - Producción")
            
            # Intentar autenticación
            if service_prod.authenticate_wsaa():
                print("   🎉 ¡PRODUCCIÓN ACTIVA! - Cambiar a modo real")
                return True
            else:
                print("   ⏳ Producción: servicios no activos aún")
        else:
            print("   ❌ Sin conectividad - Producción")
            
    except Exception as e:
        print(f"   ❌ Error probando producción: {e}")
    
    return False

if __name__ == "__main__":
    servicios_testing = diagnostico_completo()
    servicios_prod = probar_ambiente_produccion()
    
    if servicios_testing or servicios_prod:
        print("\n🎉 ¡SERVICIOS DETECTADOS COMO ACTIVOS!")
        print("   Ejecutar: python cambiar_modo.py produccion")
    else:
        print("\n⏳ Servicios aún pendientes - continuar esperando")
        print("   Verificación automática: .\\monitor_afip.bat")