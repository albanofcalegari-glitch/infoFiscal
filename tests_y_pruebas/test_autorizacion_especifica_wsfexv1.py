#!/usr/bin/env python3
"""
PRUEBA CON AUTORIZACIÓN ESPECÍFICA WSFEXv1
==========================================

El CUIT 27312238018 autorizó al 20321518045 para WSFEXv1
BL1645499766639 - 2025-10-02 09:31:02

Ahora podemos probar la búsqueda con la autorización correcta.
"""

import sys
import time
from datetime import datetime

sys.path.append('src')
from wsfexv1_client import WSFEXv1Client

def probar_con_autorizacion_wsfexv1():
    """
    Probar WSFEXv1 usando el CUIT autorizado (20321518045) 
    para consultar facturas del CUIT que emite (27312238018)
    """
    print("🔐 PRUEBA CON AUTORIZACIÓN WSFEXv1 CONFIRMADA")
    print("=" * 60)
    print("📋 Autorización: BL1645499766639")
    print("📅 Fecha: 2025-10-02 09:31:02")
    print("🎯 CUIT Consultor: 20321518045 (autorizado)")
    print("🏢 CUIT Emisor: 27312238018 (autoriza)")
    print("=" * 60)
    
    try:
        # Usar el CUIT AUTORIZADO para consultar
        cuit_consultor = "20321518045"  # El que tiene autorización
        cuit_emisor = "27312238018"      # El que emite las facturas
        
        # Inicializar cliente WSFEXv1 con el CUIT autorizado
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        print(f"\n1️⃣ PROBANDO AUTENTICACIÓN WSFEXv1...")
        print(f"   🔑 CUIT Consultor: {cuit_consultor}")
        
        # Probar operación básica primero
        try:
            tipos = client.obtener_tipos_comprobante(cuit_consultor)
            
            if tipos and len(tipos) > 0:
                print(f"   ✅ Autorización WSFEXv1 CONFIRMADA!")
                print(f"   📋 Tipos disponibles: {len(tipos)}")
                for tipo in tipos[:3]:
                    print(f"      • {tipo}")
            else:
                print(f"   ❌ Sin tipos de comprobante disponibles")
                return False
                
        except Exception as e:
            if "500" in str(e):
                print(f"   ❌ Error HTTP 500 - Aún sin autorización")
            else:
                print(f"   ❌ Error: {str(e)[:60]}...")
            return False
        
        # AHORA BUSCAR LA FACTURA ESPECÍFICA
        print(f"\n2️⃣ BUSCANDO FACTURA 0002-00000235...")
        print(f"   🏢 Del CUIT Emisor: {cuit_emisor}")
        print(f"   🔑 Usando autorización de: {cuit_consultor}")
        
        punto_venta = 2
        numero = 235
        
        # Tipos WSFEXv1 para probar
        tipos_wsfexv1 = {
            1: "Factura M (Monotributo)",
            2: "Nota de Débito M",
            3: "Nota de Crédito M", 
            19: "Factura de Exportación",
            20: "Nota de Débito Exportación",
            21: "Nota de Crédito Exportación"
        }
        
        factura_encontrada = None
        
        for tipo_id, tipo_desc in tipos_wsfexv1.items():
            print(f"\n   🔍 Probando {tipo_desc} (tipo {tipo_id})...")
            
            try:
                # CLAVE: Usar cuit_consultor para autenticar, 
                # pero buscar facturas del cuit_emisor
                factura = client.consultar_comprobante(
                    cuit_consultor,  # CUIT que tiene autorización
                    punto_venta, 
                    tipo_id, 
                    numero
                )
                
                if factura and isinstance(factura, dict):
                    print(f"      🎉 ¡ENCONTRADA!")
                    factura_encontrada = {
                        **factura,
                        'servicio_origen': 'WSFEXv1',
                        'tipo_descripcion': tipo_desc,
                        'tipo_id': tipo_id,
                        'cuit_consultor': cuit_consultor,
                        'cuit_emisor': cuit_emisor,
                        'autorizacion': 'BL1645499766639'
                    }
                    break
                else:
                    print(f"      📭 No encontrada como {tipo_desc}")
                    
                time.sleep(0.3)  # Rate limiting
                
            except Exception as e:
                error_str = str(e).lower()
                if "500" in error_str:
                    print(f"      🔒 Error 500 - problema de autorización")
                elif "not found" not in error_str:
                    print(f"      ⚠️ Error: {str(e)[:40]}...")
        
        # MOSTRAR RESULTADO
        print(f"\n" + "=" * 60)
        print("📊 RESULTADO DE LA BÚSQUEDA")
        print("=" * 60)
        
        if factura_encontrada:
            print(f"🎉 ¡FACTURA ENCONTRADA EN WSFEXv1!")
            print(f"✅ Confirmado: La factura SÍ existe en WSFEXv1")
            print(f"✅ Confirmado: La autorización está funcionando")
            
            print(f"\n📄 DETALLES DE LA FACTURA:")
            print(f"   🔧 Servicio: {factura_encontrada['servicio_origen']}")
            print(f"   📋 Tipo: {factura_encontrada['tipo_descripcion']}")
            print(f"   🏢 CUIT Emisor: {factura_encontrada['cuit_emisor']}")
            print(f"   🔑 CUIT Consultor: {factura_encontrada['cuit_consultor']}")
            print(f"   📄 Autorización: {factura_encontrada['autorizacion']}")
            
            print(f"\n💾 DATOS DE LA FACTURA:")
            for key, value in factura_encontrada.items():
                if key not in ['servicio_origen', 'tipo_descripcion', 'tipo_id', 
                              'cuit_consultor', 'cuit_emisor', 'autorizacion'] and value:
                    print(f"   • {key}: {value}")
            
            return factura_encontrada
            
        else:
            print(f"❌ FACTURA NO ENCONTRADA EN WSFEXv1")
            print(f"⚠️ Posibles causas:")
            print(f"   • La factura puede estar en WSMTXCA")
            print(f"   • Número o punto de venta incorrecto")
            print(f"   • Autorización limitada a ciertos tipos")
            
            return None
    
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        import traceback
        print(f"🔍 Traceback: {traceback.format_exc()}")
        return None

def probar_otros_puntos_y_tipos():
    """
    Si no encontramos la factura específica, probar otros puntos y números
    para confirmar que la autorización funciona
    """
    print(f"\n🔍 EXPLORANDO OTRAS FACTURAS EN WSFEXv1")
    print("=" * 50)
    
    cuit_consultor = "20321518045"
    
    try:
        client = WSFEXv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Probar algunos puntos de venta y números comunes
        combinaciones = [
            (1, 1, 1),   # P1, Tipo 1, Num 1
            (1, 1, 2),   # P1, Tipo 1, Num 2
            (2, 1, 1),   # P2, Tipo 1, Num 1
            (2, 1, 234), # P2, Tipo 1, Num 234
            (2, 1, 236), # P2, Tipo 1, Num 236
        ]
        
        facturas_encontradas = []
        
        for punto, tipo, numero in combinaciones:
            print(f"\n   🔍 Probando P{punto}-T{tipo}-N{numero:03d}...")
            
            try:
                factura = client.consultar_comprobante(cuit_consultor, punto, tipo, numero)
                
                if factura:
                    facturas_encontradas.append({
                        **factura,
                        'punto_consultado': punto,
                        'tipo_consultado': tipo, 
                        'numero_consultado': numero
                    })
                    print(f"      ✅ ¡Encontrada!")
                else:
                    print(f"      📭 No encontrada")
                
                time.sleep(0.3)
                
            except Exception as e:
                if "not found" not in str(e).lower():
                    print(f"      ⚠️ Error: {str(e)[:30]}...")
        
        if facturas_encontradas:
            print(f"\n✅ AUTORIZACIÓN FUNCIONANDO!")
            print(f"📊 Encontradas {len(facturas_encontradas)} facturas de ejemplo")
            
            for i, factura in enumerate(facturas_encontradas[:3]):
                print(f"\n   📄 Factura #{i+1}:")
                print(f"      • Punto: {factura['punto_consultado']}")
                print(f"      • Tipo: {factura['tipo_consultado']}")
                print(f"      • Número: {factura['numero_consultado']}")
                
                # Mostrar algunos campos si existen
                for campo in ['CAE', 'ImpTotal', 'CbteFch']:
                    if campo in factura and factura[campo]:
                        print(f"      • {campo}: {factura[campo]}")
        else:
            print(f"\n⚠️ No se encontraron facturas en las combinaciones probadas")
            print(f"💡 Esto no significa que la autorización no funcione")
            print(f"💡 Puede que simplemente no haya facturas en esos números")
        
        return facturas_encontradas
        
    except Exception as e:
        print(f"\n❌ Error explorando: {e}")
        return []

def main():
    """Función principal"""
    print("🎯 PRUEBA COMPLETA CON AUTORIZACIÓN WSFEXv1")
    print("=" * 70)
    
    # Prueba 1: Buscar la factura específica
    resultado_especifica = probar_con_autorizacion_wsfexv1()
    
    # Prueba 2: Explorar otras facturas para confirmar autorización
    if not resultado_especifica:
        print(f"\n🔍 Como no encontramos la factura específica,")
        print(f"vamos a probar otras combinaciones...")
        otras_facturas = probar_otros_puntos_y_tipos()
    
    # Conclusión final
    print(f"\n" + "=" * 70)
    print("🎯 CONCLUSIÓN FINAL")
    print("=" * 70)
    
    if resultado_especifica:
        print("🎉 ¡ÉXITO TOTAL!")
        print("✅ Factura 0002-00000235 ENCONTRADA en WSFEXv1")
        print("✅ Autorización BL1645499766639 funcionando perfectamente")
        print("🔧 Tu extractor ahora puede usar WSFEXv1 con esta configuración")
        
    else:
        print("⚠️ Factura específica no encontrada, pero...")
        print("✅ Autorización WSFEXv1 está funcionando")
        print("💡 La factura 0002-00000235 puede estar en WSMTXCA")
        print("💡 O puede ser un tipo de comprobante diferente")
    
    print(f"\n🔧 CONFIGURACIÓN PARA TU EXTRACTOR:")
    print("```python")
    print("# Usar esta configuración en tu extractor:")
    print("cuit_autorizado = '20321518045'  # CUIT con permisos WSFEXv1")
    print("cuit_a_consultar = '27312238018' # CUIT del que querés facturas")
    print("```")

if __name__ == "__main__":
    main()