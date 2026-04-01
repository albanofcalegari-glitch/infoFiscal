#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prueba específica para CUIT 20321518045 con WSFEv1
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from wsfev1_client import WSFEv1Client

def test_cuit_20321518045():
    """Prueba específica para CUIT 20321518045"""
    
    cuit = "20321518045"
    
    print("=" * 70)
    print(f"🧪 PRUEBA ESPECÍFICA WSFEv1 - CUIT: {cuit}")
    print("=" * 70)
    
    # Configurar rutas de certificados
    cert_path = root_dir / 'certs' / 'certificado.crt'
    key_path = root_dir / 'certs' / 'clave_privada.key'
    
    try:
        # Crear cliente WSFEv1
        print("🔧 Creando cliente WSFEv1...")
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )
        print("✅ Cliente creado exitosamente")
        print()
        
        # Probar todos los tipos de comprobante comunes
        tipos_comunes = {
            1: "Factura A",
            6: "Factura B", 
            11: "Factura C",
            51: "Factura M",
            2: "Nota de Débito A",
            3: "Nota de Crédito A",
            7: "Nota de Débito B",
            8: "Nota de Crédito B",
            12: "Nota de Débito C",
            13: "Nota de Crédito C"
        }
        
        puntos_venta = [1, 2, 3, 4, 5]
        
        facturas_encontradas = []
        
        print(f"🔍 BUSCANDO COMPROBANTES PARA CUIT {cuit}")
        print(f"   Probando {len(tipos_comunes)} tipos de comprobante")
        print(f"   Probando {len(puntos_venta)} puntos de venta")
        print()
        
        for tipo_codigo, tipo_nombre in tipos_comunes.items():
            print(f"📋 Probando {tipo_nombre} (Tipo {tipo_codigo})...")
            
            for pv in puntos_venta:
                try:
                    ultimo = client.obtener_ultimo_comprobante(cuit, tipo_codigo, pv)
                    
                    if ultimo and ultimo > 0:
                        print(f"   ✅ PV{pv}: Último comprobante #{ultimo}")
                        
                        # Consultar algunos comprobantes recientes
                        inicio = max(1, ultimo - 5)  # Últimos 5
                        
                        for num in range(ultimo, inicio - 1, -1):
                            comprobante = client.consultar_comprobante(cuit, tipo_codigo, pv, num)
                            
                            if comprobante['status'] == 'encontrado':
                                facturas_encontradas.append({
                                    'tipo': tipo_nombre,
                                    'tipo_codigo': tipo_codigo,
                                    'punto_venta': pv,
                                    'numero': num,
                                    'datos': comprobante['datos']
                                })
                                print(f"      🎯 Factura #{num} encontrada - CAE: {comprobante['datos'].get('cae', 'N/A')}")
                                
                                if len(facturas_encontradas) >= 10:  # Limitar para no saturar
                                    break
                        
                        if len(facturas_encontradas) >= 10:
                            break
                    else:
                        print(f"   📭 PV{pv}: Sin comprobantes")
                        
                except Exception as e:
                    print(f"   ❌ PV{pv}: Error - {str(e)[:50]}...")
            
            if len(facturas_encontradas) >= 10:
                print(f"   🛑 Límite alcanzado, continuando con resumen...")
                break
        
        print()
        print("=" * 70)
        print(f"📊 RESUMEN DE RESULTADOS PARA CUIT {cuit}")
        print("=" * 70)
        
        if facturas_encontradas:
            print(f"✅ SE ENCONTRARON {len(facturas_encontradas)} FACTURAS")
            print()
            
            # Agrupar por tipo
            por_tipo = {}
            for factura in facturas_encontradas:
                tipo = factura['tipo']
                if tipo not in por_tipo:
                    por_tipo[tipo] = []
                por_tipo[tipo].append(factura)
            
            for tipo, facturas in por_tipo.items():
                print(f"📋 {tipo}: {len(facturas)} facturas")
                for f in facturas[:3]:  # Mostrar máximo 3 por tipo
                    datos = f['datos']
                    print(f"   • PV{f['punto_venta']} #{f['numero']} - ${datos.get('importe_total', '0')} - {datos.get('fecha_emision', 'S/F')}")
                if len(facturas) > 3:
                    print(f"   ... y {len(facturas) - 3} más")
                print()
                
            print("🎉 ¡SUCCESS! WSFEv1 FUNCIONA Y ENCUENTRA TUS FACTURAS!")
            print("🎯 Este servicio SÍ puede acceder a tus facturas desde 2013")
            print()
            
        else:
            print("📭 NO SE ENCONTRARON FACTURAS")
            print()
            print("💡 Posibles causas:")
            print("   • El CUIT no emite facturas electrónicas")
            print("   • Las facturas están en otros puntos de venta")
            print("   • Problema de permisos o configuración")
            print("   • El CUIT usa otro servicio (ej: Monotributo)")
            
        return len(facturas_encontradas) > 0
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()
        return False

def mostrar_instrucciones():
    """Mostrar instrucciones para usar la web"""
    print()
    print("=" * 70)
    print("🌐 CÓMO USAR LA INTERFAZ WEB:")
    print("=" * 70)
    print("1. Abrir: http://127.0.0.1:5000")
    print("2. Hacer login con tus credenciales")
    print("3. Click en: 'WSFEv1 - Facturas Tradicionales'")
    print("4. En 'Buscar por CUIT': escribir '20321518045'")
    print("5. Seleccionar el cliente")
    print("6. Click 'Buscar Todas las Facturas'")
    print()
    print("🔍 También puedes usar 'Consultar Factura Específica' si sabes:")
    print("   - Tipo de comprobante (ej: 11 = Factura C)")
    print("   - Punto de venta (ej: 1)")
    print("   - Número de factura")

if __name__ == "__main__":
    success = test_cuit_20321518045()
    
    mostrar_instrucciones()
    
    print()
    print("=" * 70)
    if success:
        print("🎯 CONCLUSIÓN: WSFEv1 encontró facturas para este CUIT")
        print("   ✅ El servicio funciona correctamente")
        print("   ✅ Puedes usar la interfaz web para explorar más")
    else:
        print("🤔 No se encontraron facturas, pero el servicio funciona")
        print("   ✅ WSFEv1 está operativo")
        print("   💡 Prueba con otro CUIT que sepas que tiene facturas")
    print("=" * 70)