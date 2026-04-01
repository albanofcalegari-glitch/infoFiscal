#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test con datos reales - búsqueda inteligente de facturas existentes
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from wsfev1_client import WSFEv1Client

CUIT = "27312238018"

print(f"🎯 BÚSQUEDA INTELIGENTE DE FACTURAS REALES - CUIT: {CUIT}")
print("=" * 70)

try:
    client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
    
    # 1. Primero obtener puntos de venta habilitados
    print("1️⃣ Obteniendo puntos de venta habilitados...")
    puntos_venta = client.obtener_puntos_venta(CUIT)
    
    if puntos_venta:
        print(f"✅ Puntos de venta encontrados: {len(puntos_venta)}")
        for pv in puntos_venta[:5]:  # Mostrar primeros 5
            print(f"   📍 PV {pv.get('numero', 'N/A')}: {pv.get('descripcion', 'Sin descripción')}")
    else:
        print("⚠️ No se encontraron puntos de venta, usando lista manual")
        puntos_venta = [{'numero': 1}, {'numero': 2}, {'numero': 3}]
    
    # 2. Obtener tipos de comprobante habilitados
    print("\n2️⃣ Obteniendo tipos de comprobante habilitados...")
    tipos_comprobante = client.obtener_tipos_comprobante(CUIT)
    
    if tipos_comprobante:
        print(f"✅ Tipos de comprobante encontrados: {len(tipos_comprobante)}")
        for tipo in tipos_comprobante[:8]:  # Mostrar primeros 8
            print(f"   📝 Tipo {tipo.get('id', 'N/A')}: {tipo.get('descripcion', 'Sin descripción')}")
    else:
        print("⚠️ No se encontraron tipos, usando lista manual")
        tipos_comprobante = [
            {'id': 1, 'descripcion': 'Factura A'},
            {'id': 6, 'descripcion': 'Factura B'}, 
            {'id': 11, 'descripcion': 'Factura C'},
            {'id': 51, 'descripcion': 'Factura M'}
        ]
    
    # 3. Búsqueda sistemática de facturas existentes
    print("\n3️⃣ Búsqueda sistemática de facturas existentes...")
    facturas_encontradas = []
    
    # Probar cada combinación punto de venta + tipo
    for pv_info in puntos_venta[:3]:  # Solo primeros 3 PV
        pv_num = pv_info.get('numero', pv_info) if isinstance(pv_info, dict) else pv_info
        
        for tipo_info in tipos_comprobante[:4]:  # Solo primeros 4 tipos
            tipo_id = tipo_info.get('id', tipo_info) if isinstance(tipo_info, dict) else tipo_info
            tipo_desc = tipo_info.get('descripcion', f'Tipo {tipo_id}') if isinstance(tipo_info, dict) else f'Tipo {tipo_id}'
            
            print(f"\n   🔍 Probando PV {pv_num} - {tipo_desc} (Tipo {tipo_id})")
            
            try:
                # Obtener último autorizado
                ultimo = client.obtener_ultimo_comprobante(CUIT, tipo_id, pv_num)
                print(f"      📊 Último autorizado: {ultimo}")
                
                if ultimo and ultimo > 0:
                    # Buscar hacia atrás desde el último
                    print(f"      🔍 Buscando facturas desde {ultimo} hacia atrás...")
                    
                    for num in range(ultimo, max(1, ultimo - 10), -1):  # Últimas 10
                        try:
                            print(f"         🔍 Consultando {pv_num:04d}-{num:08d}...")
                            comp = client.consultar_comprobante(CUIT, tipo_id, pv_num, num)
                            
                            if comp:
                                print(f"         ✅ ENCONTRADA!")
                                print(f"            CAE: {comp.get('CAE', 'N/A')}")
                                print(f"            Fecha: {comp.get('CbteFch', 'N/A')}")
                                print(f"            Total: ${comp.get('ImpTotal', 'N/A')}")
                                
                                facturas_encontradas.append({
                                    'pv': pv_num,
                                    'tipo': tipo_id,
                                    'numero': num,
                                    'cae': comp.get('CAE'),
                                    'fecha': comp.get('CbteFch'),
                                    'total': comp.get('ImpTotal'),
                                    'tipo_desc': tipo_desc
                                })
                                
                                # Solo queremos una por tipo/PV para el demo
                                break
                            else:
                                print(f"         📭 No existe")
                        except Exception as e:
                            print(f"         ❌ Error: {e}")
                    
                else:
                    print(f"      📭 No hay comprobantes para este tipo/PV")
                    
            except Exception as e:
                print(f"      ❌ Error consultando último: {e}")
    
    # 4. Resumen de resultados
    print(f"\n" + "=" * 70)
    print(f"📊 RESUMEN DE BÚSQUEDA")
    print(f"=" * 70)
    
    if facturas_encontradas:
        print(f"🎉 ¡FACTURAS ENCONTRADAS! ({len(facturas_encontradas)} total)")
        print()
        
        for i, factura in enumerate(facturas_encontradas, 1):
            print(f"{i}. PV {factura['pv']:04d}-{factura['numero']:08d}")
            print(f"   Tipo: {factura['tipo']} ({factura['tipo_desc']})")
            print(f"   CAE: {factura['cae']}")
            print(f"   Fecha: {factura['fecha']}")
            print(f"   Total: ${factura['total']}")
            print()
            
        # Ahora probar la función de búsqueda unificada
        print("🎯 Probando función de búsqueda unificada...")
        resultados_unificados = client.buscar_comprobantes_rango(
            CUIT, 
            tipos_comprobante=[f['tipo'] for f in facturas_encontradas],
            puntos_venta=[f['pv'] for f in facturas_encontradas],
            limite_por_tipo=5
        )
        
        print(f"✅ Búsqueda unificada completada: {len(resultados_unificados)} encontrados")
        
    else:
        print("📭 No se encontraron facturas")
        print("💡 Posibles razones:")
        print("   - CUIT sin facturas emitidas")
        print("   - Facturas en otros puntos de venta")
        print("   - Facturas de otros tipos de comprobante")
        print("   - Necesita usar WSMTXCA/WSFEXv1 en lugar de WSFEv1")

except Exception as e:
    print(f"❌ Error en la búsqueda: {e}")
    import traceback
    traceback.print_exc()

print(f"\n✅ BÚSQUEDA COMPLETADA")