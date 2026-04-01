#!/usr/bin/env python3
"""
EXTRACTOR HÍBRIDO: WSFEv1 + WSFEXv1
===================================

Busca facturas primero en WSFEv1, y si no encuentra o encuentra pocas,
también intenta en WSFEXv1 para capturar facturas de monotributistas.
"""

import sys
import time
from datetime import datetime

sys.path.append('src')
from wsfev1_client import WSFEv1Client
from wsfexv1_client import WSFEXv1Client

def buscar_factura_especifica_hibrida(cuit, punto_venta, numero):
    """
    Buscar una factura específica en AMBOS servicios: WSFEv1 Y WSFEXv1
    
    Args:
        cuit: CUIT del emisor
        punto_venta: Número del punto de venta
        numero: Número de la factura
        
    Returns:
        dict: Información de la factura encontrada o None
    """
    print(f"🔍 BÚSQUEDA HÍBRIDA: WSFEv1 + WSFEXv1")
    print("=" * 50)
    print(f"🎯 CUIT: {cuit}")
    print(f"📍 Factura: {punto_venta:04d}-{numero:08d}")
    print("=" * 50)
    
    # PASO 1: Buscar en WSFEv1 (servicio tradicional)
    print(f"\n1️⃣ BUSCANDO EN WSFEv1 (Servicio Tradicional)...")
    
    try:
        client_wsfe = WSFEv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Tipos WSFEv1 comunes
        tipos_wsfev1 = {
            1: "Factura A", 2: "Nota de Débito A", 3: "Nota de Crédito A",
            6: "Factura B", 7: "Nota de Débito B", 8: "Nota de Crédito B", 
            11: "Factura C", 12: "Nota de Débito C", 13: "Nota de Crédito C",
            51: "Factura M (WSFEv1)", 52: "Nota de Débito M (WSFEv1)"
        }
        
        for tipo_id, tipo_desc in tipos_wsfev1.items():
            print(f"   🔍 Probando {tipo_desc}...")
            
            try:
                factura = client_wsfe.consultar_comprobante(cuit, tipo_id, punto_venta, numero)
                
                if factura and isinstance(factura, dict):
                    print(f"   🎉 ¡ENCONTRADA EN WSFEv1!")
                    factura['servicio_origen'] = 'WSFEv1'
                    factura['tipo_descripcion'] = tipo_desc
                    factura['tipo_id'] = tipo_id
                    return factura
                    
            except Exception as e:
                if "not found" not in str(e).lower():
                    print(f"   ⚠️ Error: {str(e)[:40]}...")
        
        print(f"   📭 No encontrada en WSFEv1")
        
    except Exception as e:
        print(f"   ❌ Error general WSFEv1: {e}")
    
    # PASO 2: Buscar en WSFEXv1 (servicio monotributo/exportación)
    print(f"\n2️⃣ BUSCANDO EN WSFEXv1 (Monotributo/Exportación)...")
    
    try:
        client_wsfex = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Tipos WSFEXv1 específicos
        tipos_wsfexv1 = {
            1: "Factura M (Monotributo)",
            2: "Nota de Débito M", 
            3: "Nota de Crédito M",
            19: "Factura de Exportación",
            20: "Nota de Débito Exportación", 
            21: "Nota de Crédito Exportación"
        }
        
        for tipo_id, tipo_desc in tipos_wsfexv1.items():
            print(f"   🔍 Probando {tipo_desc}...")
            
            try:
                # Intentar consultar en WSFEXv1
                factura = client_wsfex.consultar_comprobante(cuit, punto_venta, tipo_id, numero)
                
                if factura and isinstance(factura, dict):
                    print(f"   🎉 ¡ENCONTRADA EN WSFEXv1!")
                    factura['servicio_origen'] = 'WSFEXv1'
                    factura['tipo_descripcion'] = tipo_desc
                    factura['tipo_id'] = tipo_id
                    return factura
                    
            except Exception as e:
                error_str = str(e).lower()
                if "500" in error_str or "unauthorized" in error_str:
                    print(f"   🔒 Sin autorización WSFEXv1")
                    break  # Sin autorización, no seguir probando
                elif "not found" not in error_str:
                    print(f"   ⚠️ Error: {str(e)[:40]}...")
        
        print(f"   📭 No encontrada en WSFEXv1 (o sin autorización)")
        
    except Exception as e:
        error_str = str(e).lower() 
        if "500" in error_str or "unauthorized" in error_str:
            print(f"   🔒 Sin autorización para WSFEXv1")
        else:
            print(f"   ❌ Error general WSFEXv1: {e}")
    
    # PASO 3: Resultado final
    print(f"\n❌ FACTURA NO ENCONTRADA en ningún servicio")
    print(f"\n💡 POSIBLES CAUSAS:")
    print(f"   • La factura está en WSMTXCA (códigos MTX especiales)")
    print(f"   • Número o punto de venta incorrecto") 
    print(f"   • Factura anulada o cancelada")
    print(f"   • Falta autorización WSFEXv1")
    
    return None

def test_factura_problema():
    """Test específico para la factura 0002-00000235"""
    print(f"🎯 TEST ESPECÍFICO: Factura 0002-00000235")
    print("=" * 60)
    
    cuit = "27312238018"
    punto_venta = 2
    numero = 235
    
    resultado = buscar_factura_especifica_hibrida(cuit, punto_venta, numero)
    
    print(f"\n" + "=" * 60)
    print("📊 RESULTADO DEL TEST")
    print("=" * 60)
    
    if resultado:
        print(f"✅ FACTURA ENCONTRADA!")
        print(f"🔧 Servicio: {resultado['servicio_origen']}")
        print(f"📋 Tipo: {resultado['tipo_descripcion']} ({resultado['tipo_id']})")
        print(f"📄 CAE: {resultado.get('CAE', 'N/A')}")
        print(f"📅 Fecha: {resultado.get('CbteFch', 'N/A')}")
        print(f"💰 Importe: ${resultado.get('ImpTotal', 'N/A')}")
        
        print(f"\n🔍 CAMPOS DISPONIBLES:")
        for key, value in resultado.items():
            if key not in ['servicio_origen', 'tipo_descripcion', 'tipo_id'] and value:
                print(f"   • {key}: {value}")
                
    else:
        print(f"❌ FACTURA NO ENCONTRADA")
        print(f"\n🔧 DIAGNÓSTICO:")
        print(f"   1. ✅ WSFEv1 probado - no está ahí")
        print(f"   2. ⚠️ WSFEXv1 probado - sin autorización o no está")
        print(f"   3. 🤔 Posible ubicación: WSMTXCA")
        
        print(f"\n💡 RECOMENDACIONES:")
        print(f"   • Solicitar autorización WSFEXv1 en Mi AFIP")
        print(f"   • Verificar si es monotributista (requiere WSFEXv1)")
        print(f"   • Considerar que puede estar en WSMTXCA")
    
    return resultado

def extractor_completo_hibrido(cuit, limite_facturas=10):
    """
    Extractor que busca en AMBOS servicios automáticamente
    
    Args:
        cuit: CUIT a extraer
        limite_facturas: Límite de facturas por servicio (para demo)
        
    Returns:
        dict: Facturas encontradas en ambos servicios
    """
    print(f"🚀 EXTRACTOR COMPLETO HÍBRIDO")
    print("=" * 50)
    print(f"🎯 CUIT: {cuit}")
    print(f"🔧 Límite por servicio: {limite_facturas}")
    print("=" * 50)
    
    resultado = {
        'cuit': cuit,
        'facturas_wsfev1': [],
        'facturas_wsfexv1': [],
        'errores': [],
        'timestamp': datetime.now().isoformat()
    }
    
    # PASO 1: Extraer de WSFEv1
    print(f"\n1️⃣ EXTRAYENDO DE WSFEv1...")
    try:
        from extractor_completo_facturas import extraer_facturas_completas
        
        resultado_wsfev1 = extraer_facturas_completas(
            cuit=cuit,
            tipos_incluir=[1, 6, 11],  # A, B, C
            limite_por_tipo=limite_facturas,
            mostrar_progreso=False
        )
        
        resultado['facturas_wsfev1'] = resultado_wsfev1['facturas']
        print(f"   ✅ WSFEv1: {len(resultado['facturas_wsfev1'])} facturas")
        
    except Exception as e:
        error_msg = f"Error WSFEv1: {str(e)[:50]}..."
        resultado['errores'].append(error_msg)
        print(f"   ❌ {error_msg}")
    
    # PASO 2: Extraer de WSFEXv1
    print(f"\n2️⃣ INTENTANDO WSFEXv1...")
    try:
        client_wsfex = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Buscar facturas M en algunos puntos comunes
        puntos_comunes = [1, 2, 3]
        tipos_m = [1]  # Factura M
        
        for punto in puntos_comunes:
            for tipo in tipos_m:
                try:
                    # Intentar obtener último autorizado
                    ultimo = client_wsfex.obtener_ultimo_autorizado(cuit, punto, tipo)
                    
                    if ultimo and ultimo > 0:
                        print(f"   ✅ P{punto}-T{tipo}: último #{ultimo}")
                        
                        # Consultar últimas facturas
                        inicio = max(1, ultimo - limite_facturas + 1)
                        
                        for num in range(ultimo, inicio - 1, -1):
                            factura = client_wsfex.consultar_comprobante(cuit, punto, tipo, num)
                            
                            if factura:
                                factura['servicio_origen'] = 'WSFEXv1'
                                factura['punto_venta'] = punto
                                factura['tipo_comprobante'] = tipo
                                resultado['facturas_wsfexv1'].append(factura)
                    
                except Exception as e:
                    if "500" in str(e):
                        print(f"   🔒 Sin autorización WSFEXv1")
                        break
        
        print(f"   ✅ WSFEXv1: {len(resultado['facturas_wsfexv1'])} facturas")
        
    except Exception as e:
        error_msg = f"Error WSFEXv1: {str(e)[:50]}..."
        resultado['errores'].append(error_msg)
        print(f"   ❌ {error_msg}")
    
    # RESULTADO FINAL
    total_facturas = len(resultado['facturas_wsfev1']) + len(resultado['facturas_wsfexv1'])
    
    print(f"\n📊 RESUMEN FINAL:")
    print(f"   📄 Total facturas: {total_facturas}")
    print(f"   📋 WSFEv1: {len(resultado['facturas_wsfev1'])}")
    print(f"   📋 WSFEXv1: {len(resultado['facturas_wsfexv1'])}")
    print(f"   ❌ Errores: {len(resultado['errores'])}")
    
    return resultado

if __name__ == "__main__":
    print("🎯 BÚSQUEDA HÍBRIDA WSFEv1 + WSFEXv1")
    print("=" * 60)
    
    # Test 1: Factura específica problemática
    print("TEST 1: Factura específica 0002-00000235")
    test_factura_problema()
    
    # Test 2: Extractor híbrido con límite
    print(f"\n\nTEST 2: Extractor híbrido completo")
    resultado_completo = extractor_completo_hibrido("27312238018", limite_facturas=5)
    
    print(f"\n🎯 CONCLUSIÓN:")
    if resultado_completo['facturas_wsfexv1']:
        print("✅ ¡Encontradas facturas en WSFEXv1!")
        print("💡 Necesitas autorización WSFEXv1 para acceso completo")
    else:
        print("⚠️ Sin facturas en WSFEXv1 (probablemente sin autorización)")
        print("🔧 Solicitar autorización WSFEXv1 en Mi AFIP")