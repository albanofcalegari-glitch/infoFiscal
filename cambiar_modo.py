"""
Script para cambiar entre modo simulación y producción
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def activar_modo_produccion():
    """Activar modo de producción en la aplicación"""
    
    print("=== ACTIVANDO MODO PRODUCCIÓN ===")
    
    # Leer archivo actual
    app_file = Path("src/app.py")
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cambiar modo_real=False a modo_real=True
    if 'modo_real=False' in content:
        content = content.replace('modo_real=False', 'modo_real=True')
        
        # Escribir archivo actualizado
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Modo producción ACTIVADO")
        print("   La aplicación ahora usará servicios reales de AFIP")
        print("   Reiniciar Flask para aplicar cambios")
        return True
    elif 'modo_real=True' in content:
        print("ℹ️ Modo producción YA está activado")
        return True
    else:
        print("❌ No se pudo cambiar el modo")
        return False

def activar_modo_simulacion():
    """Activar modo de simulación en la aplicación"""
    
    print("=== ACTIVANDO MODO SIMULACIÓN ===")
    
    # Leer archivo actual
    app_file = Path("src/app.py")
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cambiar modo_real=True a modo_real=False
    if 'modo_real=True' in content:
        content = content.replace('modo_real=True', 'modo_real=False')
        
        # Escribir archivo actualizado
        with open(app_file, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print("✅ Modo simulación ACTIVADO")
        print("   La aplicación usará facturas de ejemplo")
        print("   Reiniciar Flask para aplicar cambios")
        return True
    elif 'modo_real=False' in content:
        print("ℹ️ Modo simulación YA está activado")
        return True
    else:
        print("❌ No se pudo cambiar el modo")
        return False

def verificar_modo_actual():
    """Verificar qué modo está activo actualmente"""
    
    app_file = Path("src/app.py")
    with open(app_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'modo_real=True' in content:
        return "PRODUCCIÓN"
    elif 'modo_real=False' in content:
        return "SIMULACIÓN"
    else:
        return "DESCONOCIDO"

if __name__ == "__main__":
    modo_actual = verificar_modo_actual()
    print(f"Modo actual: {modo_actual}")
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == "produccion":
            activar_modo_produccion()
        elif comando == "simulacion":
            activar_modo_simulacion()
        elif comando == "verificar":
            from verificar_servicios import verificar_servicios_afip
            verificar_servicios_afip()
        else:
            print("Comandos disponibles:")
            print("  python cambiar_modo.py produccion")
            print("  python cambiar_modo.py simulacion") 
            print("  python cambiar_modo.py verificar")
    else:
        print("\nComandos disponibles:")
        print("  python cambiar_modo.py produccion    # Activar servicios reales AFIP")
        print("  python cambiar_modo.py simulacion    # Activar facturas de ejemplo")
        print("  python cambiar_modo.py verificar     # Verificar estado servicios AFIP")