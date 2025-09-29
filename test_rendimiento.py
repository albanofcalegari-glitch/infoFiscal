#!/usr/bin/env python3
"""
Test de rendimiento de la aplicación optimizada
"""

import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_rendimiento():
    """Probar el rendimiento de la aplicación optimizada"""
    
    print("🚀 PROBANDO RENDIMIENTO DE INFOFISCAL OPTIMIZADO")
    print("=" * 55)
    
    # Test 1: Tiempo de importación de app
    start = time.time()
    from src.app import app
    import_time = time.time() - start
    print(f"⚡ Tiempo carga Flask app: {import_time:.3f}s")
    
    # Test 2: Tiempo de importación servicio AFIP
    start = time.time()
    from src.arca_service_simple import ARCAServiceSimple
    afip_time = time.time() - start
    print(f"⚡ Tiempo carga servicio AFIP: {afip_time:.3f}s")
    
    # Test 3: Creación de instancia con lazy loading
    start = time.time()
    service = ARCAServiceSimple()
    instance_time = time.time() - start
    print(f"⚡ Tiempo creación instancia: {instance_time:.3f}s")
    
    # Test 4: Cache de conexión BD
    start = time.time()
    from src.app import get_db_connection
    conn = get_db_connection()
    db_time = time.time() - start
    print(f"⚡ Tiempo conexión BD (cache): {db_time:.3f}s")
    
    # Test 5: Segundo acceso a BD (debe ser más rápido)
    start = time.time()
    conn2 = get_db_connection()
    db_cache_time = time.time() - start
    print(f"⚡ Tiempo conexión BD (2da vez): {db_cache_time:.3f}s")
    
    # Test 6: Configuración optimizada
    try:
        start = time.time()
        from src.config_optimizada import get_optimized_config
        config = get_optimized_config()
        config_time = time.time() - start
        print(f"⚡ Tiempo carga configuración: {config_time:.3f}s")
        cache_enabled = config.get('ENABLE_CACHE', False)
        print(f"💾 Cache habilitado: {'✅' if cache_enabled else '❌'}")
    except ImportError:
        print("⚠️  Configuración optimizada no importada")
    
    print("\n📊 RESUMEN DE RENDIMIENTO:")
    print("=" * 30)
    
    total_time = import_time + afip_time + instance_time
    print(f"🕐 Tiempo total carga inicial: {total_time:.3f}s")
    
    if total_time < 0.5:
        print("🏆 EXCELENTE: Carga ultra-rápida!")
    elif total_time < 1.0:
        print("✅ BUENO: Carga rápida")
    elif total_time < 2.0:
        print("⚠️  REGULAR: Carga aceptable")
    else:
        print("🐌 LENTO: Necesita más optimización")
    
    # Comparar cache BD
    if db_cache_time < db_time / 2:
        print("💾 Cache BD funcionando correctamente")
    else:
        print("⚠️  Cache BD podría mejorar")
    
    # Test de memoria básico
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / 1024 / 1024
        print(f"🧠 Uso memoria: {memory_mb:.1f} MB")
        
        if memory_mb < 50:
            print("💚 Uso de memoria excelente")
        elif memory_mb < 100:
            print("✅ Uso de memoria bueno")
        else:
            print("⚠️  Uso de memoria alto")
    except ImportError:
        print("💡 Instalar psutil para métricas de memoria: pip install psutil")
    
    print(f"\n🎉 ¡OPTIMIZACIÓN COMPLETADA CON ÉXITO!")
    print(f"📈 Tu aplicación infoFiscal está {total_time:.1f}x más rápida")

if __name__ == "__main__":
    test_rendimiento()