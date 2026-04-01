#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de diagnóstico para identificar por qué no se encuentran facturas
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from wsfev1_client import WSFEv1Client
from wsmtxca_client import WSMTXCAClient
from wsfexv1_client import WSFEXv1Client

CUIT = "27312238018"

print(f"🧪 DIAGNÓSTICO DE FACTURAS - CUIT: {CUIT}")
print("=" * 60)

# TEST 1: WSFEv1
print("\n📘 TEST 1: WSFEv1")
print("-" * 40)
try:
    client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
    
    # Autenticación
    print("🔐 Autenticando...")
    token, sign = client.autenticar_wsaa(CUIT)
    print(f"✅ Token obtenido: {token[:30]}...")
    
    # Probar tipo 11, PV 2
    print("\n📊 Consultando último comprobante Tipo 11, PV 2...")
    ultimo = client.obtener_ultimo_comprobante(CUIT, 11, 2)
    print(f"Último autorizado: {ultimo}")
    
    if ultimo and ultimo > 0:
        print(f"\n🔍 Consultando comprobante {ultimo}...")
        comp = client.consultar_comprobante(CUIT, 11, 2, ultimo)
        if comp:
            print(f"✅ ENCONTRADO:")
            print(f"   CAE: {comp.get('CAE')}")
            print(f"   Fecha: {comp.get('CbteFch')}")
            print(f"   Total: ${comp.get('ImpTotal')}")
        else:
            print(f"❌ No encontrado")
    else:
        print("⚠️ Punto de venta sin comprobantes o no existe")
        
    # Probar otros puntos de venta
    print("\n🔍 Probando otros puntos de venta...")
    for pv in [1, 2, 3, 4, 5]:
        ultimo = client.obtener_ultimo_comprobante(CUIT, 11, pv)
        if ultimo and ultimo > 0:
            print(f"   PV {pv}: Último = {ultimo}")
        
except Exception as e:
    print(f"❌ Error WSFEv1: {e}")
    import traceback
    traceback.print_exc()

# TEST 2: WSMTXCA
print("\n\n📗 TEST 2: WSMTXCA")
print("-" * 40)
try:
    client = WSMTXCAClient('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
    
    # Probar facturas específicas
    facturas_test = [
        {'tipo': 11, 'pv': 2, 'num': 235},
        {'tipo': 51, 'pv': 2, 'num': 235},
    ]
    
    for f in facturas_test:
        print(f"\n🔍 Consultando Tipo {f['tipo']}, PV {f['pv']}, Num {f['num']}...")
        try:
            comp = client.consultar_comprobante(CUIT, f['tipo'], f['pv'], f['num'])
            if comp:
                print(f"✅ ENCONTRADO: CAE {comp.get('cae')}")
            else:
                print(f"❌ No encontrado")
        except Exception as e:
            print(f"❌ Error: {e}")
            
except Exception as e:
    print(f"❌ Error WSMTXCA: {e}")

# TEST 3: WSFEXv1
print("\n\n📙 TEST 3: WSFEXv1")
print("-" * 40)
try:
    client = WSFEXv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
    resultado = client.diagnostico_completo(CUIT)
    if resultado:
        print("✅ WSFEXv1 funcional")
    else:
        print("❌ WSFEXv1 con problemas")
except Exception as e:
    print(f"❌ Error WSFEXv1: {e}")

print("\n" + "=" * 60)
print("✅ DIAGNÓSTICO COMPLETADO")