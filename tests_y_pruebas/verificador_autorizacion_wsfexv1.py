#!/usr/bin/env python3
"""
VERIFICADOR DE AUTORIZACIÓN WSFEXv1
===================================

Script para verificar automáticamente si ya tenés autorización WSFEXv1
o ayudarte durante el proceso de solicitud.
"""

import sys
import time
from datetime import datetime

sys.path.append('src')

def verificar_estado_autorizacion():
    """Verificar el estado actual de autorización WSFEXv1"""
    print("🔍 VERIFICADOR DE AUTORIZACIÓN WSFEXv1")
    print("=" * 50)
    
    # Solicitar CUIT
    while True:
        cuit = input("📋 Ingresá tu CUIT (11 dígitos): ").strip().replace('-', '')
        if len(cuit) == 11 and cuit.isdigit():
            break
        print("❌ CUIT inválido. Debe tener 11 dígitos sin guiones.")
    
    print(f"\n🎯 Verificando CUIT: {cuit}")
    
    # Probar homologación
    print(f"\n1️⃣ PROBANDO HOMOLOGACIÓN...")
    homo_ok = probar_ambiente(cuit, 'homologacion')
    
    # Probar producción  
    print(f"\n2️⃣ PROBANDO PRODUCCIÓN...")
    prod_ok = probar_ambiente(cuit, 'prod')
    
    # Mostrar resultado
    mostrar_resultado(homo_ok, prod_ok, cuit)
    
    return homo_ok or prod_ok

def probar_ambiente(cuit, ambiente):
    """Probar autorización en un ambiente específico"""
    try:
        from wsfexv1_client import WSFEXv1Client
        
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente=ambiente
        )
        
        print(f"   🔍 Conectando a {ambiente}...")
        
        # Intentar operación básica
        tipos = client.obtener_tipos_comprobante(cuit)
        
        if tipos and len(tipos) > 0:
            print(f"   ✅ {ambiente.upper()}: AUTORIZADO")
            print(f"   📋 Tipos disponibles: {len(tipos)}")
            
            # Mostrar algunos tipos
            for i, tipo in enumerate(tipos[:3]):
                print(f"      • {tipo.get('descripcion', f'Tipo {tipo.get('id', i+1)}')}")
            if len(tipos) > 3:
                print(f"      • ... y {len(tipos)-3} más")
                
            return True
        else:
            print(f"   ❌ {ambiente.upper()}: Sin tipos disponibles")
            return False
            
    except Exception as e:
        error_str = str(e).lower()
        
        if "500" in error_str:
            print(f"   🔒 {ambiente.upper()}: SIN AUTORIZACIÓN (Error 500)")
            print(f"      💡 Necesitas solicitar acceso en Mi AFIP")
        elif "401" in error_str or "unauthorized" in error_str:
            print(f"   🔐 {ambiente.upper()}: Problema de autenticación")
            print(f"      💡 Verificar certificados")
        elif "ssl" in error_str or "certificate" in error_str:
            print(f"   🔒 {ambiente.upper()}: Problema de certificado SSL")
            print(f"      💡 Verificar certificados válidos")
        else:
            print(f"   ❌ {ambiente.upper()}: Error de conexión")
            print(f"      🔍 Error: {str(e)[:40]}...")
            
        return False

def mostrar_resultado(homo_ok, prod_ok, cuit):
    """Mostrar resultado final y próximos pasos"""
    print(f"\n" + "=" * 60)
    print("📊 RESULTADO DE LA VERIFICACIÓN")
    print("=" * 60)
    
    if homo_ok and prod_ok:
        print("🎉 ¡EXCELENTE! AUTORIZACIÓN COMPLETA")
        print("✅ Homologación: AUTORIZADO")  
        print("✅ Producción: AUTORIZADO")
        print("🚀 Podés usar WSFEXv1 en ambos ambientes")
        
        print(f"\n🎯 PRÓXIMO PASO:")
        print("Probar buscar la factura específica 0002-00000235")
        
        probar_factura_especifica(cuit)
        
    elif homo_ok and not prod_ok:
        print("⚡ AUTORIZACIÓN PARCIAL")
        print("✅ Homologación: AUTORIZADO")
        print("❌ Producción: NO AUTORIZADO")
        
        print(f"\n🔄 PRÓXIMOS PASOS:")
        print("1. Probar tu integración en homologación")
        print("2. Solicitar autorización para producción en Mi AFIP")
        print("3. Usar el mismo proceso que usaste para homologación")
        
    elif not homo_ok and prod_ok:
        print("🤔 SITUACIÓN INUSUAL")
        print("❌ Homologación: NO AUTORIZADO")
        print("✅ Producción: AUTORIZADO")
        
        print(f"\n💡 RECOMENDACIÓN:")
        print("Contactar soporte AFIP - situación no estándar")
        
    else:
        print("❌ SIN AUTORIZACIÓN WSFEXv1")
        print("❌ Homologación: NO AUTORIZADO")
        print("❌ Producción: NO AUTORIZADO")
        
        print(f"\n🔧 NECESITAS SOLICITAR AUTORIZACIÓN:")
        mostrar_guia_solicitud(cuit)

def mostrar_guia_solicitud(cuit):
    """Mostrar guía rápida de solicitud"""
    print("1️⃣ Ir a Mi AFIP: https://auth.afip.gob.ar")
    print("2️⃣ Buscar: 'Web Services' o 'Administrador de Relaciones'")
    print("3️⃣ Encontrar: 'WSFEXv1 - Facturación Electrónica Exportadores'")
    print("4️⃣ Hacer clic: 'Agregar' o 'Solicitar Acceso'")
    print("5️⃣ Completar formulario (ver GUIA_OBTENER_PERMISOS_WSFEXV1.md)")
    print("6️⃣ Esperar aprobación (1-10 días hábiles)")
    
    print(f"\n📋 DATOS PARA EL FORMULARIO:")
    print("• Sistema: 'Consulta de Facturas Electrónicas'")
    print("• Propósito: 'Consultar facturas M y de exportación'") 
    print("• Justificación: 'Integración completa con servicios AFIP'")
    
    print(f"\n📞 AYUDA:")
    print("• Email: webservice@afip.gob.ar")
    print("• Tel: 0800-999-2347")
    print("• Documentación completa: GUIA_OBTENER_PERMISOS_WSFEXV1.md")

def probar_factura_especifica(cuit):
    """Probar buscar la factura específica 0002-00000235"""
    if cuit != "27312238018":
        return
        
    print(f"\n🎯 PROBANDO FACTURA ESPECÍFICA 0002-00000235...")
    
    try:
        from busqueda_hibrida_wsfev1_wsfexv1 import buscar_factura_especifica_hibrida
        
        resultado = buscar_factura_especifica_hibrida(cuit, 2, 235)
        
        if resultado and resultado.get('servicio_origen') == 'WSFEXv1':
            print(f"🎉 ¡FACTURA ENCONTRADA EN WSFEXv1!")
            print(f"📋 Tipo: {resultado.get('tipo_descripcion', 'N/A')}")
            print(f"💰 Importe: ${resultado.get('ImpTotal', 'N/A')}")
            print(f"📅 Fecha: {resultado.get('CbteFch', 'N/A')}")
            print(f"🔐 CAE: {resultado.get('CAE', 'N/A')}")
        else:
            print(f"📭 Factura aún no encontrada")
            print(f"💡 Puede necesitar autorización adicional")
            
    except Exception as e:
        print(f"❌ Error probando factura: {e}")

def menu_principal():
    """Menú principal del verificador"""
    print("🎯 VERIFICADOR DE AUTORIZACIÓN WSFEXv1")
    print("=" * 60)
    print("Este script te ayuda a verificar si ya tenés")
    print("autorización para WSFEXv1 y te guía en el proceso.")
    print("=" * 60)
    
    while True:
        print(f"\n📋 OPCIONES:")
        print("1️⃣ Verificar mi autorización actual")
        print("2️⃣ Ver guía de solicitud")
        print("3️⃣ Probar factura específica (27312238018)")
        print("4️⃣ Salir")
        
        opcion = input("\n🔢 Elegí una opción (1-4): ").strip()
        
        if opcion == "1":
            verificar_estado_autorizacion()
            
        elif opcion == "2":
            print(f"\n📖 GUÍA DE SOLICITUD:")
            print("Ver archivo: GUIA_OBTENER_PERMISOS_WSFEXV1.md")
            print("Contiene el proceso completo paso a paso.")
            
        elif opcion == "3":
            print(f"\n🎯 PROBANDO FACTURA ESPECÍFICA...")
            cuit = "27312238018"
            
            # Verificar si tiene autorización
            from wsfexv1_client import WSFEXv1Client
            
            try:
                client = WSFEXv1Client(
                    cert_path='certs/certificado.crt',
                    key_path='certs/clave_privada.key',
                    ambiente='prod'
                )
                
                tipos = client.obtener_tipos_comprobante(cuit)
                
                if tipos:
                    print("✅ Tienes autorización - buscando factura...")
                    probar_factura_especifica(cuit)
                else:
                    print("❌ Sin autorización WSFEXv1")
                    
            except Exception as e:
                if "500" in str(e):
                    print("🔒 Sin autorización WSFEXv1 para este CUIT")
                    print("💡 Necesitas solicitar acceso en Mi AFIP")
                else:
                    print(f"❌ Error: {e}")
            
        elif opcion == "4":
            print(f"\n👋 ¡Hasta luego!")
            print("💡 Recordá revisar GUIA_OBTENER_PERMISOS_WSFEXV1.md")
            break
            
        else:
            print("❌ Opción inválida. Elegí 1, 2, 3 o 4.")

if __name__ == "__main__":
    try:
        menu_principal()
    except KeyboardInterrupt:
        print(f"\n\n👋 Proceso interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        print("💡 Verificar configuración de certificados")