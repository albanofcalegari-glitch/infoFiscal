#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para WSFEXv1 - Facturación Electrónica para Monotributistas
Prueba del servicio correcto para usuarios de Monotributo y Régimen Simplificado
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from wsfexv1_client import WSFEXv1Client, crear_cliente_wsfexv1

def test_wsfexv1_completo():
    """Test completo de WSFEXv1 vs WSFEv1"""
    print("🧪 TEST COMPLETO: WSFEXv1 vs WSFEv1")
    print("=" * 60)
    
    # Configuración
    # Usar tu CUIT real - ajusta según tu caso
    cuit = "27312238018"
    
    print(f"🔍 Probando servicios para CUIT: {cuit}")
    print("\n📋 DIFERENCIAS CLAVE:")
    print("   WSFEv1  → Responsables Inscriptos (facturas A, B, C)")
    print("   WSFEXv1 → Monotributistas + Exportación (facturas M, exportación)")
    
    # Test WSFEXv1
    print("\n" + "="*50)
    print("🚀 PROBANDO WSFEXv1 (MONOTRIBUTO)")
    print("="*50)
    
    try:
        client = crear_cliente_wsfexv1('prod')
        
        # 1. Test de conexión y autenticación
        print("\n1️⃣ Verificando autenticación...")
        token, sign = client._obtener_token_wsaa()
        print(f"✅ Autenticación exitosa")
        print(f"   Token: {token[:30]}...")
        print(f"   Sign: {sign[:30]}...")
        
        # 2. Obtener puntos de venta
        print("\n2️⃣ Obteniendo puntos de venta...")
        puntos = client.obtener_puntos_venta(cuit)
        if puntos:
            print(f"✅ Puntos de venta encontrados: {puntos}")
        else:
            print("⚠️ No hay puntos de venta habilitados")
            print("💡 Esto puede indicar que el CUIT no está habilitado para WSFEXv1")
            return False
        
        # 3. Obtener tipos de comprobante
        print("\n3️⃣ Obteniendo tipos de comprobante...")
        tipos = client.obtener_tipos_comprobante(cuit)
        if tipos:
            print(f"✅ {len(tipos)} tipos de comprobante disponibles:")
            for tipo in tipos:
                if tipo['id'] in [51, 52, 53, 19, 20, 21]:  # Monotributo y exportación
                    print(f"   🎯 {tipo['id']}: {tipo['descripcion']}")
                elif len(tipos) <= 10:  # Si hay pocos, mostrar todos
                    print(f"      {tipo['id']}: {tipo['descripcion']}")
        else:
            print("⚠️ No se obtuvieron tipos de comprobante")
        
        # 4. Test específico para facturas M (monotributo)
        print("\n4️⃣ Probando facturas de Monotributo (tipo 51)...")
        if puntos:
            primer_punto = puntos[0]
            
            # Obtener último autorizado
            ultimo = client.obtener_ultimo_autorizado(cuit, primer_punto, 51)
            print(f"   Último autorizado PV {primer_punto}, tipo 51: {ultimo}")
            
            if ultimo > 0:
                print(f"   🔍 Consultando factura M #{ultimo}...")
                factura = client.consultar_comprobante(cuit, primer_punto, 51, ultimo)
                
                if factura:
                    print("   ✅ FACTURA ENCONTRADA:")
                    print(f"      Punto de venta: {factura.get('punto_venta')}")
                    print(f"      Tipo: {factura.get('tipo_comprobante')} (Factura M)")
                    print(f"      Número: {factura.get('numero')}")
                    print(f"      CAE: {factura.get('cae', 'N/A')}")
                    print(f"      Fecha emisión: {factura.get('fecha_emision', 'N/A')}")
                    print(f"      Fecha vto CAE: {factura.get('fecha_vto_cae', 'N/A')}")
                else:
                    print("   📭 No se pudo obtener la factura")
            else:
                print("   📭 No hay facturas M emitidas en este punto de venta")
        
        # 5. Búsqueda sistemática
        print("\n5️⃣ Búsqueda sistemática de facturas...")
        facturas = client.buscar_facturas_monotributo(cuit, max_por_punto=3)
        
        if facturas:
            print(f"\n🎉 ÉXITO: {len(facturas)} facturas encontradas")
            print("\n📊 RESUMEN DE FACTURAS:")
            for i, factura in enumerate(facturas[:5], 1):  # Mostrar máximo 5
                print(f"   {i}. PV:{factura.get('punto_venta')} - {factura.get('descripcion_tipo')} #{factura.get('numero')}")
                print(f"      CAE: {factura.get('cae', 'N/A')[:15]}... - {factura.get('fecha_emision', 'N/A')}")
        else:
            print("\n📭 No se encontraron facturas de monotributo")
            print("💡 Posibles causas:")
            print("   - El CUIT no está en régimen de monotributo")
            print("   - No se han emitido facturas M aún")
            print("   - El certificado no tiene permisos para WSFEXv1")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN WSFEXv1: {e}")
        print("\n💡 Posibles soluciones:")
        print("   1. Verificar que el CUIT esté en régimen de monotributo")
        print("   2. Habilitar servicio WSFEXv1 en AFIP Admin")
        print("   3. Asociar certificado al servicio WSFEXv1")
        print("   4. Verificar que el certificado sea válido")
        return False

def comparar_servicios():
    """Comparar características de WSFEv1 vs WSFEXv1"""
    print("\n" + "="*60)
    print("📊 COMPARACIÓN WSFEv1 vs WSFEXv1")
    print("="*60)
    
    print("\n🔸 WSFEv1 (Web Service Factura Electrónica v1):")
    print("   ✅ Para: Responsables Inscriptos")
    print("   ✅ Tipos: Facturas A, B, C (1, 6, 11)")
    print("   ✅ Tipos: Notas de Débito/Crédito A, B, C")
    print("   ✅ Disponible: Siempre (es el servicio principal)")
    print("   ✅ Desde: 2013 (todas las facturas electrónicas)")
    
    print("\n🔸 WSFEXv1 (Web Service Factura Electrónica Exportación v1):")
    print("   ✅ Para: Monotributistas + Exportadores")
    print("   ✅ Tipos: Facturas M (51, 52, 53)")
    print("   ✅ Tipos: Facturas de Exportación (19, 20, 21)")
    print("   ⚠️ Requiere: Habilitación específica en AFIP")
    print("   ⚠️ Solo si: El contribuyente emite estos tipos")
    
    print("\n💡 RECOMENDACIÓN:")
    print("   1. Si eres Responsable Inscripto → usar WSFEv1")
    print("   2. Si eres Monotributista → usar WSFEXv1") 
    print("   3. Si exportas → usar WSFEXv1")
    print("   4. Algunos CUITs pueden necesitar AMBOS servicios")

def main():
    """Función principal"""
    print("🚀 INICIO DEL TEST WSFEXv1")
    
    # Test completo
    exito = test_wsfexv1_completo()
    
    # Comparación de servicios
    comparar_servicios()
    
    # Conclusión
    print("\n" + "="*60)
    print("🎯 CONCLUSIÓN")
    print("="*60)
    
    if exito:
        print("✅ WSFEXv1 está funcionando correctamente")
        print("✅ Puedes usarlo para consultar facturas de monotributo")
        print("✅ El certificado tiene los permisos necesarios")
    else:
        print("❌ WSFEXv1 no está funcionando")
        print("⚠️ Verifica la configuración y permisos en AFIP")
        print("💡 Considera usar WSFEv1 si eres Responsable Inscripto")
    
    print(f"\n📚 PRÓXIMOS PASOS:")
    print("   1. Integrar WSFEXv1 en la aplicación web")
    print("   2. Crear interfaz específica para monotributo") 
    print("   3. Probar con diferentes CUITs de monotributo")
    print("   4. Implementar descarga masiva de facturas M")

if __name__ == "__main__":
    main()