#!/usr/bin/env python3
"""
Probar la función extraer_facturas_simple con los parámetros correctos
"""

from afip_simple import extraer_facturas_simple

def test_extraccion_martin_vega():
    print("🎯 === PRUEBA EXTRACCIÓN MARTIN VEGA ===")
    print("CUIT Cliente: 23333730219 - VEGA, MARTIN MATIAS")
    print("CUIT Consultor: 20321518045 - CALEGARI ALBANO FEDERICO")
    print("------------------------------------------------------------")
    
    try:
        facturas = extraer_facturas_simple(
            cuit="23333730219",  # CUIT del cliente (Martin Vega)
            cuit_consultor="20321518045",  # CUIT del consultor (Albano)
            desde="2024-01-01",
            hasta="2025-09-30",
            cert_path=r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\certificado.crt",
            key_path=r"C:\Users\DELL\Desktop\proyectos python\infofiscal\certs\clave_privada.key"
        )
        
        print(f"✅ Extracción exitosa!")
        print(f"📊 Facturas encontradas: {len(facturas)}")
        
        if len(facturas) > 0:
            print(f"\n📋 Primeras facturas:")
            for i, factura in enumerate(facturas[:3]):
                print(f"   {i+1}. {factura}")
        else:
            print(f"\n💡 Sin facturas electrónicas encontradas")
            print(f"   • Cliente puede tener facturas de talonario (papel)")
            print(f"   • O no ha emitido facturas electrónicas")
        
    except Exception as e:
        print(f"❌ Error en extracción: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_extraccion_martin_vega()