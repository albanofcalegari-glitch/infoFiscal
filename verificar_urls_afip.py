#!/usr/bin/env python3
"""
Verificador simple de URLs de AFIP
"""
import requests

def verificar_url_afip(nombre, url):
    """Verificar una URL específica de AFIP"""
    try:
        print(f"\n🔗 Verificando {nombre}: {url}")
        
        response = requests.get(url, timeout=10)
        
        print(f"   Estado: {response.status_code}")
        print(f"   Tamaño respuesta: {len(response.text)} caracteres")
        
        if response.status_code == 200:
            print(f"   ✅ {nombre} - Conexión exitosa")
            return True
        elif response.status_code == 404:
            print(f"   ❌ {nombre} - Servicio no encontrado (404)")
        else:
            print(f"   ⚠️ {nombre} - Código: {response.status_code}")
            
        return False
        
    except requests.exceptions.Timeout:
        print(f"   ⏱️ {nombre} - Timeout (10s)")
        return False
    except requests.exceptions.ConnectionError:
        print(f"   🚫 {nombre} - Error de conexión")
        return False
    except Exception as e:
        print(f"   ❌ {nombre} - Error: {str(e)}")
        return False

def main():
    print("=" * 60)
    print("🏢 VERIFICADOR DE SERVICIOS AFIP")
    print("=" * 60)
    
    # URLs a verificar
    urls = {
        "WSAA Producción": "https://wsaa.afip.gov.ar/ws/services/LoginCms",
        "WSFE Producción": "https://servicios1.afip.gov.ar/wsfev1/service.asmx",
        "WSAA Testing": "https://wsaahomo.afip.gov.ar/ws/services/LoginCms", 
        "WSFE Testing": "https://wswhomo.afip.gov.ar/wsfev1/service.asmx",
        "AFIP Portal": "https://www.afip.gob.ar"
    }
    
    resultados = {}
    for nombre, url in urls.items():
        resultados[nombre] = verificar_url_afip(nombre, url)
    
    print("\n" + "=" * 60)
    print("📋 RESUMEN DE VERIFICACIÓN")
    print("=" * 60)
    
    for nombre, ok in resultados.items():
        estado = "✅ OK" if ok else "❌ ERROR"
        print(f"{estado:8} | {nombre}")
    
    # Recomendaciones
    print("\n💡 ANÁLISIS:")
    
    if resultados["WSAA Producción"] and resultados["WSFE Producción"]:
        print("✅ Servicios de PRODUCCIÓN disponibles")
    else:
        print("❌ Problemas con servicios de PRODUCCIÓN")
        
    if resultados["WSAA Testing"] and resultados["WSFE Testing"]:
        print("✅ Servicios de TESTING disponibles")
        print("💡 Recomendación: Usar ambiente de testing primero")
    else:
        print("❌ Problemas con servicios de TESTING")

if __name__ == "__main__":
    main()