#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Búsqueda específica de la factura 0002-00000237
CUIT: 27312238018
"""

import sys
import os

# Agregar el directorio src si existe
if os.path.exists('src'):
    sys.path.insert(0, 'src')

from wsfev1_client import WSFEv1Client

def buscar_factura_237():
    """Buscar específicamente la factura 0002-00000237"""
    
    # Configuración
    CUIT = "27312238018"
    PUNTO_VENTA = 2  # 0002 como entero
    NUMERO = 237
    
    # Tipos ordenados por probabilidad
    TIPOS_A_PROBAR = [
        11,  # Factura C (monotributistas) - MÁS PROBABLE
        6,   # Factura B 
        1,   # Factura A
        51,  # Factura M (monotributo)
        2,   # Nota de Débito A
        3,   # Nota de Crédito A
        7,   # Nota de Débito B
        8,   # Nota de Crédito B
        52,  # Nota de Débito M
        53,  # Nota de Crédito M
        12,  # Nota de Débito C
        13,  # Nota de Crédito C
        4,   # Recibo A
        9,   # Recibo B
        15,  # Recibo C
    ]
    
    print("🎯 BÚSQUEDA ESPECÍFICA: FACTURA 0002-00000237")
    print("=" * 50)
    print(f"🏢 CUIT: {CUIT}")
    print(f"📄 Factura: {PUNTO_VENTA:04d}-{NUMERO:08d}")
    print("=" * 50)
    
    # Crear cliente WSFEv1
    try:
        client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        print("✅ Cliente WSFEv1 inicializado")
    except Exception as e:
        print(f"❌ Error inicializando cliente: {e}")
        return None
    
    # Autenticar
    try:
        token, sign = client.autenticar_wsaa(CUIT)
        print("✅ Autenticación WSAA exitosa")
    except Exception as e:
        print(f"❌ Error de autenticación: {e}")
        return None
    
    # Buscar en cada tipo
    for i, tipo in enumerate(TIPOS_A_PROBAR, 1):
        tipo_desc = client.tipos_comprobante.get(tipo, f"Tipo {tipo}")
        print(f"\n📋 [{i}/{len(TIPOS_A_PROBAR)}] Probando tipo {tipo} - {tipo_desc}")
        
        # Verificar último autorizado para este tipo/PV
        try:
            ultimo = client.obtener_ultimo_comprobante(CUIT, tipo, PUNTO_VENTA)
            
            if ultimo and ultimo > 0:
                print(f"   ✅ Último autorizado: {ultimo}")
                
                if NUMERO <= ultimo:
                    print(f"   🔎 Consultando {PUNTO_VENTA:04d}-{NUMERO:08d}...")
                    
                    try:
                        # Consultar la factura específica
                        comp = client.consultar_comprobante(CUIT, tipo, PUNTO_VENTA, NUMERO)
                        
                        if comp is not None:
                            print(f"\n🎉 ¡FACTURA 0002-00000237 ENCONTRADA!")
                            print("=" * 50)
                            print(f"📋 DETALLES:")
                            print(f"   🏷️ Tipo: {tipo} ({tipo_desc})")
                            print(f"   📄 Número: {PUNTO_VENTA:04d}-{NUMERO:08d}")
                            print(f"   📅 Fecha: {comp.get('CbteFch', comp.get('fecha_emision', 'N/A'))}")
                            print(f"   💰 Total: ${comp.get('ImpTotal', comp.get('importe_total', 'N/A'))}")
                            print(f"   🔑 CAE: {comp.get('CAE', comp.get('cae', 'N/A'))}")
                            print(f"   📆 Vto CAE: {comp.get('CAEFchVto', comp.get('fecha_vto_cae', 'N/A'))}")
                            
                            # Información adicional si existe
                            if comp.get('DocNro'):
                                print(f"   👤 Cliente: {comp.get('DocNro')} ({comp.get('DocTipo', 'N/A')})")
                            
                            if comp.get('ImpNeto'):
                                print(f"   💵 Neto: ${comp.get('ImpNeto')}")
                            if comp.get('ImpIVA'):
                                print(f"   🏛️ IVA: ${comp.get('ImpIVA')}")
                            
                            print("=" * 50)
                            
                            # Guardar resultado
                            guardar_resultado_factura(comp, tipo, tipo_desc)
                            
                            return comp
                        else:
                            print(f"   ❌ No encontrada como tipo {tipo}")
                            
                    except Exception as e:
                        print(f"   ⚠️ Error consultando: {str(e)[:100]}...")
                        continue
                else:
                    print(f"   ⚠️ Número {NUMERO} > último autorizado ({ultimo})")
            else:
                print(f"   📭 Sin comprobantes autorizados (último: {ultimo})")
                
        except Exception as e:
            print(f"   ❌ Error obteniendo último: {str(e)[:100]}...")
            continue
    
    # Si llegamos aquí, no se encontró
    print(f"\n❌ FACTURA 0002-00000237 NO ENCONTRADA EN WSFEv1")
    print("=" * 50)
    print(f"💡 CONCLUSIONES:")
    print(f"   • La factura no existe en ningún tipo WSFEv1")
    print(f"   • Probados {len(TIPOS_A_PROBAR)} tipos diferentes")
    print(f"   • Puede estar en WSFEXv1 (monotributo/exportación)")
    print(f"   • Puede ser un tipo no contemplado")
    
    return None

def guardar_resultado_factura(factura_data, tipo_encontrado, tipo_descripcion):
    """Guardar el resultado de la factura encontrada"""
    import json
    from datetime import datetime
    
    resultado = {
        'factura': '0002-00000237',
        'cuit': '27312238018',
        'fecha_busqueda': datetime.now().isoformat(),
        'encontrada_en': {
            'servicio': 'WSFEv1',
            'tipo_codigo': tipo_encontrado,
            'tipo_descripcion': tipo_descripcion
        },
        'datos_factura': factura_data
    }
    
    filename = 'factura_0002_00000237_encontrada.json'
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(resultado, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Resultado guardado en: {filename}")
        
    except Exception as e:
        print(f"⚠️ Error guardando resultado: {e}")

def verificar_rango_facturas():
    """Verificar un pequeño rango alrededor de la 237"""
    print(f"\n🔍 VERIFICACIÓN DE RANGO (235-240)")
    print("=" * 40)
    
    CUIT = "27312238018"
    PUNTO_VENTA = 2
    RANGO = [235, 236, 237, 238, 239, 240]
    
    try:
        client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        # Probar solo con los tipos más comunes
        tipos_comunes = [11, 6, 1, 51]
        
        encontradas = []
        
        for tipo in tipos_comunes:
            tipo_desc = client.tipos_comprobante.get(tipo, f"Tipo {tipo}")
            print(f"\n📋 Verificando tipo {tipo} ({tipo_desc})...")
            
            ultimo = client.obtener_ultimo_comprobante(CUIT, tipo, PUNTO_VENTA)
            if ultimo and ultimo > 0:
                print(f"   Último autorizado: {ultimo}")
                
                for numero in RANGO:
                    if numero <= ultimo:
                        try:
                            comp = client.consultar_comprobante(CUIT, tipo, PUNTO_VENTA, numero)
                            if comp is not None:
                                encontradas.append({
                                    'numero': numero,
                                    'tipo': tipo,
                                    'tipo_desc': tipo_desc,
                                    'cae': comp.get('CAE', 'N/A'),
                                    'fecha': comp.get('CbteFch', 'N/A'),
                                    'total': comp.get('ImpTotal', 'N/A')
                                })
                                print(f"      ✅ {PUNTO_VENTA:04d}-{numero:08d}: CAE {comp.get('CAE', 'N/A')}")
                        except:
                            continue
        
        print(f"\n📊 RESUMEN DEL RANGO:")
        if encontradas:
            for factura in encontradas:
                print(f"   ✅ {PUNTO_VENTA:04d}-{factura['numero']:08d} - {factura['tipo_desc']} - ${factura['total']}")
        else:
            print(f"   📭 No se encontraron facturas en el rango 235-240")
            
        return encontradas
        
    except Exception as e:
        print(f"❌ Error verificando rango: {e}")
        return []

def main():
    """Función principal"""
    print("🚀 BÚSQUEDA DE FACTURA 0002-00000237")
    print("CUIT: 27312238018")
    print("=" * 60)
    
    # 1. Búsqueda específica de la 237
    factura_encontrada = buscar_factura_237()
    
    # 2. Si no se encontró, verificar el rango
    if factura_encontrada is None:
        verificar_rango_facturas()
    
    # 3. Mostrar recomendaciones finales
    print(f"\n🎯 PRÓXIMOS PASOS:")
    if factura_encontrada:
        print(f"   ✅ Factura encontrada en WSFEv1")
        print(f"   💡 Usar los mismos parámetros para otras consultas")
    else:
        print(f"   📋 Verificar en WSFEXv1:")
        print(f"      python busqueda_hibrida_wsfev1_wsfexv1.py")
        print(f"   ⏳ Esperar disponibilidad WSFEXv1 (24-48h)")
        print(f"   🔄 Ejecutar monitor automático:")
        print(f"      python monitor_wsfexv1.py")
    
    return factura_encontrada

if __name__ == "__main__":
    main()