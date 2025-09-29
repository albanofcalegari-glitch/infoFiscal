"""
Monitor automático para verificar cuando se activen los servicios AFIP
"""

import time
import sys
from pathlib import Path
from datetime import datetime

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def verificar_servicios_cada_minuto():
    """Verificar servicios cada minuto hasta que se activen"""
    
    print("🔄 MONITOR DE SERVICIOS AFIP")
    print("============================")
    print("Este script verificará automáticamente cada 2 minutos")
    print("si los servicios web se han activado en AFIP.")
    print()
    print("Presiona Ctrl+C para detener")
    print()
    
    intentos = 0
    max_intentos = 30  # 1 hora máximo
    
    while intentos < max_intentos:
        try:
            intentos += 1
            hora_actual = datetime.now().strftime("%H:%M:%S")
            
            print(f"[{hora_actual}] Intento {intentos}/{max_intentos} - Verificando servicios...")
            
            # Importar aquí para evitar errores de imports al inicio
            from arca_service_simple import ARCAServiceSimple
            
            # Configuración
            cuit = "20321518045"
            cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
            key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
            
            # Crear servicio y probar
            service = ARCAServiceSimple(cuit, cert_path, key_path, testing=False)  # PRODUCCION
            
            if service.authenticate_wsaa():
                print()
                print("🎉 ¡SERVICIOS ACTIVADOS!")
                print("=" * 50)
                print("✅ Los servicios web de AFIP están funcionando")
                print("✅ Ya podés descargar facturas reales")
                print()
                print("Ejecutar para probar:")
                print("python verificar_servicios.py")
                return True
            else:
                print("   ⏳ Servicios aún no activados...")
                
        except KeyboardInterrupt:
            print()
            print("⏹️ Monitoreo detenido por el usuario")
            return False
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
        
        if intentos < max_intentos:
            print("   ⏱️ Esperando 2 minutos antes del próximo intento...")
            print()
            time.sleep(120)  # Esperar 2 minutos
    
    print("⏰ Tiempo de espera agotado")
    print("Los servicios pueden tardar más de 1 hora en activarse")
    print("Recomendación: Verificar manualmente en AFIP o llamar al 0800-999-2347")
    return False

if __name__ == "__main__":
    print("ANTES DE EJECUTAR ESTE MONITOR:")
    print("1. ¿Ya habilitaste los servicios en AFIP? (s/n): ", end="")
    
    try:
        respuesta = input().lower().strip()
        if respuesta in ['s', 'si', 'sí', 'y', 'yes']:
            verificar_servicios_cada_minuto()
        else:
            print()
            print("📋 PRIMERO COMPLETÁ ESTOS PASOS:")
            print("1. Seguir GUIA_SERVICIOS_AFIP.txt")
            print("2. Habilitar servicios en AFIP")
            print("3. Ejecutar este monitor nuevamente")
            
    except KeyboardInterrupt:
        print("\nSaliendo...")
        sys.exit(0)