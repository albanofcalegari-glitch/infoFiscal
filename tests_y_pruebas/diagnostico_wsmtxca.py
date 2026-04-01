#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test WSMTXCA paso a paso para diagnosticar el problema
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from wsmtxca_client import WSMTXCAClient
import json

def test_wsmtxca_homologacion():
    """
    Probar WSMTXCA en homologación primero
    """
    print("🧪 Test WSMTXCA en Homologación")
    print("-" * 50)
    
    try:
        # Usar homologación primero
        cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
        
        print(f"📁 Certificado: {cert_path}")
        print(f"🔑 Clave: {key_path}")
        
        # Crear cliente WSMTXCA en HOMOLOGACIÓN
        cliente = WSMTXCAClient(str(cert_path), str(key_path), ambiente='homo')
        print(f"✅ Cliente WSMTXCA creado (HOMOLOGACIÓN)")
        
        # Datos de prueba para homologación
        cuit_test = "20111111112"  # CUIT de prueba común en homologación
        
        print(f"🔐 Autenticando WSAA en homologación...")
        try:
            token = cliente.autenticar_wsaa(cuit_test)
            if token:
                print(f"✅ Autenticación exitosa en homologación")
                
                # Intentar consulta simple
                print(f"📋 Probando consulta básica...")
                resultado = cliente.consultar_comprobante(
                    cuit=cuit_test,
                    tipo=11,  # Factura C
                    punto_venta=1,
                    numero=1
                )
                
                print(f"✅ Consulta completada - Status: {resultado['status']}")
                return True
                
            else:
                print(f"❌ Error en autenticación homologación")
                return False
                
        except Exception as e:
            print(f"❌ Error en autenticación: {str(e)}")
            return False
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_wsmtxca_produccion():
    """
    Probar WSMTXCA en producción con datos reales
    """
    print(f"\n🏭 Test WSMTXCA en Producción")
    print("-" * 50)
    
    try:
        cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
        
        # Crear cliente WSMTXCA en PRODUCCIÓN
        cliente = WSMTXCAClient(str(cert_path), str(key_path), ambiente='prod')
        print(f"✅ Cliente WSMTXCA creado (PRODUCCIÓN)")
        
        # Datos de Martin Vega
        cuit_martin = "27291928698"
        
        print(f"🔐 Autenticando WSAA en producción (CUIT: {cuit_martin})...")
        try:
            token = cliente.autenticar_wsaa(cuit_martin)
            if token:
                print(f"✅ Autenticación exitosa en producción")
                
                # Intentar consulta
                print(f"📋 Probando consulta con datos reales...")
                resultado = cliente.consultar_comprobante(
                    cuit=cuit_martin,
                    tipo=11,  # Factura C
                    punto_venta=1,
                    numero=1
                )
                
                print(f"✅ Consulta completada - Status: {resultado['status']}")
                
                if resultado['status'] == 'encontrado':
                    print(f"   📋 Comprobante encontrado!")
                    print(f"   CAE: {resultado['datos'].get('cae', 'N/A')}")
                else:
                    print(f"   📭 Comprobante no encontrado (normal)")
                
                return True
                
            else:
                print(f"❌ Error en autenticación producción")
                return False
                
        except Exception as e:
            print(f"❌ Error específico: {str(e)}")
            if "500" in str(e):
                print(f"   💡 HTTP 500 indica problema de servicio o permisos")
                print(f"   - Verificar si el certificado tiene acceso a WSMTXCA")
                print(f"   - Contactar AFIP para habilitar el servicio")
            return False
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        return False

def diagnosticar_problema():
    """
    Diagnosticar el problema paso a paso
    """
    print(f"\n🔍 Diagnóstico WSMTXCA")
    print("-" * 50)
    
    print(f"1. ✅ WSAA funciona (verificado anteriormente)")
    print(f"2. ✅ Certificados válidos")  
    print(f"3. ⚠️ WSMTXCA produce HTTP 500")
    print(f"")
    print(f"💡 Posibles causas del HTTP 500:")
    print(f"   a) El certificado NO tiene permisos para WSMTXCA")
    print(f"   b) El servicio WSMTXCA no está habilitado para este CUIT")
    print(f"   c) Problema temporario en el servicio AFIP")
    print(f"   d) Diferencias en la implementación WSMTXCA vs WSFEv1")
    print(f"")
    print(f"🔧 Soluciones sugeridas:")
    print(f"   1. Verificar en AFIP Admin si WSMTXCA está habilitado")
    print(f"   2. Probar primero en homologación")  
    print(f"   3. Verificar documentación específica de WSMTXCA")
    print(f"   4. Contactar soporte AFIP si es necesario")

if __name__ == "__main__":
    print("🧪 Diagnóstico completo WSMTXCA")
    print("=" * 50)
    
    # Probar homologación primero
    if test_wsmtxca_homologacion():
        print(f"\n✅ WSMTXCA funciona en homologación")
        
        # Ahora probar producción
        if test_wsmtxca_produccion():
            print(f"\n✅ WSMTXCA funciona completamente")
        else:
            print(f"\n⚠️ WSMTXCA falla en producción")
    else:
        print(f"\n❌ WSMTXCA falla en homologación")
    
    # Diagnóstico
    diagnosticar_problema()
    
    print(f"\n🏁 Diagnóstico completado")