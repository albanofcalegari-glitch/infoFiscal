#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test: Verificar tipo de CUIT y qué facturas tiene disponibles
Determinar si es Responsable Inscripto, Monotributista o ambos
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from wsfev1_client import WSFEv1Client

def diagnosticar_cuit_completo():
    """Diagnóstico completo para determinar el tipo de CUIT y qué facturas tiene"""
    print("🩺 DIAGNÓSTICO COMPLETO DE CUIT")
    print("=" * 60)
    
    # Configuración - ajusta tu CUIT
    cuit = "27312238018"
    
    try:
        # Crear cliente WSFEv1
        client = WSFEv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        print(f"🔍 Analizando CUIT: {cuit}")
        print(f"🔧 Servicio: WSFEv1 (Facturación Electrónica v1)")
        
        # 1. Autenticación
        print("\n1️⃣ Verificando acceso a AFIP...")
        token, sign = client.autenticar_wsaa(cuit)
        print(f"✅ Autenticación exitosa - Token: {token[:30]}...")
        
        # 2. Tipos de comprobante a verificar
        tipos_comprobante = {
            # Responsable Inscripto
            1: "Factura A",
            2: "Nota de Débito A", 
            3: "Nota de Crédito A",
            6: "Factura B",
            7: "Nota de Débito B",
            8: "Nota de Crédito B", 
            11: "Factura C",
            12: "Nota de Débito C",
            13: "Nota de Crédito C",
            
            # Monotributo
            51: "Factura M",
            52: "Nota de Débito M",
            53: "Nota de Crédito M",
            
            # Exportación
            19: "Factura de Exportación",
            20: "Nota de Débito Exportación",
            21: "Nota de Crédito Exportación",
            
            # Otros comunes
            4: "Recibo A", 
            9: "Recibo B",
            15: "Recibo C",
            54: "Recibo M"
        }
        
        print(f"\n2️⃣ Verificando tipos de comprobante disponibles...")
        puntos_venta = [1, 2, 3, 4, 5]
        
        resultados = {}
        facturas_encontradas = []
        
        for tipo_id, descripcion in tipos_comprobante.items():
            print(f"\n   🔍 Tipo {tipo_id}: {descripcion}")
            
            tipo_tiene_facturas = False
            
            for punto in puntos_venta[:3]:  # Solo primeros 3 puntos para eficiencia
                try:
                    ultimo = client.obtener_ultimo_comprobante(cuit, tipo_id, punto)
                    
                    if ultimo and ultimo > 0:
                        tipo_tiene_facturas = True
                        print(f"      ✅ PV {punto}: Último #{ultimo}")
                        
                        # Intentar consultar la última factura
                        try:
                            factura = client.consultar_comprobante(cuit, tipo_id, punto, ultimo)
                            if factura:
                                facturas_encontradas.append({
                                    'tipo': tipo_id,
                                    'descripcion': descripcion,
                                    'punto_venta': punto,
                                    'numero': ultimo,
                                    'fecha_emision': factura.get('fecha_emision', 'N/A'),
                                    'cae': factura.get('cae', 'N/A'),
                                    'importe_total': factura.get('importe_total', 'N/A'),
                                    'receptor_cuit': factura.get('receptor_cuit', 'N/A'),
                                    'receptor_denominacion': factura.get('receptor_denominacion', 'N/A')
                                })
                                print(f"         📄 CAE: {factura.get('cae', 'N/A')[:15]}...")
                        except Exception as e:
                            print(f"         ⚠️ Error consultando: {e}")
                            
                except Exception as e:
                    print(f"      ❌ PV {punto}: Error - {e}")
            
            resultados[tipo_id] = {
                'descripcion': descripcion,
                'tiene_facturas': tipo_tiene_facturas
            }
            
            if not tipo_tiene_facturas:
                print(f"      📭 Sin facturas de este tipo")
        
        # 3. Análisis de resultados
        print(f"\n3️⃣ ANÁLISIS DE RESULTADOS")
        print("=" * 40)
        
        # Clasificar por categorías
        responsable_inscripto = any(resultados[t]['tiene_facturas'] for t in [1, 6, 11])  # A, B, C
        monotributista = any(resultados[t]['tiene_facturas'] for t in [51, 52, 53, 54])  # M
        exportador = any(resultados[t]['tiene_facturas'] for t in [19, 20, 21])  # Exportación
        
        print(f"\n📊 TIPO DE CONTRIBUYENTE:")
        if responsable_inscripto:
            print("   ✅ RESPONSABLE INSCRIPTO - Emite facturas A, B, C")
        if monotributista:
            print("   ✅ MONOTRIBUTISTA - Emite facturas M")
        if exportador:
            print("   ✅ EXPORTADOR - Emite facturas de exportación")
        
        if not any([responsable_inscripto, monotributista, exportador]):
            print("   ⚠️ SIN FACTURAS ELECTRÓNICAS DETECTADAS")
            print("   💡 Posible causa: CUIT no emite facturas o usa otro servicio")
        
        # 4. Resumen de facturas
        print(f"\n4️⃣ FACTURAS ENCONTRADAS")
        print("=" * 40)
        
        if facturas_encontradas:
            print(f"🎉 Total: {len(facturas_encontradas)} facturas")
            
            # Agrupar por tipo
            por_tipo = {}
            for f in facturas_encontradas:
                tipo = f['descripcion']
                if tipo not in por_tipo:
                    por_tipo[tipo] = []
                por_tipo[tipo].append(f)
            
            for tipo, facturas in por_tipo.items():
                print(f"\n📄 {tipo}: {len(facturas)} facturas")
                for f in facturas[:3]:  # Mostrar máximo 3 por tipo
                    print(f"   • PV:{f['punto_venta']} #{f['numero']} - {f['fecha_emision']} - CAE:{f['cae'][:12]}...")
                    if f['importe_total'] != 'N/A':
                        print(f"     💰 ${f['importe_total']}")
                    if f['receptor_denominacion'] not in ['N/A', '']:
                        print(f"     👤 {f['receptor_denominacion']}")
        else:
            print("📭 No se encontraron facturas consultables")
        
        # 5. Recomendaciones
        print(f"\n5️⃣ RECOMENDACIONES")
        print("=" * 40)
        
        if responsable_inscripto:
            print("✅ WSFEv1 es perfecto para este CUIT")
            print("✅ Puede consultar todas las facturas A, B, C desde 2013")
            print("✅ Tu aplicación ya está configurada correctamente")
            
        if monotributista:
            print("✅ Las facturas M están disponibles en WSFEv1")
            print("💡 También podrías usar WSFEXv1 si necesitas más funciones")
            
        if exportador:
            print("⚠️ Para facturas de exportación, considera WSFEXv1")
            print("💡 WSFEXv1 tiene mejor soporte para exportación")
            
        if not facturas_encontradas:
            print("💡 Opciones para investigar:")
            print("   1. Verificar si el CUIT emite facturas electrónicas")
            print("   2. Probar con WSMTXCA para códigos MTX especiales")
            print("   3. Verificar permisos del certificado en AFIP")
            print("   4. Considerar que sea un CUIT nuevo sin historial")
        
        return True, facturas_encontradas, {
            'responsable_inscripto': responsable_inscripto,
            'monotributista': monotributista,
            'exportador': exportador
        }
        
    except Exception as e:
        print(f"\n❌ ERROR EN DIAGNÓSTICO: {e}")
        return False, [], {}

def main():
    """Función principal"""
    print("🚀 DIAGNÓSTICO DE CUIT PARA FACTURACIÓN ELECTRÓNICA")
    
    exito, facturas, perfil = diagnosticar_cuit_completo()
    
    print("\n" + "="*60)
    print("🎯 RESUMEN EJECUTIVO")
    print("="*60)
    
    if exito:
        if facturas:
            print(f"✅ CUIT ACTIVO: {len(facturas)} facturas detectadas")
            
            if perfil['responsable_inscripto']:
                print("📋 Perfil: RESPONSABLE INSCRIPTO")
                print("🛠️ Servicio recomendado: WSFEv1 (actual)")
                
            if perfil['monotributista']:
                print("📋 Perfil: MONOTRIBUTISTA") 
                print("🛠️ Servicios: WSFEv1 (actual) o WSFEXv1")
                
            if perfil['exportador']:
                print("📋 Perfil: EXPORTADOR")
                print("🛠️ Servicio recomendado: WSFEXv1")
                
        else:
            print("⚠️ CUIT SIN FACTURAS DETECTADAS")
            print("💭 Posibles causas:")
            print("   - CUIT nuevo sin historial de facturación")
            print("   - No usa facturación electrónica") 
            print("   - Usa servicios específicos (WSMTXCA, WSFEXv1)")
    else:
        print("❌ ERROR EN DIAGNÓSTICO")
        print("🔧 Verificar configuración de certificados")
    
    print(f"\n📚 CONCLUSIÓN:")
    print("Ya tienes un diagnóstico completo de tu CUIT")
    print("Puedes usar esta información para optimizar tu aplicación")

if __name__ == "__main__":
    main()