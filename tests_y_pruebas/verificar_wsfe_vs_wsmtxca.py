#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Verificar si el certificado tiene acceso a WSFEv1 vs WSMTXCA
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from afip_simple import extraer_facturas_simple

def test_wsfe_vs_wsmtxca():
    """
    Comparar WSFEv1 (que debería funcionar) vs WSMTXCA (que falla)
    """
    print("🔍 Diagnóstico: WSFEv1 vs WSMTXCA")
    print("=" * 50)
    
    cert_path = Path(__file__).parent / 'certs' / 'certificado.crt'
    key_path = Path(__file__).parent / 'certs' / 'clave_privada.key'
    cuit_martin = "27291928698"
    
    print(f"📋 Probando con CUIT: {cuit_martin}")
    print(f"📄 Certificado: {cert_path}")
    
    # Test 1: WSFEv1 (debería funcionar)
    print(f"\n1️⃣ Probando WSFEv1 (facturas tradicionales)")
    print("-" * 30)
    
    try:
        facturas = extraer_facturas_simple(
            cuit=cuit_martin,
            desde=1,
            hasta=5,
            punto_venta=1,
            cert_path=str(cert_path),
            key_path=str(key_path),
            max_por_tipo=3
        )
        
        if facturas and len(facturas) > 0:
            print(f"✅ WSFEv1 FUNCIONA - {len(facturas)} facturas encontradas")
            for i, f in enumerate(facturas[:2], 1):
                print(f"   {i}. Tipo {f.get('tipo', 'N/A')} - CAE: {f.get('cae', 'N/A')}")
                print(f"      Fecha: {f.get('fecha_emision', 'N/A')} - ${f.get('importe_total', 0)}")
        else:
            print(f"📭 WSFEv1 - No encontró facturas (pero autenticó correctamente)")
            
    except Exception as e:
        if "500" in str(e):
            print(f"❌ WSFEv1 - Error de permisos: {str(e)}")
        else:
            print(f"❌ WSFEv1 - Error técnico: {str(e)}")
    
    # Test 2: WSMTXCA (sabemos que falla)
    print(f"\n2️⃣ Recordatorio sobre WSMTXCA")
    print("-" * 30)
    print(f"❌ WSMTXCA falla por falta de permisos (HTTP 500)")
    print(f"💡 WSMTXCA es solo para facturas CON CÓDIGOS MTX")
    print(f"💡 Requiere habilitación específica en AFIP Admin")
    
    print(f"\n📊 Conclusión:")
    print(f"   • WSFEv1: Para facturas normales (2013+)")
    print(f"   • WSMTXCA: Para facturas con códigos MTX (requiere permisos)")

if __name__ == "__main__":
    test_wsfe_vs_wsmtxca()