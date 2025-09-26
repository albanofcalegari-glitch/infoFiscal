#!/usr/bin/env python3
"""
Monitor AFIP Simple - Verificación cada 5 minutos
"""

import time
import datetime
import subprocess
import sys
import os

def verificar_servicios():
    """Ejecuta verificar_servicios.py y analiza el resultado"""
    try:
        # Ejecutar el script de verificación
        result = subprocess.run([
            sys.executable, "verificar_servicios.py"
        ], capture_output=True, text=True, encoding='utf-8')
        
        output = result.stdout
        
        # Analizar la salida
        if "✅ SERVICIOS AFIP FUNCIONANDO" in output:
            return True, "¡SERVICIOS ACTIVOS!"
        elif "❌ ERROR EN AUTENTICACIÓN WSAA" in output:
            return False, "Servicios pendientes de activación"
        elif "El CMS no es valido" in output:
            return False, "Servicios aún no habilitados en AFIP"
        else:
            return False, "Estado desconocido"
            
    except Exception as e:
        return False, f"Error: {str(e)}"

def main():
    """Monitor principal"""
    print("\n" + "="*60)
    print("🔍 MONITOR AFIP - Verificación automática cada 5 minutos")
    print("="*60)
    print("CUIT: 20-32151804-5")
    print("Presiona Ctrl+C para detener\n")
    
    verificacion = 1
    
    try:
        while True:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] Verificación #{verificacion}...")
            
            activos, mensaje = verificar_servicios()
            
            if activos:
                print(f"\n🎉 ¡EXCELENTE! {mensaje}")
                print("\n📋 PRÓXIMOS PASOS:")
                print("1. Ejecutar: python cambiar_modo.py produccion")
                print("2. Reiniciar la aplicación Flask")
                print("3. ¡Ya puedes descargar facturas reales!")
                
                # Sonido de notificación
                try:
                    import winsound
                    winsound.Beep(800, 1000)
                except:
                    pass
                    
                break
            else:
                print(f"   ⏳ {mensaje}")
                print(f"   Próxima verificación en 5 minutos...")
                
                # Esperar 5 minutos con contador
                for mins_restantes in range(5, 0, -1):
                    print(f"   ⏰ {mins_restantes} minuto{'s' if mins_restantes != 1 else ''} restante{'s' if mins_restantes != 1 else ''}...")
                    time.sleep(60)  # 1 minuto
                
                verificacion += 1
                print()
                
    except KeyboardInterrupt:
        print("\n🛑 Monitor detenido.")
        print("💡 Verificación manual: python verificar_servicios.py")

if __name__ == "__main__":
    main()