"""
Script para verificar si los servicios WSFE están habilitados en AFIP
"""

import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from arca_service_simple import ARCAServiceSimple

def verificar_servicios_afip():
    """Verificar estado de servicios web en AFIP"""
    
    cuit = "20321518045"
    cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
    key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
    
    print("=== VERIFICACIÓN SERVICIOS AFIP ===")
    print(f"CUIT: {cuit}")
    print()
    
    if not cert_path.exists() or not key_path.exists():
        print("❌ Certificados no encontrados")
        return False
    
    print("✅ Certificados OK")
    
    try:
        # Crear servicio optimizado
        service = ARCAServiceSimple(cuit, cert_path, key_path, testing=False)  # PRODUCCION
        
        # Verificar conectividad básica
        from arca_service_simple import verificar_conexion_afip
        conectividad, mensaje = verificar_conexion_afip()
        if not conectividad:
            print(f"❌ Sin conectividad a AFIP: {mensaje}")
            return False
        
        # Intentar autenticación WSAA
        print("🔄 Probando autenticación WSAA...")
        auth_data = service.autenticar()
        if auth_data and 'token' in auth_data:
            print("✅ AUTENTICACIÓN WSAA EXITOSA!")
            print("✅ SERVICIOS WEB HABILITADOS CORRECTAMENTE")
            
            # Probar consulta WSFE básica
            print("🔄 Probando consulta WSFE...")
            ultimo = service.wsfe_fecomp_ultimo_autorizado(1, 1)
            
            if ultimo is not None:
                print("✅ CONSULTA WSFE EXITOSA!")
                print(f"Último comprobante autorizado: {ultimo}")
                return True
            else:
                print("⚠️ WSFE responde pero sin datos o sin permisos")
                return True
                
        else:
            print("❌ ERROR EN AUTENTICACIÓN WSAA")
            print("\nPOSIBLES CAUSAS:")
            print("1. Servicios web NO habilitados en AFIP")
            print("2. Certificado no asociado al CUIT")
            print("3. OpenSSL no instalado correctamente")
            print("4. Error en firma del TRA")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    exito = verificar_servicios_afip()
    
    print("\n" + "="*50)
    if exito:
        print("🎉 SERVICIOS AFIP FUNCIONANDO!")
        print("Ya podés usar descargas reales de facturas")
    else:
        print("⚠️ SERVICIOS AFIP NO DISPONIBLES")
        print("\nPRÓXIMOS PASOS:")
        print("1. Ir a AFIP → Administrador de Relaciones")
        print("2. Habilitar servicio 'wsfe' para tu CUIT")
        print("3. Asociar el certificado al servicio")
        print("4. Esperar activación (puede tomar horas)")
        print("5. Ejecutar este script nuevamente")
        print("\nMientras tanto, la app funciona en modo simulación")