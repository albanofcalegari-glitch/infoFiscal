#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificación urgente: ¿En qué servicio están las facturas 235-238?
Vamos a probar TODOS los clientes disponibles
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importar SOLO WSFEv1 que sabemos que funciona
from wsfev1_client import WSFEv1Client

def buscar_facturas_en_todos_lados():
    """Buscar las facturas usando todos los métodos posibles"""
    
    CUIT = "27312238018"
    PUNTO_VENTA = 2
    FACTURAS = [235, 236, 237, 238]
    
    print(f"🚀 BÚSQUEDA EXHAUSTIVA DE FACTURAS EXISTENTES")
    print("=" * 60)
    print(f"🏢 CUIT: {CUIT}")
    print(f"📍 Punto de Venta: {PUNTO_VENTA}")
    print(f"📄 Facturas: {FACTURAS}")
    print("=" * 60)
    
    # ===============================================
    # MÉTODO 1: WSFEv1 con TODOS los tipos posibles
    # ===============================================
    
    print(f"\n1️⃣ WSFEv1 - Búsqueda exhaustiva de tipos")
    print("-" * 40)
    
    try:
        client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        # Lista COMPLETA de tipos de comprobante
        tipos_completos = [
            (1, "Factura A"), (2, "Nota de Débito A"), (3, "Nota de Crédito A"),
            (4, "Recibo A"), (5, "Nota de Venta al Contado A"), (6, "Factura B"),
            (7, "Nota de Débito B"), (8, "Nota de Crédito B"), (9, "Recibo B"),
            (10, "Nota de Venta al Contado B"), (11, "Factura C"), (12, "Nota de Débito C"),
            (13, "Nota de Crédito C"), (15, "Recibo C"), (16, "Nota de Venta al Contado C"),
            (19, "Factura de Exportación"), (20, "Nota de Débito por Operaciones con el Exterior"),
            (21, "Nota de Crédito por Operaciones con el Exterior"),
            (51, "Factura M"), (52, "Nota de Débito M"), (53, "Nota de Crédito M"),
            (54, "Recibo M"), (55, "Nota de Venta al Contado M"),
            (81, "Tique Factura A"), (82, "Tique Factura B"), (83, "Tique"),
            (109, "Tique Nota de Crédito A"), (110, "Tique Nota de Crédito B"),
            (111, "Tique Factura C"), (112, "Tique Nota de Crédito C"),
            (113, "Tique Nota de Débito A"), (114, "Tique Nota de Débito B"),
            (115, "Tique Nota de Débito C"), (116, "Tique Factura M"),
            (117, "Tique Nota de Crédito M"), (118, "Tique Nota de Débito M")
        ]
        
        facturas_encontradas = []
        
        # Probar solo la primera factura con todos los tipos
        factura_test = FACTURAS[0]  # 235
        
        print(f"   🔍 Probando factura {factura_test} en {len(tipos_completos)} tipos...")
        
        for tipo_id, tipo_desc in tipos_completos:
            try:
                print(f"      📝 Tipo {tipo_id:3d} ({tipo_desc[:30]:30s}): ", end="")
                
                comp = client.consultar_comprobante(CUIT, tipo_id, PUNTO_VENTA, factura_test)
                
                if comp and comp.get('CAE'):
                    print(f"✅ ENCONTRADA! CAE: {comp.get('CAE')}")
                    facturas_encontradas.append({
                        'numero': factura_test,
                        'tipo': tipo_id,
                        'tipo_desc': tipo_desc,
                        'cae': comp.get('CAE'),
                        'servicio': 'WSFEv1'
                    })
                    break  # Encontramos el tipo correcto
                else:
                    print(f"❌")
                    
            except Exception as e:
                print(f"ERROR: {str(e)[:50]}")
        
        if facturas_encontradas:
            print(f"\n   🎉 ¡FACTURA ENCONTRADA EN WSFEv1!")
            f = facturas_encontradas[0]
            print(f"      Tipo: {f['tipo']} ({f['tipo_desc']})")
            print(f"      CAE: {f['cae']}")
            
            # Ahora buscar las otras facturas con el mismo tipo
            print(f"\n   🔍 Buscando las demás facturas con tipo {f['tipo']}...")
            
            for num in FACTURAS[1:]:  # 236, 237, 238
                try:
                    comp = client.consultar_comprobante(CUIT, f['tipo'], PUNTO_VENTA, num)
                    if comp and comp.get('CAE'):
                        print(f"      📄 {num}: ✅ CAE {comp.get('CAE')}")
                        facturas_encontradas.append({
                            'numero': num,
                            'tipo': f['tipo'],
                            'cae': comp.get('CAE'),
                            'servicio': 'WSFEv1'
                        })
                    else:
                        print(f"      📄 {num}: ❌ No encontrada")
                except Exception as e:
                    print(f"      📄 {num}: ❌ Error: {e}")
        
        else:
            print(f"   📭 No encontrada en WSFEv1 con ningún tipo")
    
    except Exception as e:
        print(f"   ❌ Error en WSFEv1: {e}")
    
    # ===============================================
    # RESUMEN
    # ===============================================
    
    print(f"\n" + "=" * 60)
    print(f"📊 RESUMEN DE LA BÚSQUEDA")
    print("=" * 60)
    
    if facturas_encontradas:
        print(f"🎉 ¡FACTURAS ENCONTRADAS! ({len(facturas_encontradas)} total)")
        print(f"\n📋 Detalle:")
        
        for f in facturas_encontradas:
            print(f"   📄 Factura {f['numero']}")
            print(f"      Servicio: {f['servicio']}")
            print(f"      Tipo: {f['tipo']} ({f.get('tipo_desc', 'N/A')})")
            print(f"      CAE: {f['cae']}")
            print()
        
        # Actualizar el app.py con el tipo correcto
        tipo_correcto = facturas_encontradas[0]['tipo']
        print(f"💡 TIPO CORRECTO IDENTIFICADO: {tipo_correcto}")
        print(f"   Necesitas actualizar app.py para usar tipo {tipo_correcto} en lugar de 11 o 51")
        
    else:
        print(f"❌ NO SE ENCONTRARON FACTURAS EN WSFEv1")
        print(f"\n💡 ESTO SIGNIFICA QUE ESTÁN EN:")
        print(f"   • WSMTXCA (necesita fix de autenticación)")
        print(f"   • WSFEXv1 (necesita fix de autenticación)")
        print(f"   • Otro servicio no contemplado")
    
    return facturas_encontradas

if __name__ == "__main__":
    facturas = buscar_facturas_en_todos_lados()
    
    if facturas:
        print(f"\n🎯 SIGUIENTE PASO:")
        print(f"   Las facturas están en el tipo {facturas[0]['tipo']}")
        print(f"   Actualizar la lógica de búsqueda unificada para usar este tipo")
    else:
        print(f"\n🔧 SIGUIENTE PASO:")
        print(f"   Arreglar la autenticación WSAA de WSMTXCA/WSFEXv1")
        print(f"   Las facturas deben estar en uno de esos servicios")