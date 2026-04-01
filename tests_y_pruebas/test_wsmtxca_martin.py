#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prueba básica de WSMTXCA con datos de Martin Vega
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from wsmtxca_client import WSMTXCAClient
import json

def test_wsmtxca_martin_vega():
    """
    Test básico de WSMTXCA con Martin Vega
    Utiliza datos que sabemos que funcionan en WSFEv1
    """
    print("🔍 Probando WSMTXCA con datos de Martin Vega")
    print("-" * 50)
    
    # Datos de Martin Vega que funcionan en WSFEv1
    cuit_martin = "27291928698"
    
    try:
        # Configurar rutas de certificados (usar las mismas que WSFEv1)
        cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
        
        print(f"📁 Certificado: {cert_path}")
        print(f"🔑 Clave privada: {key_path}")
        
        # Crear cliente WSMTXCA
        cliente = WSMTXCAClient(str(cert_path), str(key_path))
        print(f"✅ Cliente WSMTXCA creado")
        
        # Autenticar con CUIT de Martin Vega
        print(f"🔐 Autenticando con WSAA (CUIT: {cuit_martin})...")
        token = cliente.autenticar_wsaa(cuit_martin)
        if token:
            print(f"✅ Autenticación exitosa")
        else:
            print(f"❌ Error en autenticación")
            return False
        
        # Probar consulta con diferentes tipos de comprobante
        tipos_comprobrante = [
            (11, "Factura C"),
            (51, "Factura M"), 
            (1, "Factura A"),
            (6, "Factura B")
        ]
        
        for tipo_cbte, desc_tipo in tipos_comprobrante:
            print(f"\n📋 Probando {desc_tipo} (Tipo {tipo_cbte})")
            print(f"   CUIT: {cuit_martin}")
            print(f"   Punto de Venta: 1")
            print(f"   Número: 1")
            
            try:
                resultado = cliente.consultar_comprobante(
                    cuit=cuit_martin,
                    tipo=tipo_cbte,
                    punto_venta=1,
                    numero=1
                )
                
                if resultado['status'] == 'encontrado':
                    datos = resultado['datos']
                    print(f"   ✅ Encontrado - CAE: {datos.get('cae', 'N/A')}")
                    print(f"   📅 Fecha: {datos.get('fecha_emision', 'N/A')}")
                    print(f"   💰 Total: ${datos.get('importe_total', '0')}")
                    
                    if 'items' in resultado and resultado['items']:
                        print(f"   📦 Items: {len(resultado['items'])}")
                        for idx, item in enumerate(resultado['items'][:2]):  # Mostrar solo 2
                            print(f"     {idx+1}. {item.get('descripcion', 'N/A')} - MTX: {item.get('codigo_mtx', 'N/A')}")
                    
                elif resultado['status'] == 'no_encontrado':
                    print(f"   📭 No encontrado")
                else:
                    print(f"   ⚠️ Estado: {resultado['status']}")
                    
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_consulta_puntos_venta():
    """
    Probar diferentes puntos de venta
    """
    print(f"\n🏪 Probando diferentes puntos de venta")
    print("-" * 50)
    
    cuit_martin = "27291928698"
    
    cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
    key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
    cliente = WSMTXCAClient(str(cert_path), str(key_path))
    
    # Probar puntos de venta del 1 al 5
    for pv in range(1, 6):
        print(f"\n📍 Punto de Venta: {pv}")
        
        try:
            resultado = cliente.consultar_comprobante(
                cuit=cuit_martin,
                tipo=11,  # Factura C
                punto_venta=pv,
                numero=1
            )
            
            if resultado['status'] == 'encontrado':
                datos = resultado['datos']
                print(f"   ✅ PV{pv} - Factura encontrada")
                print(f"   💰 Total: ${datos.get('importe_total', '0')}")
            else:
                print(f"   📭 PV{pv} - No encontrado")
                
        except Exception as e:
            print(f"   ❌ PV{pv} - Error: {str(e)}")

if __name__ == "__main__":
    print("🧪 Test WSMTXCA - Martin Vega")
    print("=" * 50)
    
    # Test básico
    if test_wsmtxca_martin_vega():
        print(f"\n✅ Test básico completado")
        
        # Test puntos de venta
        test_consulta_puntos_venta()
    else:
        print(f"\n❌ Test básico falló")
    
    print(f"\n🏁 Pruebas completadas")