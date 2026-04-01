#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico: Consultar factura 0002-00000235 del CUIT 27312238018
Buscar esta factura específica en todos los servicios disponibles
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from wsfev1_client import WSFEv1Client

def buscar_factura_especifica():
    """Buscar la factura específica 0002-00000235"""
    print("🔍 BÚSQUEDA ESPECÍFICA: Factura 0002-00000235")
    print("=" * 60)
    
    # Datos de la factura
    cuit = "27312238018"
    punto_venta = 2
    numero = 235
    
    print(f"🎯 CUIT: {cuit}")
    print(f"📍 Factura: {punto_venta:04d}-{numero:08d}")
    print(f"🔧 Estrategia: Probar todos los tipos de comprobante comunes")
    
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
        
        # Tipos de comprobante a probar
        tipos_comprobante = {
            1: "Factura A",
            2: "Nota de Débito A", 
            3: "Nota de Crédito A",
            4: "Recibo A",
            6: "Factura B",
            7: "Nota de Débito B",
            8: "Nota de Crédito B",
            9: "Recibo B", 
            11: "Factura C",
            12: "Nota de Débito C",
            13: "Nota de Crédito C",
            15: "Recibo C",
            51: "Factura M",
            52: "Nota de Débito M",
            53: "Nota de Crédito M",
            54: "Recibo M"
        }
        
        print(f"\n2️⃣ Probando la factura en diferentes tipos...")
        
        factura_encontrada = None
        
        for tipo_id, tipo_desc in tipos_comprobante.items():
            print(f"\n   🔍 Probando como {tipo_desc} (tipo {tipo_id})...")
            
            try:
                factura = client.consultar_comprobante(cuit, tipo_id, punto_venta, numero)
                
                if factura and isinstance(factura, dict):
                    print(f"      🎉 ¡ENCONTRADA!")
                    print(f"         📋 Datos raw: {list(factura.keys())}")
                    
                    # Mapear todas las claves posibles de la respuesta
                    factura_encontrada = {
                        'tipo_id': tipo_id,
                        'tipo_descripcion': tipo_desc,
                        'cuit_emisor': cuit,
                        'punto_venta': punto_venta,
                        'numero': numero,
                        'factura_raw': factura,  # Guardar respuesta completa
                        'servicio': 'WSFEv1'
                    }
                    
                    # Mapear campos con diferentes nombres posibles
                    campos_mapeo = {
                        'fecha_emision': ['fecha_emision', 'FchProceso', 'CbteFch', 'Fecha', 'fecha'],
                        'cae': ['cae', 'CodAutorizacion', 'CAE', 'CodigoAutorizacion'],
                        'fecha_vto_cae': ['fecha_vto_cae', 'FchVto', 'FechaVencimiento', 'fecha_vencimiento'],
                        'importe_total': ['importe_total', 'ImpTotal', 'ImporteTotal', 'Total', 'total'],
                        'receptor_cuit': ['receptor_cuit', 'DocNro', 'CUIT', 'cuit_receptor'],
                        'receptor_denominacion': ['receptor_denominacion', 'cliente_razon_social', 'RazonSocial', 'Denominacion'],
                        'receptor_tipo_doc': ['receptor_tipo_doc', 'DocTipo', 'TipoDoc'],
                        'receptor_nro_doc': ['receptor_nro_doc', 'DocNro', 'NumeroDoc'],
                        'moneda': ['moneda', 'MonId', 'Moneda'],
                        'cotizacion': ['cotizacion', 'MonCotiz', 'Cotizacion'],
                        'concepto': ['concepto', 'Concepto', 'ConceptoTipo'],
                        'punto_venta_respuesta': ['punto_venta', 'PtoVta', 'PuntoVenta'],
                        'numero_respuesta': ['numero', 'CbteDesde', 'CbteHasta', 'NumeroComprobante']
                    }
                    
                    # Buscar y mapear cada campo
                    for campo_destino, posibles_nombres in campos_mapeo.items():
                        valor_encontrado = 'N/A'
                        for nombre in posibles_nombres:
                            if nombre in factura and factura[nombre] not in [None, '', 0, '0']:
                                valor_encontrado = factura[nombre]
                                break
                        factura_encontrada[campo_destino] = valor_encontrado
                    
                    print(f"         ✅ Datos mapeados correctamente")
                    break
                else:
                    print(f"      📭 No encontrada como {tipo_desc}")
                    
            except Exception as e:
                print(f"      ❌ Error: {e}")
                import traceback
                print(f"      🔍 Detalle: {traceback.format_exc()}")
        
        # 3. Mostrar resultados
        print(f"\n3️⃣ RESULTADOS DE LA BÚSQUEDA")
        print("=" * 50)
        
        if factura_encontrada:
            print("🎉 ¡FACTURA ENCONTRADA EN WSFEv1!")
            print()
            
            # Mostrar datos RAW para depuración
            print(f"� DATOS RAW RECIBIDOS:")
            raw_data = factura_encontrada.get('factura_raw', {})
            for key, value in raw_data.items():
                if value not in [None, '', 0, '0']:
                    print(f"   {key}: {value}")
            
            print(f"\n�📋 DETALLES DE LA FACTURA:")
            print(f"   🏷️  Tipo: {factura_encontrada['tipo_descripcion']} ({factura_encontrada['tipo_id']})")
            print(f"   📍 Número: {factura_encontrada['punto_venta']:04d}-{factura_encontrada['numero']:08d}")
            print(f"   📅 Fecha emisión: {factura_encontrada['fecha_emision']}")
            print(f"   🔐 CAE: {factura_encontrada['cae']}")
            print(f"   📅 Vencimiento CAE: {factura_encontrada['fecha_vto_cae']}")
            print(f"   💰 Importe: ${factura_encontrada['importe_total']}")
            print(f"   💴 Moneda: {factura_encontrada['moneda']}")
            print(f"   📋 Concepto: {factura_encontrada['concepto']}")
            
            print(f"\n👤 DATOS DEL RECEPTOR:")
            if factura_encontrada['receptor_cuit'] not in ['N/A', '', '0']:
                print(f"   🏢 CUIT: {factura_encontrada['receptor_cuit']}")
            if factura_encontrada['receptor_denominacion'] not in ['N/A', '']:
                print(f"   📝 Razón Social: {factura_encontrada['receptor_denominacion']}")
            if factura_encontrada['receptor_nro_doc'] not in ['N/A', '', '0']:
                print(f"   🆔 Documento: {factura_encontrada['receptor_tipo_doc']} {factura_encontrada['receptor_nro_doc']}")
            
            print(f"\n🔧 VERIFICACIÓN CRUZADA:")
            if factura_encontrada['punto_venta_respuesta'] not in ['N/A']:
                print(f"   📍 Punto venta confirmado: {factura_encontrada['punto_venta_respuesta']}")
            if factura_encontrada['numero_respuesta'] not in ['N/A']:
                print(f"   🔢 Número confirmado: {factura_encontrada['numero_respuesta']}")
            
            print(f"\n🔧 SERVICIO UTILIZADO: {factura_encontrada['servicio']}")
            
            # Determinar qué tipo de contribuyente es
            tipo_contribuyente = determinar_tipo_contribuyente(factura_encontrada['tipo_id'])
            print(f"📊 TIPO DE CONTRIBUYENTE: {tipo_contribuyente}")
            
            # Mostrar todos los campos mapeados
            print(f"\n📊 RESUMEN COMPLETO DE CAMPOS:")
            for campo, valor in factura_encontrada.items():
                if campo not in ['factura_raw', 'servicio'] and valor not in ['N/A', None]:
                    print(f"   {campo}: {valor}")
            
        else:
            print("❌ FACTURA NO ENCONTRADA EN WSFEv1")
            print()
            print("💡 POSIBLES CAUSAS:")
            print("   • La factura está en WSFEXv1 (monotributo)")
            print("   • La factura está en WSMTXCA (códigos MTX)")
            print("   • Error en el punto de venta o número")
            print("   • La factura fue anulada")
            
            # Sugerir siguiente paso
            print(f"\n🔄 SIGUIENTE PASO:")
            print("   Intentar con WSFEXv1 si es monotributista")
        
        return factura_encontrada
        
    except Exception as e:
        print(f"\n❌ ERROR GENERAL: {e}")
        return None

def determinar_tipo_contribuyente(tipo_comprobante):
    """Determinar tipo de contribuyente según el tipo de comprobante"""
    if tipo_comprobante in [1, 2, 3, 4]:  # A
        return "Responsable Inscripto (emite facturas A)"
    elif tipo_comprobante in [6, 7, 8, 9]:  # B  
        return "Responsable Inscripto (emite facturas B)"
    elif tipo_comprobante in [11, 12, 13, 15]:  # C
        return "Cualquier contribuyente (facturas C para consumidor final)"
    elif tipo_comprobante in [51, 52, 53, 54]:  # M
        return "Monotributista (facturas M)"
    else:
        return "Tipo especial o no identificado"

def verificar_ultimo_autorizado():
    """Verificar cuál es el último número autorizado en el punto 2"""
    print(f"\n4️⃣ VERIFICACIÓN ADICIONAL")
    print("=" * 50)
    
    cuit = "27312238018"
    punto_venta = 2
    
    try:
        client = WSFEv1Client(
            cert_path='certs/certificado.crt',
            key_path='certs/clave_privada.key',
            ambiente='prod'
        )
        
        # Probar los tipos más comunes
        tipos_principales = [11, 6, 1, 51]  # C, B, A, M
        
        print(f"🔍 Verificando último autorizado en punto de venta {punto_venta}:")
        
        for tipo in tipos_principales:
            try:
                ultimo = client.obtener_ultimo_comprobante(cuit, tipo, punto_venta)
                if ultimo and ultimo > 0:
                    tipo_nombre = {11: "Factura C", 6: "Factura B", 1: "Factura A", 51: "Factura M"}.get(tipo, f"Tipo {tipo}")
                    print(f"   ✅ {tipo_nombre}: último #{ultimo}")
                    
                    if ultimo >= 235:
                        print(f"      💡 La factura #235 debería existir como {tipo_nombre}")
                else:
                    tipo_nombre = {11: "Factura C", 6: "Factura B", 1: "Factura A", 51: "Factura M"}.get(tipo, f"Tipo {tipo}")
                    print(f"   📭 {tipo_nombre}: sin facturas")
                    
            except Exception as e:
                print(f"   ❌ Error verificando tipo {tipo}: {e}")
                
    except Exception as e:
        print(f"❌ Error en verificación: {e}")

def main():
    """Función principal"""
    print("🎯 INVESTIGACIÓN: Factura específica 0002-00000235")
    
    # Buscar la factura específica
    factura = buscar_factura_especifica()
    
    # Verificar últimos autorizados
    verificar_ultimo_autorizado()
    
    # Conclusión
    print(f"\n" + "="*60)
    print("🎯 CONCLUSIÓN DE LA INVESTIGACIÓN")
    print("="*60)
    
    if factura:
        print(f"✅ LA FACTURA EXISTE Y ESTÁ EN WSFEv1")
        print(f"📄 Tipo: {factura['tipo_descripcion']}")
        print(f"🔧 Tu aplicación actual YA PUEDE consultarla")
        print(f"💡 No necesitas WSFEXv1 para este caso específico")
    else:
        print(f"⚠️ LA FACTURA NO SE ENCUENTRA EN WSFEv1")
        print(f"🔄 Próximo paso: Intentar con WSFEXv1")
        print(f"💡 Puede ser una factura M (monotributo)")
    
    print(f"\n📝 LECCIÓN APRENDIDA:")
    print("Al tener un número específico, podemos verificar")
    print("exactamente en qué servicio está cada factura")

if __name__ == "__main__":
    main()