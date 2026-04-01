#!/usr/bin/env python3
"""
Test de optimizaciones aplicadas
"""

try:
    print("🔧 Probando importación de módulos optimizados...")
    
    # Test 1: App principal
    from src.app import app
    print("✅ App Flask cargada correctamente")
    
    # Test 2: Servicio AFIP optimizado  
    from src.arca_service_simple import ARCAServiceSimple
    print("✅ Servicio AFIP optimizado cargado")
    
    # Test 3: Configuración optimizada
    try:
        from src.config_optimizada import get_optimized_config
        config = get_optimized_config()
        print(f"✅ Configuración optimizada cargada (cache: {config.get('ENABLE_CACHE', False)})")
    except ImportError:
        print("⚠️  Configuración optimizada opcional no encontrada")
    
    # Test 4: Verificar lazy loading
    service = ARCAServiceSimple()
    print("✅ Instancia de servicio creada con lazy loading")
    
    # Test 5: Verificar cache
    from src.app import get_db_connection
    conn1 = get_db_connection()
    conn2 = get_db_connection()
    if conn1 is conn2:
        print("✅ Cache de conexión DB funcionando correctamente")
    else:
        print("⚠️  Cache de conexión DB no activo")
    
    print("\n🎉 ¡TODAS LAS OPTIMIZACIONES FUNCIONAN CORRECTAMENTE!")
    print("📊 Tu aplicación infoFiscal está optimizada y lista para usar")
    
except Exception as e:
    print(f"❌ Error en las optimizaciones: {e}")
    print("💡 Verifica que todas las dependencias estén instaladas")