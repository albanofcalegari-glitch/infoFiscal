#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificar si la autenticación WSAA funciona antes de probar WSMTXCA
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from afip_simple import extraer_facturas_simple, wsaa_auth_simple
import json

def test_wsaa_basico():
    """
    Probar autenticación WSAA básica
    """
    print("🔐 Verificando autenticación WSAA básica")
    print("-" * 50)
    
    try:
        cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
        
        print(f"📁 Certificado: {cert_path}")
        print(f"🔑 Clave: {key_path}")
        
        # Intentar autenticación WSAA
        print(f"🔐 Autenticando WSAA...")
        
        # Usar la función de autenticación simple
        auth_result = wsaa_auth_simple(str(cert_path), str(key_path))
        
        if auth_result and 'token' in auth_result and 'sign' in auth_result:
            print(f"✅ Autenticación WSAA exitosa")
            print(f"   Token: {auth_result['token'][:50]}...")
            print(f"   Sign: {auth_result['sign'][:50]}...")
            return True
        else:
            print(f"❌ Error en autenticación WSAA: {auth_result}")
            return False
        
    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_consulta_wsfe_completa():
    """
    Hacer una consulta completa en WSFEv1 para verificar que todo funciona
    """
    print(f"\n📋 Verificando consulta completa WSFEv1")
    print("-" * 50)
    
    try:
        cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
        key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
        cuit_martin = "27291928698"
        
        # Usar función de extracción que maneja todo internamente
        print(f"📄 Extrayendo facturas para CUIT {cuit_martin}...")
        
        facturas = extraer_facturas_simple(
            cuit=cuit_martin,
            desde=1,
            hasta=5,
            punto_venta=1,
            cert_path=str(cert_path),
            key_path=str(key_path),
            max_por_tipo=5
        )
        
        if facturas and len(facturas) > 0:
            print(f"✅ {len(facturas)} facturas encontradas")
            primer_factura = facturas[0]
            print(f"   Primera factura:")
            print(f"   CAE: {primer_factura.get('cae', 'N/A')}")
            print(f"   Fecha: {primer_factura.get('fecha_emision', 'N/A')}")
            print(f"   Total: ${primer_factura.get('importe_total', '0')}")
            return True
        else:
            print(f"📭 No se encontraron facturas")
            return False
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🧪 Test de verificación WSAA")
    print("=" * 50)
    
    # Verificar autenticación básica
    if test_wsaa_basico():
        print(f"\n✅ WSAA funciona correctamente")
        
        # Hacer test completo
        if test_consulta_wsfe_completa():
            print(f"\n✅ WSFEv1 funciona completamente")
            print(f"\n💡 El problema podría ser específico de WSMTXCA")
            print(f"   - WSAA funciona (WSFEv1 OK)")
            print(f"   - Certificados OK") 
            print(f"   - Revisar implementación WSMTXCA")
        else:
            print(f"\n⚠️ WSFEv1 tiene problemas en consultas")
    else:
        print(f"\n❌ WSAA no funciona")
        print(f"   - Verificar certificados")
        print(f"   - Verificar conectividad")
        print(f"   - Verificar configuración ambiente")
    
    print(f"\n🏁 Verificación completada")