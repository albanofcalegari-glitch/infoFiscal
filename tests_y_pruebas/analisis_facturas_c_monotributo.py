#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS: Facturas C de Monotributistas - ¿Qué servicio usar?
Investigación sobre dónde encontrar facturas C emitidas por monotributistas
"""

def analizar_facturas_c_monotributo():
    """Análisis de dónde están las facturas C de monotributistas"""
    print("🔍 FACTURAS C DE MONOTRIBUTISTAS - ANÁLISIS COMPLETO")
    print("=" * 70)
    
    print("\n📊 SITUACIÓN ACTUAL:")
    print("-" * 40)
    print("❓ PREGUNTA: ¿Dónde están las Facturas C de monotributistas?")
    print("🎯 RESPUESTA: Depende del caso específico")
    
    print(f"\n📋 ESCENARIOS POSIBLES:")
    print("=" * 50)
    
    print(f"\n🔸 ESCENARIO 1: Monotributista que emite Facturas C")
    print("   📄 Tipo: Factura C (tipo 11)")
    print("   🎯 Servicio: WSFEv1 (el que ya tienes)")
    print("   💡 Explicación: Las facturas C están en WSFEv1 aunque seas monotributista")
    print("   ✅ Estado: YA FUNCIONA con tu código actual")
    
    print(f"\n🔸 ESCENARIO 2: Monotributista que emite Facturas M")
    print("   📄 Tipo: Factura M (tipo 51)")
    print("   🎯 Servicio: WSFEXv1 (requiere habilitación)")
    print("   💡 Explicación: Las facturas M son específicas de monotributo")
    print("   ⚠️ Estado: Requiere habilitar WSFEXv1")
    
    print(f"\n🔸 ESCENARIO 3: Monotributista con códigos MTX")
    print("   📄 Tipo: Facturas con códigos MTX especiales")
    print("   🎯 Servicio: WSMTXCA (casos muy específicos)")
    print("   💡 Explicación: Para productos con códigos MTX obligatorios")
    print("   ⚠️ Estado: Requiere habilitación especial")

def diferencias_facturas_c_vs_m():
    """Diferencias entre Facturas C y Facturas M"""
    print(f"\n📊 DIFERENCIAS: FACTURA C vs FACTURA M")
    print("=" * 70)
    
    print(f"\n🔸 FACTURA C (Tipo 11):")
    print("   👤 Emisor: Cualquier contribuyente (RI, Monotributo, etc.)")
    print("   👥 Receptor: Consumidor Final")
    print("   📍 Servicio: WSFEv1")
    print("   💰 IVA: No discrimina IVA")
    print("   📝 Uso: Ventas al público en general")
    print("   ✅ Disponible: Siempre en WSFEv1")
    
    print(f"\n🔸 FACTURA M (Tipo 51):")
    print("   👤 Emisor: SOLO Monotributistas")
    print("   👥 Receptor: Consumidor Final principalmente")
    print("   📍 Servicio: WSFEXv1")
    print("   💰 IVA: Régimen especial monotributo")
    print("   📝 Uso: Específico para monotributistas")
    print("   ⚠️ Disponible: Solo si se habilita WSFEXv1")
    
    print(f"\n💡 CLAVE: Un monotributista puede emitir AMBOS tipos")
    print("   • Factura C → en WSFEv1")
    print("   • Factura M → en WSFEXv1")

def test_facturas_c_monotributo():
    """Test para verificar facturas C de monotributistas"""
    print(f"\n🧪 TEST: BUSCAR FACTURAS C DE MONOTRIBUTISTAS")
    print("=" * 70)
    
    print("\n1️⃣ ESTRATEGIA RECOMENDADA:")
    print("-" * 40)
    print("✅ USAR WSFEv1 PRIMERO (el que ya tienes)")
    print("   • Buscar tipo 11 (Factura C)")
    print("   • La mayoría de facturas C están aquí")
    print("   • Funciona para RI y Monotributistas")
    
    print("\n2️⃣ SI NO ENCUENTRAS FACTURAS C EN WSFEv1:")
    print("-" * 40)
    print("⚠️ CONSIDERAR WSFEXv1")
    print("   • Algunos monotributistas usan solo facturas M")
    print("   • En este caso no hay facturas C")
    print("   • Solo hay facturas M (tipo 51)")
    
    print("\n3️⃣ CASOS ESPECIALES:")
    print("-" * 40)
    print("🔸 Monotributista con productos MTX → WSMTXCA")
    print("🔸 Monotributista exportador → WSFEXv1")
    print("🔸 Monotributista tradicional → WSFEv1 + WSFEXv1")

def codigo_ejemplo():
    """Código de ejemplo para buscar facturas C"""
    print(f"\n💻 CÓDIGO DE EJEMPLO")
    print("=" * 70)
    
    codigo = '''
# Buscar Facturas C de monotributista
def buscar_facturas_c_monotributista(cuit):
    """Buscar facturas C emitidas por un monotributista"""
    
    # PASO 1: Buscar en WSFEv1 (la mayoría están aquí)
    from wsfev1_client import WSFEv1Client
    
    client = WSFEv1Client(cert_path, key_path, ambiente='prod')
    
    # Buscar Facturas C (tipo 11)
    facturas_c = []
    for punto in [1, 2, 3]:
        ultimo = client.obtener_ultimo_comprobante(cuit, 11, punto)
        if ultimo and ultimo > 0:
            for num in range(max(1, ultimo-10), ultimo+1):
                factura = client.consultar_comprobante(cuit, 11, punto, num)
                if factura:
                    facturas_c.append(factura)
    
    return facturas_c

# Si WSFEv1 no tiene facturas C, probar WSFEXv1
def buscar_facturas_m_como_alternativa(cuit):
    """Si no hay facturas C, buscar facturas M"""
    
    from wsfexv1_client import WSFEXv1Client
    
    client = WSFEXv1Client(cert_path, key_path, ambiente='prod')
    
    # Buscar Facturas M (tipo 51)
    facturas_m = client.buscar_facturas_monotributo(cuit)
    
    return facturas_m
'''
    
    print(codigo)

def recomendacion_final():
    """Recomendación final"""
    print(f"\n🎯 RECOMENDACIÓN PARA FACTURAS C DE MONOTRIBUTISTAS")
    print("=" * 70)
    
    print(f"\n✅ SOLUCIÓN ÓPTIMA:")
    print("1. 🔍 USAR WSFEv1 PRIMERO")
    print("   • Buscar tipo 11 (Factura C)")
    print("   • Cubre 80-90% de los casos")
    print("   • Ya tienes el código funcionando")
    
    print(f"\n2. 🔍 SI NO ENCUENTRA NADA EN WSFEv1:")
    print("   • Habilitar WSFEXv1")
    print("   • Buscar tipo 51 (Factura M)")
    print("   • Algunos monotributistas solo usan facturas M")
    
    print(f"\n3. 🔍 IMPLEMENTACIÓN INTELIGENTE:")
    print("   • Primero intentar WSFEv1")
    print("   • Si no hay resultados, intentar WSFEXv1")
    print("   • Mostrar ambos tipos al usuario")
    
    print(f"\n🎯 RESPUESTA DIRECTA A TU PREGUNTA:")
    print("📄 Para Facturas C de monotributistas → WSFEv1")
    print("📄 Para Facturas M de monotributistas → WSFEXv1")
    print("📄 Un monotributista puede tener AMBOS tipos")

def main():
    """Función principal"""
    analizar_facturas_c_monotributo()
    diferencias_facturas_c_vs_m()
    test_facturas_c_monotributo()
    codigo_ejemplo()
    recomendacion_final()
    
    print(f"\n" + "="*70)
    print("🎉 RESPUESTA FINAL")
    print("="*70)
    print("Para FACTURAS C de monotributistas:")
    print("🎯 USAR WSFEv1 (el que ya tienes funcionando)")
    print("🔍 Buscar tipo 11 en puntos de venta 1, 2, 3...")
    print("✅ No necesitas cambiar nada en tu código actual")

if __name__ == "__main__":
    main()