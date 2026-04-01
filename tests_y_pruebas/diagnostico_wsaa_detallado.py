#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnóstico específico de problemas de autenticación WSAA
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from wsfev1_client import WSFEv1Client
from wsmtxca_client import WSMTXCAClient
from wsfexv1_client import WSFEXv1Client

CUIT = "27312238018"

print(f"🔧 DIAGNÓSTICO ESPECÍFICO WSAA - CUIT: {CUIT}")
print("=" * 60)

# Test detallado de cada servicio
servicios = [
    ('wsfe', WSFEv1Client),
    ('wsmtxca', WSMTXCAClient), 
    ('wsfex', WSFEXv1Client)
]

for servicio_nombre, ClienteClass in servicios:
    print(f"\n📋 SERVICIO: {servicio_nombre.upper()}")
    print("-" * 40)
    
    try:
        # Crear cliente
        client = ClienteClass('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        # Para WSFEv1 usar método específico
        if servicio_nombre == 'wsfe':
            token, sign = client.autenticar_wsaa(CUIT)
            print(f"✅ {servicio_nombre.upper()} - Autenticación exitosa")
            print(f"   Token: {token[:50]}...")
            print(f"   Sign: {sign[:50]}...")
            
            # Probar consulta específica
            print(f"\n🔍 Probando obtener último comprobante...")
            tipos_test = [11, 51, 6, 1]  # Facturas C, M, B, A
            for tipo in tipos_test:
                for pv in [1, 2]:
                    ultimo = client.obtener_ultimo_comprobante(CUIT, tipo, pv)
                    if ultimo and ultimo > 0:
                        print(f"   ✅ Tipo {tipo}, PV {pv}: Último = {ultimo}")
                        
                        # Consultar ese comprobante específico
                        comp = client.consultar_comprobante(CUIT, tipo, pv, ultimo)
                        if comp:
                            print(f"      🎯 Comprobante encontrado: CAE {comp.get('CAE', 'N/A')}")
                        break
                    else:
                        print(f"   📭 Tipo {tipo}, PV {pv}: Sin comprobantes")
        
        elif servicio_nombre == 'wsmtxca':
            # Test específico de WSMTXCA
            print(f"🔍 Probando autenticación WSMTXCA...")
            try:
                # Probar facturas M específicas
                facturas_test = [
                    {'tipo': 51, 'pv': 1, 'num': 1},
                    {'tipo': 51, 'pv': 2, 'num': 1},
                ]
                
                for f in facturas_test:
                    print(f"   🔍 Consultando Tipo {f['tipo']}, PV {f['pv']}, Num {f['num']}...")
                    try:
                        comp = client.consultar_comprobante(CUIT, f['tipo'], f['pv'], f['num'])
                        if comp:
                            print(f"      ✅ ENCONTRADO: CAE {comp.get('cae', 'N/A')}")
                        else:
                            print(f"      📭 No encontrado")
                    except Exception as e:
                        if "500" in str(e):
                            print(f"      ❌ Error 500 - Problema de certificado/WSAA")
                        else:
                            print(f"      ❌ Error: {e}")
                        
            except Exception as e:
                print(f"❌ Error en WSMTXCA: {e}")
                
        elif servicio_nombre == 'wsfex':
            # Test específico de WSFEXv1
            print(f"🔍 Probando WSFEXv1...")
            try:
                # Intentar diagnóstico
                resultado = client.diagnostico_completo(CUIT)
                if resultado:
                    print(f"✅ WSFEXv1 funcional")
                else:
                    print(f"❌ WSFEXv1 con problemas")
            except Exception as e:
                print(f"❌ Error WSFEXv1: {e}")
    
    except Exception as e:
        print(f"❌ Error creando cliente {servicio_nombre.upper()}: {e}")
        import traceback
        traceback.print_exc()

print(f"\n🔬 ANÁLISIS DE RESULTADOS:")
print("=" * 60)
print("1. WSFEv1 funciona → Certificado válido")
print("2. WSMTXCA/WSFEXv1 fallan → Problema específico con estos servicios")
print("3. Error 500 → Posible problema de permisos del certificado")
print("\n💡 SOLUCIONES POSIBLES:")
print("- Verificar que el certificado tenga permisos para WSMTXCA y WSFEXv1") 
print("- Revisar si necesita homologación específica para cada servicio")
print("- Verificar configuración de TRA para cada servicio")
print("\n✅ DIAGNÓSTICO COMPLETADO")