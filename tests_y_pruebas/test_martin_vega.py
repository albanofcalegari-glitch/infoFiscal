#!/usr/bin/env python3
"""
Script para probar extracción AFIP con el CUIT de Martín Vega
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from afip_simple import extraer_facturas_simple, export_simple

def test_martin_vega():
    print("🧪 === PRUEBA CON CUIT DE MARTÍN VEGA ===")
    
    # CUIT de consultor (tu certificado para autenticación)
    cuit_consultor = "20321518045"  # Tu CUIT con certificado
    
    # CUIT de cliente a consultar (Martín Vega)  
    cuit_martin = "23333730219"
    
    print(f"CUIT consultor (autenticación): {cuit_consultor}")
    print(f"CUIT a consultar (cliente): {cuit_martin}")
    print("Tipo: Responsable Inscripto")
    print("-" * 50)
    
    # Usar un rango de fechas amplio
    fecha_desde = "2020-01-01"
    fecha_hasta = "2025-09-30"
    
    try:
        # Usar tu certificado para autenticar pero consultar facturas de Martín
        comprobantes = extraer_facturas_simple(
            cuit=cuit_martin,           # CUIT a consultar (Martín Vega)
            cuit_consultor=cuit_consultor,  # CUIT para autenticación (tu certificado)
            desde=fecha_desde,
            hasta=fecha_hasta
        )
        
        print(f"\n🎉 RESULTADO:")
        print(f"Total de comprobantes encontrados: {len(comprobantes)}")
        
        if comprobantes:
            # Mostrar resumen
            pv_summary = {}
            tipo_summary = {}
            
            for comp in comprobantes:
                pv = comp.get('PtoVta', 'Unknown')
                tipo = comp.get('CbteTipo', 'Unknown')
                
                pv_summary[pv] = pv_summary.get(pv, 0) + 1
                tipo_summary[tipo] = tipo_summary.get(tipo, 0) + 1
            
            print("\n📊 Resumen por punto de venta:")
            for pv in sorted(pv_summary.keys()):
                print(f"   PV {pv}: {pv_summary[pv]} comprobantes")
            
            print("\n📋 Resumen por tipo de comprobante:")
            for tipo in sorted(tipo_summary.keys()):
                print(f"   Tipo {tipo}: {tipo_summary[tipo]} comprobantes")
            
            # Exportar a archivos
            print(f"\n💾 Exportando resultados...")
            archivos = export_simple(comprobantes, f"facturas/martin_vega_{cuit_martin}")
            print(f"   CSV: {archivos['csv']}")
            print(f"   JSON: {archivos['json']}")
        else:
            print("   No se encontraron comprobantes en el rango especificado")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_martin_vega()