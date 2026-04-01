#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test rápido para CUIT 27312238018 con WSMTXCA
Verificar si tiene facturas con códigos MTX
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from wsmtxca_client import crear_cliente_wsmtxca

def test_cuit_wsmtxca():
    """Test rápido con WSMTXCA"""
    print("🧪 TEST RÁPIDO: WSMTXCA para CUIT 27312238018")
    print("=" * 60)
    
    cuit = "27312238018"
    
    try:
        print(f"🔍 Probando WSMTXCA para: {cuit}")
        
        # Crear cliente WSMTXCA
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        print("\n1️⃣ Probando consulta de comprobante...")
        
        # Probar algunos tipos y números comunes
        tipos_a_probar = [
            (1, "Factura A"),
            (6, "Factura B"), 
            (11, "Factura C"),
            (51, "Factura M"),
            (201, "Factura MiPyME A")
        ]
        
        for tipo, desc in tipos_a_probar:
            print(f"\n   🔍 Probando {desc} (tipo {tipo})...")
            
            for pv in [1, 2]:
                for num in [1, 2, 3]:
                    try:
                        resultado = client.consultar_comprobante(
                            cuit_representada=cuit,
                            tipo_comprobante=tipo,
                            punto_venta=pv,
                            numero_comprobante=num
                        )
                        
                        if resultado:
                            print(f"      ✅ ENCONTRADO: PV{pv} #{num}")
                            print(f"         Fecha: {resultado.get('fecha_emision', 'N/A')}")
                            print(f"         Total: ${resultado.get('importe_total', 'N/A')}")
                            print(f"         Receptor: {resultado.get('receptor_denominacion', 'N/A')}")
                            return True
                    except Exception as e:
                        if "401" in str(e) or "unauthorized" in str(e).lower():
                            print(f"      ❌ Sin autorización WSMTXCA")
                            return False
                        # Otros errores son normales (comprobante no existe)
                        pass
        
        print("\n📭 No se encontraron comprobantes en WSMTXCA")
        return False
        
    except Exception as e:
        print(f"\n❌ ERROR EN WSMTXCA: {e}")
        if "401" in str(e) or "unauthorized" in str(e).lower():
            print("💡 El certificado no tiene permisos para WSMTXCA")
        return False

def main():
    """Función principal"""
    print("🔍 INVESTIGACIÓN COMPLETA: CUIT 27312238018")
    print("=" * 60)
    
    # Test WSMTXCA
    wsmtxca_ok = test_cuit_wsmtxca()
    
    print("\n" + "="*60)
    print("📊 RESUMEN DE INVESTIGACIÓN")
    print("="*60)
    
    print(f"\n🔍 CUIT: 27312238018")
    print(f"✅ WSFEv1: Acceso OK, pero sin facturas")
    print(f"❌ WSFEXv1: Sin habilitación")
    
    if wsmtxca_ok:
        print(f"✅ WSMTXCA: Facturas encontradas")
        print(f"💡 Este CUIT usa códigos MTX especiales")
    else:
        print(f"❌ WSMTXCA: Sin acceso o sin facturas")
    
    print(f"\n💭 CONCLUSIÓN:")
    if not wsmtxca_ok:
        print("   - Este CUIT puede no tener facturación electrónica")
        print("   - O usa un servicio no habilitado en este certificado")
        print("   - O es un CUIT nuevo/inactivo")
    else:
        print("   - Este CUIT tiene facturas especiales con códigos MTX")
        print("   - Requiere WSMTXCA para consultas completas")
    
    print(f"\n🔧 PRÓXIMOS PASOS:")
    print("   1. Verificar en AFIP si el CUIT está activo")
    print("   2. Consultar qué régimen fiscal tiene (RI, Monotributo, etc.)")
    print("   3. Verificar si emite facturas electrónicas")

if __name__ == "__main__":
    main()