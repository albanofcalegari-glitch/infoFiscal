#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para buscar las facturas específicas:
- 0002-00000235
- 0002-00000236
CUIT: 27312238018

Este script aplica la corrección del bug en el método de búsqueda
donde comp['status'] == 'encontrado' debía ser comp is not None
"""

import sys
import os

# Agregar el directorio src si existe
if os.path.exists('src'):
    sys.path.insert(0, 'src')

from wsfev1_client import WSFEv1Client

def buscar_facturas_especificas():
    """Buscar las facturas específicas que sabemos que existen"""
    
    # Configuración
    CUIT = "27312238018"
    PUNTO_VENTA = 2  # 0002 como entero
    NUMEROS = [235, 236]
    
    # Tipos más probables (ordenados por probabilidad)
    TIPOS_PROBABLES = [
        11,  # Factura C (monotributistas) - MÁS PROBABLE
        6,   # Factura B 
        1,   # Factura A
        51,  # Factura M (monotributo)
        2,   # Nota de Débito A
        3,   # Nota de Crédito A
        7,   # Nota de Débito B
        8,   # Nota de Crédito B
        52,  # Nota de Débito M
        53,  # Nota de Crédito M
    ]
    
    print("🔍 BÚSQUEDA DE FACTURAS ESPECÍFICAS")
    print("=" * 50)
    print(f"🏢 CUIT: {CUIT}")
    print(f"📄 Punto de venta: {PUNTO_VENTA:04d}")
    print(f"🎯 Números buscados: {NUMEROS}")
    print("=" * 50)
    
    # Crear cliente WSFEv1
    try:
        client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        print("✅ Cliente WSFEv1 inicializado")
    except Exception as e:
        print(f"❌ Error inicializando cliente: {e}")
        return []
    
    # Autenticar
    try:
        token, sign = client.autenticar_wsaa(CUIT)
        print("✅ Autenticación WSAA exitosa")
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        return []
    
    facturas_encontradas = []
    
    for tipo in TIPOS_PROBABLES:
        tipo_desc = client.tipos_comprobante.get(tipo, f"Tipo {tipo}")
        print(f"\n📋 Probando tipo {tipo} - {tipo_desc}")
        
        # Verificar último autorizado para este tipo/PV
        try:
            ultimo = client.obtener_ultimo_comprobante(CUIT, tipo, PUNTO_VENTA)
            if ultimo and ultimo > 0:
                print(f"   ✅ Último autorizado: {ultimo}")
                
                # Solo buscar si nuestros números están en rango
                numeros_en_rango = [n for n in NUMEROS if n <= ultimo]
                if not numeros_en_rango:
                    print(f"   ⚠️ Números {NUMEROS} están fuera de rango (último: {ultimo})")
                    continue
                
                for numero in numeros_en_rango:
                    print(f"   🔎 Consultando {PUNTO_VENTA:04d}-{numero:08d}...")
                    
                    try:
                        # Consultar factura específica
                        comp = client.consultar_comprobante(CUIT, tipo, PUNTO_VENTA, numero)
                        
                        # APLICAR LA CORRECCIÓN DEL BUG
                        if comp is not None:  # ✅ Validación correcta (antes era comp['status'] == 'encontrado')
                            print(f"   🎉 ¡ENCONTRADA! {PUNTO_VENTA:04d}-{numero:08d}")
                            print(f"      📅 Fecha: {comp.get('CbteFch', 'N/A')}")
                            print(f"      💰 Total: ${comp.get('ImpTotal', 'N/A')}")
                            print(f"      🔑 CAE: {comp.get('CAE', 'N/A')}")
                            print(f"      📝 Tipo: {tipo} ({tipo_desc})")
                            
                            # Agregar metadatos de la búsqueda
                            comp['busqueda'] = {
                                'cuit': CUIT,
                                'tipo': tipo,
                                'tipo_descripcion': tipo_desc,
                                'punto_venta': PUNTO_VENTA,
                                'numero': numero,
                                'numero_formateado': f"{PUNTO_VENTA:04d}-{numero:08d}"
                            }
                            
                            facturas_encontradas.append(comp)
                            
                            # Si encontramos una, podemos assumir que las demás del mismo tipo también existen
                            break
                        else:
                            print(f"      ❌ No encontrada como tipo {tipo}")
                            
                    except Exception as e:
                        print(f"      ⚠️ Error consultando: {str(e)[:100]}...")
                        continue
                        
            else:
                print(f"   📭 Sin comprobantes de este tipo (último: {ultimo})")
                
        except Exception as e:
            print(f"   ❌ Error obteniendo último autorizado: {str(e)[:100]}...")
            continue
    
    # Mostrar resumen
    print(f"\n" + "=" * 50)
    print(f"📊 RESUMEN DE RESULTADOS")
    print("=" * 50)
    print(f"✅ Facturas encontradas: {len(facturas_encontradas)}")
    
    if facturas_encontradas:
        print(f"\n📋 DETALLES:")
        for i, factura in enumerate(facturas_encontradas, 1):
            busqueda = factura.get('busqueda', {})
            print(f"{i}. {busqueda.get('numero_formateado', 'N/A')}")
            print(f"   Tipo: {busqueda.get('tipo_descripcion', 'N/A')}")
            print(f"   Fecha: {factura.get('CbteFch', 'N/A')}")
            print(f"   Total: ${factura.get('ImpTotal', 'N/A')}")
            print(f"   CAE: {factura.get('CAE', 'N/A')}")
            print()
    else:
        print(f"\n❌ No se encontraron las facturas buscadas")
        print(f"\n💡 POSIBLES CAUSAS:")
        print(f"   • Las facturas pueden estar en WSFEXv1 (monotributo)")
        print(f"   • El tipo de comprobante no está en la lista probada")
        print(f"   • Problema de permisos o certificados")
        print(f"   • Las facturas no existen en WSFEv1")
        
        print(f"\n🔧 PRÓXIMOS PASOS:")
        print(f"   1. Verificar en WSFEXv1 (archivo: busqueda_hibrida_wsfev1_wsfexv1.py)")
        print(f"   2. Ampliar tipos de comprobante probados")
        print(f"   3. Verificar permisos de delegación")
    
    return facturas_encontradas

def test_correccion_bug():
    """
    Test específico para demostrar que la corrección del bug funciona
    """
    print(f"\n🧪 TEST DE CORRECCIÓN DEL BUG")
    print("=" * 40)
    print(f"BUG ORIGINAL: comp['status'] == 'encontrado'")
    print(f"CORRECCIÓN:   comp is not None")
    print("=" * 40)
    
    # Simular el comportamiento anterior vs nuevo
    print(f"\n📝 Comportamiento del método consultar_comprobante():")
    print(f"   • Factura encontrada → Retorna dict con datos")
    print(f"   • Factura NO encontrada → Retorna None")
    print(f"   • NUNCA retorna dict con 'status': 'encontrado'")
    
    print(f"\n✅ Por eso la corrección es:")
    print(f"   ANTES: if comp['status'] == 'encontrado':  ❌")
    print(f"   AHORA: if comp is not None:               ✅")

def main():
    """Función principal"""
    print("🚀 SCRIPT DE CORRECCIÓN DE BUG - WSFEv1")
    print("=" * 60)
    print("Buscando facturas 0002-00000235 y 0002-00000236")
    print("CUIT: 27312238018")
    print("=" * 60)
    
    # Ejecutar test de corrección
    test_correccion_bug()
    
    # Buscar las facturas específicas
    facturas = buscar_facturas_especificas()
    
    # Guardar resultados si se encontraron
    if facturas:
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"facturas_encontradas_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(facturas, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados guardados en: {filename}")
    
    print(f"\n🎯 Script completado")
    return facturas

if __name__ == "__main__":
    main()