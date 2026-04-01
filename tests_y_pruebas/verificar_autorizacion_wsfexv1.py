#!/usr/bin/env python3
"""
VERIFICADOR DE AUTORIZACIÓN WSFEXv1
===================================

Este script te ayuda a verificar si ya tenes autorización para WSFEXv1
y te guía en el proceso de solicitud si aún no la tenes.
"""

import sys
sys.path.append('src')

from wsfexv1_client import WSFEXv1Client

def verificar_autorizacion_actual():
    """Verificar estado actual de autorización WSFEXv1"""
    print("🔍 VERIFICANDO AUTORIZACIÓN WSFEXv1")
    print("=" * 50)
    
    cuit = input("📋 Ingresá tu CUIT (11 dígitos): ").strip()
    
    if len(cuit) != 11 or not cuit.isdigit():
        print("❌ CUIT inválido. Debe tener 11 dígitos.")
        return False
    
    print(f"\n🎯 Verificando CUIT: {cuit}")
    
    # Probar homologación primero
    print(f"\n1️⃣ PROBANDO HOMOLOGACIÓN...")
    homolog_ok = probar_ambiente(cuit, 'homologacion')
    
    # Probar producción
    print(f"\n2️⃣ PROBANDO PRODUCCIÓN...")  
    prod_ok = probar_ambiente(cuit, 'prod')
    
    # Resumen
    print(f"\n" + "="*50)
    print("📊 RESUMEN DE AUTORIZACIÓN")
    print("="*50)
    
    if homolog_ok and prod_ok:
        print("🎉 ¡EXCELENTE! Tenes autorización completa")
        print("✅ Homologación: AUTORIZADO")
        print("✅ Producción: AUTORIZADO")
        print("🚀 Podes usar WSFEXv1 en ambos ambientes")
        return True
        
    elif homolog_ok and not prod_ok:
        print("⚠️ Autorización parcial")
        print("✅ Homologación: AUTORIZADO") 
        print("❌ Producción: NO AUTORIZADO")
        print("💡 Necesitas solicitar acceso a producción")
        return False
        
    elif not homolog_ok and prod_ok:
        print("🤔 Situación inusual")
        print("❌ Homologación: NO AUTORIZADO")
        print("✅ Producción: AUTORIZADO") 
        print("💡 Contacta a AFIP para revisar configuración")
        return False
        
    else:
        print("❌ SIN AUTORIZACIÓN WSFEXv1")
        print("❌ Homologación: NO AUTORIZADO")
        print("❌ Producción: NO AUTORIZADO")
        print("🔧 Necesitas solicitar autorización en Mi AFIP")
        mostrar_guia_solicitud()
        return False

def probar_ambiente(cuit, ambiente):
    """Probar autorización en un ambiente específico"""
    try:
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key', 
            ambiente=ambiente
        )
        
        print(f"   🔍 Conectando a {ambiente}...")
        
        # Probar método básico
        tipos = client.obtener_tipos_comprobante(cuit)
        
        if tipos and len(tipos) > 0:
            print(f"   ✅ {ambiente.upper()}: AUTORIZADO")
            print(f"   📋 Tipos disponibles: {len(tipos)}")
            for tipo in tipos[:3]:  # Mostrar primeros 3
                print(f"      • {tipo}")
            if len(tipos) > 3:
                print(f"      • ... y {len(tipos)-3} más")
            return True
        else:
            print(f"   ❌ {ambiente.upper()}: Sin tipos de comprobante")
            return False
            
    except Exception as e:
        error_msg = str(e)
        print(f"   ❌ {ambiente.upper()}: Error de conexión")
        
        if "500" in error_msg:
            print(f"      💡 Error HTTP 500 = Sin autorización")
        elif "401" in error_msg:
            print(f"      💡 Error 401 = Problema de autenticación")
        elif "Certificate" in error_msg:
            print(f"      💡 Problema con certificado")
        else:
            print(f"      🔍 Error: {error_msg[:50]}...")
            
        return False

def mostrar_guia_solicitud():
    """Mostrar guía rápida de solicitud"""
    print(f"\n🔧 CÓMO SOLICITAR AUTORIZACIÓN WSFEXv1")
    print("=" * 50)
    print("1️⃣ Ir a Mi AFIP: https://auth.afip.gob.ar")
    print("2️⃣ Buscar: 'Web Services' o 'Administrador de Relaciones'")
    print("3️⃣ Encontrar: 'WSFEXv1 - Facturación Electrónica Exportadores'")
    print("4️⃣ Hacer clic: 'Agregar' o 'Solicitar Acceso'")
    print("5️⃣ Completar formulario con datos de tu sistema")
    print("6️⃣ Esperar aprobación (1-10 días hábiles)")
    
    print(f"\n📝 DATOS PARA EL FORMULARIO:")
    print("• Descripción: Sistema de consulta de facturas electrónicas")
    print("• Propósito: Integración con WSFEXv1 para facturas M y exportación") 
    print("• Email: [tu email técnico]")
    print("• Teléfono: [tu número de contacto]")
    
    print(f"\n📞 AYUDA:")
    print("• Web: https://www.afip.gob.ar/ws/")
    print("• Email: webservice@afip.gob.ar")
    print("• Tel: 0800-999-2347")

def probar_factura_especifica():
    """Probar consulta de la factura específica una vez autorizado"""
    print(f"\n🎯 PROBAR FACTURA ESPECÍFICA")
    print("=" * 50)
    
    respuesta = input("¿Querés probar buscar la factura 0002-00000235? (s/n): ").lower()
    
    if respuesta in ['s', 'si', 'yes', 'y']:
        print(f"\n🔍 Buscando factura 0002-00000235 en WSFEXv1...")
        
        try:
            from buscar_factura_wsfexv1_especifica import buscar_factura_wsfexv1
            resultado = buscar_factura_wsfexv1()
            
            if resultado:
                print(f"🎉 ¡Factura encontrada en WSFEXv1!")
                return True
            else:
                print(f"📭 Factura no encontrada (aún puede estar en WSMTXCA)")
                return False
                
        except Exception as e:
            print(f"❌ Error probando factura: {e}")
            return False

def main():
    """Función principal"""
    print("🔐 VERIFICADOR DE AUTORIZACIÓN WSFEXv1")
    print("=" * 60)
    print("Este script verifica si tenes acceso a WSFEXv1")
    print("y te guía para solicitarlo si es necesario.")
    print("=" * 60)
    
    # Verificar autorización actual
    autorizado = verificar_autorizacion_actual()
    
    if autorizado:
        # Si está autorizado, ofrecer probar la factura específica
        probar_factura_especifica()
    else:
        # Si no está autorizado, mostrar próximos pasos
        print(f"\n🔄 PRÓXIMOS PASOS:")
        print("1. Seguir la guía para solicitar autorización")
        print("2. Esperar aprobación de AFIP")
        print("3. Volver a ejecutar este script para verificar")
        print("4. Una vez autorizado, buscar la factura 0002-00000235")
    
    print(f"\n📋 ARCHIVO GUÍA CREADO:")
    print("• Revisa: GUIA_AUTORIZAR_WSFEXV1.md")
    print("• Contiene: Proceso completo paso a paso")

if __name__ == "__main__":
    main()