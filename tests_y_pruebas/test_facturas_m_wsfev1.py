#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test práctico: Buscar facturas M usando WSFEv1
Muchas veces las facturas M se pueden consultar también a través del servicio WSFEv1 tradicional
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from wsfev1_client import WSFEv1Client

def test_buscar_facturas_m_con_wsfev1():
    """Buscar facturas M usando el servicio WSFEv1 tradicional"""
    print("🧪 TEST: Buscar Facturas M con WSFEv1")
    print("=" * 50)
    
    # Configuración - ajusta tu CUIT
    cuit = "20321518045"
    
    try:
        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        print(f"🔍 Buscando facturas para CUIT: {cuit}")
        
        # 1. Verificar autenticación
        print("\n1️⃣ Verificando autenticación WSFEv1...")
        token, sign = client.autenticar_wsaa(cuit)
        print(f"✅ Token obtenido: {token[:20]}...")
        
        # 2. Usar puntos de venta típicos
        print("\n2️⃣ Usando puntos de venta típicos...")
        puntos = [1, 2, 3, 4, 5]  # Puntos más comunes
        print(f"📍 Puntos a probar: {puntos}")
        
        # 3. Buscar facturas M (tipo 51) en cada punto de venta
        print("\n3️⃣ Buscando Facturas M (tipo 51)...")
        facturas_m_encontradas = []
        
        for punto in puntos[:3]:  # Probar primeros 3 puntos
            print(f"\n   🔍 Buscando en punto de venta {punto}...")
            
            try:
                # Obtener último autorizado para tipo 51 (Factura M)
                ultimo = client.obtener_ultimo_comprobante(cuit, 51, punto)
                print(f"      Último autorizado tipo 51: {ultimo}")
                
                if ultimo and ultimo > 0:
                    # Probar las últimas 5 facturas
                    desde = max(1, ultimo - 4)
                    hasta = ultimo
                    
                    for num in range(desde, hasta + 1):
                        try:
                            factura = client.consultar_comprobante(cuit, 51, punto, num)
                            if factura:
                                facturas_m_encontradas.append({
                                    'punto_venta': punto,
                                    'numero': num,
                                    'tipo': 51,
                                    'descripcion': 'Factura M',
                                    'fecha_emision': factura.get('fecha_emision', 'N/A'),
                                    'cae': factura.get('cae', 'N/A'),
                                    'receptor_cuit': factura.get('receptor_cuit', 'N/A'),
                                    'receptor_denominacion': factura.get('receptor_denominacion', 'N/A'),
                                    'importe_total': factura.get('importe_total', 'N/A')
                                })
                                print(f"      ✅ Factura M #{num}: CAE {factura.get('cae', 'N/A')[:15]}...")
                        except Exception as e:
                            print(f"      ⚠️ Factura M #{num}: {e}")
                            
                else:
                    print(f"      📭 No hay facturas M en PV {punto}")
                    
            except Exception as e:
                print(f"      ❌ Error en PV {punto}: {e}")
        
        # 4. Buscar también otros tipos relacionados con monotributo
        print("\n4️⃣ Buscando otros tipos de Monotributo...")
        tipos_monotributo = [
            (52, "Nota de Débito M"),
            (53, "Nota de Crédito M"),
            (54, "Recibo M"),
            (55, "Nota de Venta al Contado M")
        ]
        
        for tipo, descripcion in tipos_monotributo:
            print(f"\n   🔍 Buscando {descripcion} (tipo {tipo})...")
            
            for punto in puntos[:2]:  # Solo primeros 2 puntos para otros tipos
                try:
                    ultimo = client.obtener_ultimo_comprobante(cuit, tipo, punto)
                    if ultimo and ultimo > 0:
                        print(f"      ✅ PV {punto}: Último {descripcion} #{ultimo}")
                        
                        # Consultar el último
                        comprobante = client.consultar_comprobante(cuit, tipo, punto, ultimo)
                        if comprobante:
                            facturas_m_encontradas.append({
                                'punto_venta': punto,
                                'numero': ultimo,
                                'tipo': tipo,
                                'descripcion': descripcion,
                                'fecha_emision': comprobante.get('fecha_emision', 'N/A'),
                                'cae': comprobante.get('cae', 'N/A'),
                                'importe_total': comprobante.get('importe_total', 'N/A')
                            })
                except Exception as e:
                    print(f"      ⚠️ PV {punto}: {e}")
        
        # 5. Mostrar resumen
        print("\n5️⃣ RESUMEN DE RESULTADOS")
        print("=" * 40)
        
        if facturas_m_encontradas:
            print(f"🎉 ¡ÉXITO! Se encontraron {len(facturas_m_encontradas)} comprobantes de monotributo:")
            print()
            
            for i, factura in enumerate(facturas_m_encontradas, 1):
                print(f"   {i}. {factura['descripcion']} - PV:{factura['punto_venta']} #{factura['numero']}")
                print(f"      CAE: {factura['cae']}")
                print(f"      Fecha: {factura['fecha_emision']}")
                if factura['importe_total'] != 'N/A':
                    print(f"      Importe: ${factura['importe_total']}")
                if 'receptor_denominacion' in factura and factura['receptor_denominacion'] != 'N/A':
                    print(f"      Cliente: {factura['receptor_denominacion']}")
                print()
                
            return True
        else:
            print("📭 No se encontraron comprobantes de monotributo")
            print("\n💡 Posibles causas:")
            print("   - El CUIT no está en régimen de monotributo")
            print("   - No se han emitido facturas M aún")
            print("   - Las facturas M están en un servicio diferente (WSFEXv1)")
            return False
            
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        return False

def comparar_servicios_practico():
    """Comparación práctica de servicios"""
    print("\n" + "="*60)
    print("📊 GUÍA PRÁCTICA: ¿Qué servicio usar?")
    print("="*60)
    
    print("\n🎯 PARA MONOTRIBUTISTAS:")
    print("   1️⃣ Primero probar WSFEv1 (lo que acabamos de hacer)")
    print("      ✅ Más simple, usa el mismo certificado")
    print("      ✅ Muchas veces las facturas M están aquí")
    print("      ❌ No siempre funciona para todos los monotributistas")
    
    print("\n   2️⃣ Si WSFEv1 no funciona, usar WSFEXv1")
    print("      ✅ Servicio específico para monotributo")
    print("      ✅ Soporta exportación también")
    print("      ❌ Requiere habilitación específica en AFIP")
    
    print("\n🎯 PARA RESPONSABLES INSCRIPTOS:")
    print("   ✅ Usar WSFEv1 siempre")
    print("   ✅ Facturas A, B, C están garantizadas aquí")
    
    print("\n🎯 PARA EXPORTADORES:")
    print("   ✅ Usar WSFEXv1 obligatoriamente")
    print("   ✅ Facturas de exportación (tipos 19, 20, 21)")

def main():
    """Función principal"""
    print("🚀 TEST PRÁCTICO: Facturas M con WSFEv1")
    print("=" * 60)
    
    # Test principal
    exito = test_buscar_facturas_m_con_wsfev1()
    
    # Comparación práctica
    comparar_servicios_practico()
    
    # Conclusión
    print("\n" + "="*60)
    print("🎯 CONCLUSIÓN")
    print("="*60)
    
    if exito:
        print("✅ ¡PERFECTO! Las facturas M se pueden consultar con WSFEv1")
        print("✅ No necesitas WSFEXv1 para este CUIT")
        print("✅ Tu aplicación ya puede manejar facturas de monotributo")
        
        print("\n📝 PRÓXIMOS PASOS:")
        print("   1. Integrar búsqueda de facturas M en tu app web")
        print("   2. Agregar filtros por tipo de comprobante")
        print("   3. Crear vista específica para monotributo")
        
    else:
        print("⚠️ Las facturas M no están disponibles en WSFEv1")
        print("💡 Necesitas habilitar WSFEXv1 en AFIP:")
        print("   1. Ir a https://auth.afip.gob.ar/contribuyente_sin_clave")
        print("   2. Admin de Relaciones → Generar nueva relación")
        print("   3. Buscar servicio 'WSFEXv1' o 'Facturación Electrónica Exportación'")
        print("   4. Asociar tu certificado al servicio")
        
    print("\n🔧 INFO TÉCNICA:")
    print(f"   - WSFEv1 URL: https://servicios1.afip.gov.ar/wsfev1/service.asmx")
    print(f"   - WSFEXv1 URL: https://servicios1.afip.gov.ar/wsfexv1/service.asmx")
    print(f"   - Ambos usan el mismo WSAA para autenticación")

if __name__ == "__main__":
    main()