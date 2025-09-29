#!/usr/bin/env python3
"""
Monitor AFIP - Verificación automática de servicios (OPTIMIZADO)
Verifica cada 5 minutos si los servicios AFIP están activos
Versión optimizada con lazy loading para mejor rendimiento
"""

import time
import sys
import os
from pathlib import Path

# Agregar el directorio src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Cache global para módulos pesados
_modules_cache = {}

def get_module(name):
    """Lazy loading universal de módulos"""
    if name not in _modules_cache:
        if name == 'datetime':
            import datetime
            _modules_cache[name] = datetime
            
        elif name == 'colorama':
            try:
                import colorama
                from colorama import Fore, Style
                colorama.init()
                _modules_cache[name] = {'Fore': Fore, 'Style': Style}
            except ImportError:
                # Fallback sin colorama para compatibilidad
                class MockColor:
                    CYAN = YELLOW = WHITE = RED = GREEN = ''
                    RESET_ALL = BRIGHT = ''
                
                _modules_cache[name] = {
                    'Fore': MockColor(), 
                    'Style': MockColor()
                }
                
        elif name == 'arca_service':
            from arca_service_simple import ARCAServiceSimple
            _modules_cache[name] = ARCAServiceSimple
            
    return _modules_cache[name]

def print_header():
    """Imprime el header del monitor (optimizado)"""
    colors = get_module('colorama')
    Fore, Style = colors['Fore'], colors['Style']
    
    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}🔍 MONITOR AFIP - VERIFICACIÓN AUTOMÁTICA (OPTIMIZADO)")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.YELLOW}CUIT: 20-32151804-5")
    print(f"Verificando cada 5 minutos...{Style.RESET_ALL}")
    print(f"{Fore.RED}Presiona Ctrl+C para detener{Style.RESET_ALL}\n")

def verificar_servicios():
    """Verifica si los servicios están activos (optimizado)"""
    try:
        # Lazy loading del servicio AFIP
        ARCAServiceSimple = get_module('arca_service')
        service = ARCAServiceSimple(testing=False)
        
        # Intentar autenticar
        ticket = service.autenticar()
        
        if ticket and 'token' in ticket:
            return True, "✅ SERVICIOS ACTIVOS - ¡LISTO PARA PRODUCCIÓN!"
        else:
            return False, "⏳ Servicios aún no activos"
            
    except Exception as e:
        error_msg = str(e)
        if "CMS no es válido" in error_msg:
            return False, "⏳ Servicios pendientes de activación"
        elif "No se pudo conectar" in error_msg:
            return False, "🌐 Problema de conexión"
        else:
            return False, f"❌ Error: {error_msg[:50]}..."

def main():
    """Función principal del monitor (optimizada)"""
    print_header()
    
    verificacion_num = 1
    
    try:
        while True:
            # Lazy loading de módulos cuando se necesitan
            datetime = get_module('datetime')
            colors = get_module('colorama')
            Fore, Style = colors['Fore'], colors['Style']
            
            # Timestamp actual
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            print(f"{Fore.WHITE}[{timestamp}] Verificación #{verificacion_num}...{Style.RESET_ALL}")
            
            # Verificar servicios
            activos, mensaje = verificar_servicios()
            
            if activos:
                # ¡SERVICIOS ACTIVOS!
                print(f"\n{Fore.GREEN}{Style.BRIGHT}🎉 ¡EXCELENTE! {mensaje}")
                print(f"\n{Fore.YELLOW}📋 PRÓXIMOS PASOS:")
                print(f"{Fore.WHITE}1. Ejecutar: python cambiar_modo.py produccion")
                print(f"{Fore.WHITE}2. Reiniciar la aplicación Flask")
                print(f"{Fore.WHITE}3. ¡Ya puedes descargar facturas reales!{Style.RESET_ALL}")
                
                # Sonido de notificación optimizado (si está disponible)
                try:
                    import winsound
                    for freq in [800, 1000]:
                        winsound.Beep(freq, 400)
                except ImportError:
                    print("🔔 ¡NOTIFICACIÓN SONORA!")
                except:
                    pass
                
                break
                
            else:
                # Servicios aún no activos
                print(f"{Fore.YELLOW}   {mensaje}")
                print(f"{Fore.WHITE}   Próxima verificación en 5 minutos...{Style.RESET_ALL}")
                
                # Esperar optimizado (mostrar progreso cada minuto)
                for i in range(300, 0, -1):
                    if i % 60 == 0:  # Mostrar cada minuto
                        mins = i // 60
                        plural_min = 's' if mins != 1 else ''
                        plural_rest = 's' if mins != 1 else ''
                        print(f"{Fore.CYAN}   ⏰ {mins} minuto{plural_min} restante{plural_rest}...{Style.RESET_ALL}")
                    time.sleep(1)
                
                verificacion_num += 1
                print()  # Línea en blanco
                
    except KeyboardInterrupt:
        colors = get_module('colorama')
        Fore, Style = colors['Fore'], colors['Style']
        print(f"\n{Fore.RED}🛑 Monitor detenido por el usuario.{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}💡 Puedes verificar manualmente con: python verificar_servicios.py{Style.RESET_ALL}")
        
    except Exception as e:
        colors = get_module('colorama')
        Fore, Style = colors['Fore'], colors['Style']
        print(f"\n{Fore.RED}❌ Error en el monitor: {e}{Style.RESET_ALL}")
        
    finally:
        try:
            colors = get_module('colorama')
            Fore, Style = colors['Fore'], colors['Style']
            print(f"\n{Fore.CYAN}👋 Monitor AFIP finalizado.{Style.RESET_ALL}")
        except:
            print("\n👋 Monitor AFIP finalizado.")

if __name__ == "__main__":
    main()