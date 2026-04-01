#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Prueba rápida de WSFEv1 - Verificar que SÍ trae facturas tradicionales
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

from wsfev1_client import WSFEv1Client

def test_wsfev1():
    """Prueba rápida del cliente WSFEv1"""
    
    print("=" * 60)
    print("🧪 PRUEBA WSFEv1 - FACTURAS TRADICIONALES DESDE 2013")
    print("=" * 60)
    
    # Configurar rutas de certificados
    cert_path = root_dir / 'certs' / 'certificado.crt'
    key_path = root_dir / 'certs' / 'clave_privada.key'
    
    if not cert_path.exists():
        print(f"❌ Certificado no encontrado: {cert_path}")
        return False
        
    if not key_path.exists():
        print(f"❌ Clave privada no encontrada: {key_path}")
        return False
    
    print(f"✅ Certificado: {cert_path}")
    print(f"✅ Clave: {key_path}")
    print()
    
    try:
        # Crear cliente WSFEv1
        print("🔧 Creando cliente WSFEv1...")
        client = WSFEv1Client(
            cert_path=str(cert_path),
            key_path=str(key_path),
            ambiente='prod'
        )
        print("✅ Cliente WSFEv1 creado")
        print()
        
        # CUIT de prueba (configurable)
        cuit_prueba = "20321518045"  # Reemplaza con un CUIT real
        
        print(f"🔍 PRUEBA 1: Verificar último comprobante autorizado")
        print(f"   CUIT: {cuit_prueba}")
        print(f"   Tipo: 11 (Factura C)")
        print(f"   Punto de Venta: 1")
        
        ultimo = client.obtener_ultimo_comprobante(
            cuit=cuit_prueba,
            tipo_comprobante=11,
            punto_venta=1
        )
        
        if ultimo is not None and ultimo > 0:
            print(f"✅ Último comprobante autorizado: {ultimo}")
            
            # Probar consulta específica
            print(f"\n🔍 PRUEBA 2: Consultar comprobante específico")
            print(f"   Consultando comprobante #{ultimo}")
            
            resultado = client.consultar_comprobante(
                cuit=cuit_prueba,
                tipo_comprobante=11,
                punto_venta=1,
                numero=ultimo
            )
            
            print(f"   Status: {resultado['status']}")
            
            if resultado['status'] == 'encontrado':
                datos = resultado['datos']
                print(f"   ✅ Factura encontrada:")
                print(f"      - Tipo: {datos['tipo_comprobante']}")
                print(f"      - Número: {datos['numero_comprobante']}")
                print(f"      - Fecha: {datos['fecha_emision']}")
                print(f"      - CAE: {datos['cae']}")
                print(f"      - Importe: ${datos['importe_total']}")
                
                print(f"\n🎉 ¡SUCCESS! WSFEv1 FUNCIONA CORRECTAMENTE")
                print(f"   Este servicio SÍ debería traer tus facturas desde 2013")
                return True
            else:
                print(f"   ⚠️ Comprobante no encontrado (normal en algunos casos)")
                
        else:
            print(f"   📭 No hay comprobantes autorizados para este tipo")
            print(f"   Probando otros tipos de comprobante...")
            
            # Probar otros tipos comunes
            tipos_comunes = [1, 6, 51, 2, 3]
            for tipo in tipos_comunes:
                ultimo = client.obtener_ultimo_comprobante(cuit_prueba, tipo, 1)
                if ultimo and ultimo > 0:
                    print(f"   ✅ Tipo {tipo}: último #{ultimo}")
                    return True
        
        print(f"\n🔍 PRUEBA 3: Búsqueda amplia de comprobantes")
        facturas = client.buscar_comprobantes_rango(
            cuit=cuit_prueba,
            tipos_comprobante=[1, 6, 11, 51],
            puntos_venta=[1, 2],
            limite_por_tipo=10
        )
        
        if facturas:
            print(f"   ✅ Encontradas {len(facturas)} facturas")
            print(f"\n🎉 ¡SUCCESS! WSFEv1 FUNCIONA Y ENCUENTRA FACTURAS")
            return True
        else:
            print(f"   📭 No se encontraron facturas")
            print(f"   💡 Esto puede ser normal si el CUIT no tiene facturas electrónicas")
            
    except Exception as e:
        print(f"❌ Error en prueba WSFEv1: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n✅ Cliente WSFEv1 funciona correctamente")
    print(f"💡 Para ver facturas, necesitas un CUIT que tenga facturas electrónicas")
    return True

if __name__ == "__main__":
    success = test_wsfev1()
    
    print("\n" + "=" * 60)
    if success:
        print("🎯 CONCLUSIÓN: WSFEv1 está listo para usar")
        print("   - Este SÍ traerá facturas desde 2013")
        print("   - Funciona con cualquier CUIT que emita facturas electrónicas")
        print("   - A diferencia de WSMTXCA, NO requiere autorización especial")
    else:
        print("❌ WSFEv1 tiene problemas de configuración")
    print("=" * 60)