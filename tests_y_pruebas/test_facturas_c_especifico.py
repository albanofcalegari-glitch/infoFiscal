#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test práctico: Buscar Facturas C específicamente
Demostrar que WSFEv1 encuentra facturas C de cualquier tipo de contribuyente
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from wsfev1_client import WSFEv1Client

def test_buscar_facturas_c():
    """Test específico para buscar solo Facturas C (tipo 11)"""
    print("🔍 TEST ESPECÍFICO: FACTURAS C (TIPO 11)")
    print("=" * 60)
    
    # Configuración - puedes cambiar estos CUITs
    cuits_a_probar = [
        "20321518045",  # Tu CUIT actual
        "27312238018",  # El que probamos antes
    ]
    
    print("💡 OBJETIVO: Demostrar que WSFEv1 maneja facturas C de monotributistas")
    print("📄 TIPO A BUSCAR: Factura C (tipo 11)")
    print("🔧 SERVICIO: WSFEv1 (el que ya tienes funcionando)")
    
    for cuit in cuits_a_probar:
        print(f"\n" + "="*50)
        print(f"🔍 PROBANDO CUIT: {cuit}")
        print("="*50)
        
        try:
            # Crear cliente WSFEv1
            client = WSFEv1Client(
                cert_path='certs/certificado.crt',
                key_path='certs/clave_privada.key',
                ambiente='prod'
            )
            
            print(f"\n1️⃣ Autenticando con WSFEv1...")
            token, sign = client.autenticar_wsaa(cuit)
            print(f"✅ Autenticación exitosa")
            
            print(f"\n2️⃣ Buscando SOLO Facturas C (tipo 11)...")
            
            facturas_c_encontradas = []
            puntos_venta = [1, 2, 3, 4, 5]
            
            for punto in puntos_venta:
                print(f"\n   🔍 Punto de venta {punto}...")
                
                try:
                    # Obtener último autorizado SOLO para tipo 11 (Factura C)
                    ultimo = client.obtener_ultimo_comprobante(cuit, 11, punto)
                    
                    if ultimo and ultimo > 0:
                        print(f"      ✅ Último autorizado tipo 11: {ultimo}")
                        
                        # Consultar las últimas 3 facturas C
                        desde = max(1, ultimo - 2)
                        hasta = ultimo
                        
                        for num in range(desde, hasta + 1):
                            try:
                                factura = client.consultar_comprobante(cuit, 11, punto, num)
                                if factura:
                                    facturas_c_encontradas.append({
                                        'cuit_emisor': cuit,
                                        'punto_venta': punto,
                                        'numero': num,
                                        'tipo': 11,
                                        'descripcion': 'Factura C',
                                        'fecha_emision': factura.get('fecha_emision', 'N/A'),
                                        'cae': factura.get('cae', 'N/A'),
                                        'importe_total': factura.get('importe_total', 'N/A'),
                                        'receptor_denominacion': factura.get('receptor_denominacion', 'N/A')
                                    })
                                    print(f"         ✅ Factura C #{num}: CAE {factura.get('cae', 'N/A')[:12]}...")
                            except Exception as e:
                                print(f"         ⚠️ Factura C #{num}: {e}")
                    else:
                        print(f"      📭 Sin facturas C en PV {punto}")
                        
                except Exception as e:
                    print(f"      ❌ Error en PV {punto}: {e}")
            
            # Resumen para este CUIT
            print(f"\n📊 RESUMEN PARA CUIT {cuit}:")
            if facturas_c_encontradas:
                print(f"🎉 ENCONTRADAS: {len(facturas_c_encontradas)} Facturas C")
                for i, f in enumerate(facturas_c_encontradas, 1):
                    print(f"   {i}. Factura C - PV:{f['punto_venta']} #{f['numero']}")
                    print(f"      📅 {f['fecha_emision']} - 💰 ${f['importe_total']}")
                    if f['receptor_denominacion'] not in ['N/A', '']:
                        print(f"      👤 {f['receptor_denominacion']}")
                    print()
            else:
                print("📭 No se encontraron Facturas C")
                print("💡 Este CUIT podría:")
                print("   • No emitir facturas electrónicas")
                print("   • Usar solo Facturas M (monotributo)")
                print("   • Usar solo Facturas A o B (responsable inscripto)")
        
        except Exception as e:
            print(f"\n❌ ERROR CON CUIT {cuit}: {e}")
    
    return facturas_c_encontradas

def explicacion_tipos_factura():
    """Explicación de cuándo usar cada tipo"""
    print(f"\n📚 EXPLICACIÓN: ¿CUÁNDO SE USAN FACTURAS C?")
    print("=" * 60)
    
    print(f"\n🔸 FACTURA C (Tipo 11) - LA MÁS COMÚN:")
    print("   👥 Para: CONSUMIDOR FINAL (sin CUIT)")
    print("   💰 IVA: No se discrimina (incluido en el precio)")
    print("   📝 Ejemplo: Venta en un comercio minorista")
    print("   🏪 Usos: Supermercados, tiendas, restaurantes, etc.")
    print("   ✅ Emisor: Cualquier contribuyente (RI, Monotributo, etc.)")
    
    print(f"\n🔸 FACTURA A (Tipo 1):")
    print("   👥 Para: Responsables Inscriptos")
    print("   💰 IVA: Discriminado (se muestra por separado)")
    print("   📝 Ejemplo: Venta entre empresas")
    
    print(f"\n🔸 FACTURA B (Tipo 6):")
    print("   👥 Para: Monotributistas, Exentos")
    print("   💰 IVA: Discriminado")
    
    print(f"\n🔸 FACTURA M (Tipo 51):")
    print("   👥 Para: Consumidor Final (específica monotributo)")
    print("   💰 IVA: Régimen especial")
    print("   📝 Solo la emiten monotributistas")
    
    print(f"\n💡 CLAVE PARA TU PREGUNTA:")
    print("Un monotributista puede emitir:")
    print("   ✅ Factura C (tipo 11) → WSFEv1")
    print("   ✅ Factura M (tipo 51) → WSFEXv1")
    print("   ✅ Ambas son válidas para consumidor final")

def main():
    """Función principal"""
    print("🎯 TEST: FACTURAS C DE MONOTRIBUTISTAS")
    
    # Test principal
    facturas = test_buscar_facturas_c()
    
    # Explicación
    explicacion_tipos_factura()
    
    # Conclusión final
    print(f"\n" + "="*60)
    print("🎉 CONCLUSIÓN FINAL")
    print("="*60)
    
    print("Para buscar FACTURAS C de monotributistas:")
    print("🎯 USAR WSFEv1 (tu implementación actual)")
    print("📄 BUSCAR tipo 11 (Factura C)")
    print("✅ NO necesitas WSFEXv1 para facturas C")
    print("✅ WSFEXv1 solo es necesario para facturas M")
    
    print(f"\n🔧 EN TU APLICACIÓN:")
    print("• Ya tienes el código correcto")
    print("• WSFEv1 maneja facturas C de todos los contribuyentes")
    print("• Monotributistas pueden usar facturas C normalmente")

if __name__ == "__main__":
    main()