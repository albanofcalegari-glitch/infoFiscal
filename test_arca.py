"""
Script de prueba para verificar conexión con AFIP/ARCA
"""

import sys
import os
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

try:
    from arca_service import ARCAService
except ImportError as e:
    print(f"Error importing ARCAService: {e}")
    print("Verificando instalación de zeep...")
    import subprocess
    result = subprocess.run([sys.executable, "-c", "import zeep; print('zeep OK')"], capture_output=True, text=True)
    if result.returncode != 0:
        print("⚠️ zeep no está instalado correctamente")
        print("Ejecutar: pip install zeep lxml")
    sys.exit(1)

def test_arca_connection():
    """Probar conexión con AFIP"""
    
    # Configuración
    cuit = "20321518045"
    cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
    key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
    
    print("=== PRUEBA DE CONEXIÓN ARCA/AFIP ===")
    print(f"CUIT: {cuit}")
    print(f"Certificado: {cert_path}")
    print(f"Clave: {key_path}")
    print()
    
    # Verificar archivos
    if not cert_path.exists():
        print("❌ ERROR: No se encontró certificado.crt")
        return False
        
    if not key_path.exists():
        print("❌ ERROR: No se encontró clave_privada.key")
        return False
        
    print("✅ Archivos de certificados encontrados")
    
    try:
        # Crear servicio (modo testing)
        print("🔄 Creando servicio ARCA...")
        service = ARCAService(cuit, cert_path, key_path, testing=True)
        
        print("🔄 Intentando autenticación WSAA...")
        if service.authenticate():
            print("✅ AUTENTICACIÓN EXITOSA!")
            print(f"Token obtenido: {service.token[:50]}...")
            print(f"Sign obtenido: {service.sign[:50]}...")
            
            # Probar consulta de facturas (último mes)
            print("🔄 Consultando facturas del último mes...")
            from datetime import datetime, timedelta
            fecha_desde = (datetime.now() - timedelta(days=30)).strftime('%Y%m%d')
            fecha_hasta = datetime.now().strftime('%Y%m%d')
            
            facturas = service.get_facturas_emitidas(fecha_desde, fecha_hasta)
            print("✅ CONSULTA DE FACTURAS EXITOSA!")
            print(f"Respuesta recibida: {type(facturas)}")
            
            return True
            
        else:
            print("❌ ERROR en autenticación")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("Posibles causas:")
        print("- Servicios web no habilitados en AFIP")
        print("- Certificado no válido o no asociado al CUIT")
        print("- Problemas de conectividad")
        return False

if __name__ == "__main__":
    success = test_arca_connection()
    
    if success:
        print("\n🎉 ¡CONEXIÓN ARCA FUNCIONANDO!")
        print("Ya podés usar la descarga de facturas en la web app")
    else:
        print("\n⚠️  REVISAR CONFIGURACIÓN")
        print("1. Verificar que los servicios web estén habilitados en AFIP")
        print("2. Confirmar que el certificado esté asociado al CUIT correcto")
        print("3. Revisar conectividad a internet")