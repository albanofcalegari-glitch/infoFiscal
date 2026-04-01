#!/usr/bin/env python3
"""
TEST DEL EXTRACTOR COMPLETO DE FACTURAS
=======================================

Prueba el extractor completo con un CUIT real pero limitando
las consultas para no sobrecargar AFIP.
"""

import sys
import json
from datetime import datetime

sys.path.append('src')
from extractor_completo_facturas import extraer_facturas_completas

def test_extractor_basico():
    """Test básico del extractor"""
    print("🧪 TEST DEL EXTRACTOR COMPLETO")
    print("=" * 50)
    
    # CUIT de prueba (usar uno conocido)
    cuit_test = "27312238018"  # El mismo que hemos estado usando
    
    print(f"🎯 CUIT de prueba: {cuit_test}")
    print(f"⚠️  LIMITADO: Solo primeras 3 facturas por tipo")
    print("=" * 50)
    
    try:
        # Extraer con límites para prueba
        resultado = extraer_facturas_completas(
            cuit=cuit_test,
            tipos_incluir=[1, 6, 11],  # Solo Factura A, B, C
            puntos_incluir=None,       # Todos los puntos
            limite_por_tipo=3,         # Máximo 3 facturas por combinación
            mostrar_progreso=True
        )
        
        print("\n" + "=" * 60)
        print("📊 RESULTADO DEL TEST")
        print("=" * 60)
        
        facturas = resultado['facturas']
        estadisticas = resultado['estadisticas']
        resumen = resultado['resumen']
        
        print(f"✅ Facturas encontradas: {len(facturas)}")
        
        # Calcular tiempo transcurrido de forma segura
        tiempo_inicio = estadisticas.get('tiempo_inicio')
        tiempo_fin = estadisticas.get('tiempo_fin')
        if tiempo_inicio and tiempo_fin:
            tiempo_transcurrido = tiempo_fin - tiempo_inicio
            print(f"⏱️  Tiempo transcurrido: {tiempo_transcurrido}")
        else:
            print(f"⏱️  Tiempo transcurrido: No disponible")
        
        print(f"📍 Puntos de venta: {estadisticas['puntos_venta']}")
        print(f"📋 Tipos de comprobante: {estadisticas['tipos_comprobante']}")
        print(f"❌ Errores: {estadisticas['errores']}")
        
        if facturas:
            print(f"\n🔍 MUESTRA DE FACTURAS ENCONTRADAS:")
            for i, factura in enumerate(facturas[:3]):
                print(f"\n   📄 Factura #{i+1}:")
                print(f"      • Tipo: {factura.get('CbteTipo', 'N/A')}")
                print(f"      • Número: {factura.get('PtoVta', 'N/A')}-{factura.get('CbteNro', 'N/A')}")
                print(f"      • Fecha: {factura.get('CbteFch', 'N/A')}")
                print(f"      • CAE: {factura.get('CAE', 'N/A')}")
                print(f"      • Importe: ${factura.get('ImpTotal', 'N/A')}")
        
        print(f"\n📊 RESUMEN POR PUNTO DE VENTA:")
        for punto, info in resumen['por_punto_venta'].items():
            if info['cantidad'] > 0:
                print(f"   • Punto {punto}: {info['cantidad']} facturas - {info['descripcion']}")
        
        print(f"\n📋 RESUMEN POR TIPO:")
        for tipo, info in resumen['por_tipo_comprobante'].items():
            if info['cantidad'] > 0:
                print(f"   • Tipo {tipo}: {info['cantidad']} facturas - {info['descripcion']}")
        
        print(f"\n💰 RESUMEN DE IMPORTES:")
        if resumen['importes']['total_general'] > 0:
            print(f"   • Total general: ${resumen['importes']['total_general']:,.2f}")
            print(f"   • Promedio: ${resumen['importes']['promedio']:,.2f}")
            print(f"   • Máximo: ${resumen['importes']['maximo']:,.2f}")
            print(f"   • Mínimo: ${resumen['importes']['minimo']:,.2f}")
        else:
            print("   • No hay importes válidos para calcular")
        
        # Guardar resultado para análisis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_resultado = f"test_extractor_resultado_{timestamp}.json"
        
        # Convertir datetime a string para JSON
        resultado_serializable = {
            'facturas': facturas,
            'estadisticas': {
                **estadisticas,
                'tiempo_inicio': estadisticas['tiempo_inicio'].isoformat() if estadisticas['tiempo_inicio'] else None,
                'tiempo_fin': estadisticas['tiempo_fin'].isoformat() if estadisticas['tiempo_fin'] else None
            },
            'resumen': resumen
        }
        
        with open(archivo_resultado, 'w', encoding='utf-8') as f:
            json.dump(resultado_serializable, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 RESULTADO GUARDADO EN: {archivo_resultado}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return False

def test_metodos_individuales():
    """Test de métodos individuales del WSFEv1Client"""
    print("\n🔧 TEST DE MÉTODOS INDIVIDUALES")
    print("=" * 50)
    
    try:
        from wsfev1_client import WSFEv1Client
        
        client = WSFEv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        cuit = "27312238018"
        
        # Test 1: Obtener puntos de venta
        print(f"\n1️⃣ PROBANDO PUNTOS DE VENTA...")
        puntos = client.obtener_puntos_venta(cuit)
        print(f"   ✅ Encontrados: {len(puntos)} puntos de venta")
        for punto in puntos[:3]:
            print(f"      • {punto}")
        
        # Test 2: Obtener tipos de comprobante  
        print(f"\n2️⃣ PROBANDO TIPOS DE COMPROBANTE...")
        tipos = client.obtener_tipos_comprobante(cuit)
        print(f"   ✅ Encontrados: {len(tipos)} tipos")
        for tipo in tipos[:5]:
            print(f"      • {tipo}")
        
        # Test 3: Último autorizado para combinación específica
        if puntos and tipos:
            punto_test = puntos[0]['numero']
            tipo_test = tipos[0]['id']
            
            print(f"\n3️⃣ PROBANDO ÚLTIMO AUTORIZADO...")
            print(f"   🔍 Punto {punto_test}, Tipo {tipo_test}")
            ultimo = client.obtener_ultimo_comprobante(cuit, tipo_test, punto_test)
            print(f"   ✅ Último autorizado: {ultimo}")
            
            # Test 4: Consultar comprobante específico
            if ultimo and ultimo > 0:
                print(f"\n4️⃣ PROBANDO CONSULTA DE COMPROBANTE...")
                numero_test = min(ultimo, 1)  # Consultar el número 1 o el último
                factura = client.consultar_comprobante(cuit, tipo_test, punto_test, numero_test)
                
                if factura:
                    print(f"   ✅ Factura encontrada: {len(factura)} campos")
                    print(f"      • CAE: {factura.get('CAE', 'N/A')}")
                    print(f"      • Importe: {factura.get('ImpTotal', 'N/A')}")
                else:
                    print(f"   📭 Factura no encontrada")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR EN TEST INDIVIDUAL: {e}")
        return False

def main():
    """Ejecutar todos los tests"""
    print("🎯 SUITE DE TESTS DEL EXTRACTOR COMPLETO")
    print("=" * 60)
    
    # Test 1: Métodos individuales
    test1_ok = test_metodos_individuales()
    
    # Test 2: Extractor completo (solo si el test 1 pasó)
    if test1_ok:
        test2_ok = test_extractor_basico()
    else:
        print("\n⏭️  Saltando test del extractor completo debido a errores en métodos individuales")
        test2_ok = False
    
    # Resultado final
    print("\n" + "=" * 60)
    print("🏁 RESULTADO FINAL DE TESTS")
    print("=" * 60)
    print(f"✅ Test métodos individuales: {'PASÓ' if test1_ok else 'FALLÓ'}")
    print(f"✅ Test extractor completo: {'PASÓ' if test2_ok else 'FALLÓ'}")
    
    if test1_ok and test2_ok:
        print("\n🎉 ¡TODOS LOS TESTS PASARON!")
        print("✅ El extractor está listo para usar en producción")
    else:
        print("\n⚠️  ALGUNOS TESTS FALLARON")
        print("🔧 Revisar errores antes de usar en producción")

if __name__ == "__main__":
    main()