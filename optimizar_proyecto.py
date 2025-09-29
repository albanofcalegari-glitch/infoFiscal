"""
Script de optimización y limpieza para infoFiscal
Elimina archivos innecesarios y optimiza el proyecto
"""

import os
import shutil
from pathlib import Path

def limpiar_proyecto():
    """Eliminar archivos y directorios innecesarios"""
    
    base_dir = Path(__file__).parent
    
    # Archivos y directorios a eliminar
    archivos_eliminar = [
        # Cache de Python
        '__pycache__',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.Python',
        
        # Archivos temporales
        '*.tmp',
        '*.temp',
        'temp_*',
        
        # Logs antiguos
        '*.log',
        '*.log.*',
        
        # Archivos de backup
        '*.bak',
        '*.backup',
        '*~',
        
        # Archivos de IDE
        '.vscode/settings.json.bak',
        '*.swp',
        '*.swo',
        
        # Archivos específicos del proyecto que son duplicados o legacy
        'src/_deprecated_*',
    ]
    
    # Directorios a limpiar recursivamente
    directorios_limpiar = [
        base_dir / '__pycache__',
        base_dir / 'src' / '__pycache__',
        base_dir / 'debug_wsaa' / '*.debug_summary.txt',  # Mantener solo archivos esenciales
    ]
    
    archivos_eliminados = 0
    espacio_liberado = 0
    
    print("🧹 Iniciando limpieza del proyecto infoFiscal...")
    print("=" * 50)
    
    # Limpiar archivos por patrón
    for patron in archivos_eliminar:
        if '*' in patron:
            # Es un patrón, buscar archivos coincidentes
            import glob
            archivos_encontrados = glob.glob(str(base_dir / '**' / patron), recursive=True)
            for archivo in archivos_encontrados:
                try:
                    path_archivo = Path(archivo)
                    if path_archivo.is_file():
                        tamaño = path_archivo.stat().st_size
                        path_archivo.unlink()
                        print(f"🗑️  Eliminado: {path_archivo.name} ({tamaño} bytes)")
                        archivos_eliminados += 1
                        espacio_liberado += tamaño
                    elif path_archivo.is_dir():
                        shutil.rmtree(path_archivo)
                        print(f"📁 Eliminado directorio: {path_archivo.name}")
                except Exception as e:
                    print(f"⚠️  Error eliminando {archivo}: {e}")
        else:
            # Es un archivo o directorio específico
            path_item = base_dir / patron
            try:
                if path_item.exists():
                    if path_item.is_file():
                        tamaño = path_item.stat().st_size
                        path_item.unlink()
                        print(f"🗑️  Eliminado: {patron} ({tamaño} bytes)")
                        archivos_eliminados += 1
                        espacio_liberado += tamaño
                    elif path_item.is_dir():
                        shutil.rmtree(path_item)
                        print(f"📁 Eliminado directorio: {patron}")
            except Exception as e:
                print(f"⚠️  Error eliminando {patron}: {e}")
    
    # Limpiar directorios específicos
    debug_dir = base_dir / 'debug_wsaa'
    if debug_dir.exists():
        archivos_debug = list(debug_dir.glob('*.debug_summary.txt'))
        archivos_debug.extend(list(debug_dir.glob('*.decode_error.txt')))
        
        for archivo in archivos_debug:
            try:
                tamaño = archivo.stat().st_size
                archivo.unlink()
                print(f"🗑️  Debug limpiado: {archivo.name} ({tamaño} bytes)")
                archivos_eliminados += 1
                espacio_liberado += tamaño
            except Exception as e:
                print(f"⚠️  Error limpiando debug {archivo}: {e}")
    
    print("\n" + "=" * 50)
    print(f"✅ Limpieza completada:")
    print(f"   📁 Archivos eliminados: {archivos_eliminados}")
    print(f"   💾 Espacio liberado: {espacio_liberado:,} bytes ({espacio_liberado/1024:.1f} KB)")
    
    return archivos_eliminados, espacio_liberado

def optimizar_estructura():
    """Optimizar la estructura de archivos del proyecto"""
    
    base_dir = Path(__file__).parent
    
    print("\n🔧 Optimizando estructura del proyecto...")
    print("=" * 50)
    
    optimizaciones = []
    
    # Verificar si existe el archivo optimizado y sugerir reemplazo
    archivo_original = base_dir / 'src' / 'arca_service_simple.py'
    archivo_optimizado = base_dir / 'src' / 'arca_service_optimized.py'
    
    if archivo_optimizado.exists() and archivo_original.exists():
        tamaño_original = archivo_original.stat().st_size
        tamaño_optimizado = archivo_optimizado.stat().st_size
        
        print(f"📊 arca_service_simple.py: {tamaño_original:,} bytes")
        print(f"📊 arca_service_optimized.py: {tamaño_optimizado:,} bytes")
        
        if tamaño_optimizado < tamaño_original:
            ahorro = tamaño_original - tamaño_optimizado
            print(f"💡 Potencial ahorro: {ahorro:,} bytes ({ahorro/1024:.1f} KB)")
            optimizaciones.append(f"Reemplazar servicio AFIP (ahorro: {ahorro/1024:.1f} KB)")
    
    # Verificar monitor optimizado
    monitor_original = base_dir / 'monitor_afip.py'
    monitor_optimizado = base_dir / 'monitor_afip_optimized.py'
    
    if monitor_optimizado.exists() and monitor_original.exists():
        tamaño_original = monitor_original.stat().st_size
        tamaño_optimizado = monitor_optimizado.stat().st_size
        
        if tamaño_optimizado <= tamaño_original:  # Permitir igual tamaño si está optimizado
            print(f"📊 Monitor AFIP optimizado disponible")
            optimizaciones.append("Monitor AFIP con lazy loading")
    
    # Verificar archivos de configuración
    config_optimizada = base_dir / 'src' / 'config_optimizada.py'
    if config_optimizada.exists():
        print(f"📊 Configuración optimizada disponible")
        optimizaciones.append("Configuración de rendimiento centralizada")
    
    if optimizaciones:
        print(f"✅ Optimizaciones disponibles:")
        for opt in optimizaciones:
            print(f"   ✓ {opt}")
    else:
        print("ℹ️  No se encontraron optimizaciones adicionales")
    
    return len(optimizaciones)

def generar_reporte_proyecto():
    """Generar reporte del estado del proyecto"""
    
    base_dir = Path(__file__).parent
    
    print(f"\n📋 Reporte del proyecto infoFiscal")
    print("=" * 50)
    
    # Contar archivos por tipo
    archivos_python = list(base_dir.glob('**/*.py'))
    archivos_html = list(base_dir.glob('**/*.html'))
    archivos_css = list(base_dir.glob('**/*.css'))
    archivos_txt = list(base_dir.glob('**/*.txt'))
    archivos_md = list(base_dir.glob('**/*.md'))
    
    # Calcular tamaños
    tamaño_python = sum(f.stat().st_size for f in archivos_python)
    tamaño_html = sum(f.stat().st_size for f in archivos_html)
    tamaño_css = sum(f.stat().st_size for f in archivos_css)
    tamaño_total = tamaño_python + tamaño_html + tamaño_css
    
    print(f"📄 Archivos Python: {len(archivos_python)} ({tamaño_python/1024:.1f} KB)")
    print(f"🌐 Archivos HTML: {len(archivos_html)} ({tamaño_html/1024:.1f} KB)")
    print(f"🎨 Archivos CSS: {len(archivos_css)} ({tamaño_css/1024:.1f} KB)")
    print(f"📝 Archivos documentación: {len(archivos_txt + archivos_md)}")
    print(f"📦 Tamaño total código: {tamaño_total/1024:.1f} KB")
    
    # Verificar optimizaciones aplicadas
    optimizaciones_detectadas = []
    
    if (base_dir / 'src' / 'config_optimizada.py').exists():
        optimizaciones_detectadas.append("✅ Configuración optimizada")
    
    if any('lazy' in f.read_text(encoding='utf-8').lower() for f in archivos_python[:3]):
        optimizaciones_detectadas.append("✅ Lazy loading implementado")
    
    requirements_file = base_dir / 'requirements.txt'
    if requirements_file.exists():
        content = requirements_file.read_text(encoding='utf-8')
        if len(content.split('\\n')) < 10:  # Pocas dependencias
            optimizaciones_detectadas.append("✅ Dependencias minimizadas")
    
    print(f"\\n🚀 Optimizaciones detectadas: {len(optimizaciones_detectadas)}")
    for opt in optimizaciones_detectadas:
        print(f"   {opt}")
    
    return {
        'archivos_python': len(archivos_python),
        'archivos_html': len(archivos_html),
        'tamaño_total_kb': tamaño_total/1024,
        'optimizaciones': len(optimizaciones_detectadas)
    }

def main():
    """Función principal del script de optimización"""
    
    print("🚀 OPTIMIZADOR INFOFISCAL")
    print("========================")
    print("Este script optimiza el proyecto para mejor rendimiento\\n")
    
    # Paso 1: Limpieza
    archivos_eliminados, espacio_liberado = limpiar_proyecto()
    
    # Paso 2: Optimización de estructura
    optimizaciones_disponibles = optimizar_estructura()
    
    # Paso 3: Reporte final
    reporte = generar_reporte_proyecto()
    
    # Resumen final
    print(f"\\n🎯 RESUMEN DE OPTIMIZACIÓN")
    print("=" * 50)
    print(f"🗑️  Archivos limpiados: {archivos_eliminados}")
    print(f"💾 Espacio liberado: {espacio_liberado/1024:.1f} KB")
    print(f"🔧 Optimizaciones disponibles: {optimizaciones_disponibles}")
    print(f"📦 Tamaño final del proyecto: {reporte['tamaño_total_kb']:.1f} KB")
    
    # Recomendaciones
    print(f"\\n💡 RECOMENDACIONES:")
    
    if reporte['tamaño_total_kb'] > 500:
        print("   ⚠️  El proyecto sigue siendo grande. Considera usar archivos optimizados.")
    else:
        print("   ✅ Tamaño del proyecto optimizado correctamente.")
    
    if reporte['optimizaciones'] >= 3:
        print("   ✅ Buen nivel de optimizaciones aplicadas.")
    else:
        print("   💡 Puedes aplicar más optimizaciones usando los archivos *_optimized.py")
    
    print(f"\\n🏁 Optimización completada. ¡Tu proyecto infoFiscal está más ligero!")

if __name__ == "__main__":
    main()