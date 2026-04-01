#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Diagnóstico específico para facturas 235-238 que SABEMOS que existen
CUIT: 27312238018, PV: 2
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from wsfev1_client import WSFEv1Client

def diagnostico_facturas_especificas():
    """Diagnóstico detallado de por qué no encontramos las facturas que existen"""
    
    CUIT = "27312238018"
    PUNTO_VENTA = 2
    FACTURAS = [235, 236, 237, 238]
    
    print(f"🔬 DIAGNÓSTICO ESPECÍFICO - Facturas que SABEMOS que existen")
    print("=" * 70)
    print(f"🏢 CUIT: {CUIT}")
    print(f"📍 Punto de Venta: {PUNTO_VENTA}")
    print(f"📄 Facturas: {FACTURAS}")
    print("=" * 70)
    
    try:
        client = WSFEv1Client('certs/certificado.crt', 'certs/clave_privada.key', 'prod')
        
        # 1. Verificar autenticación
        print("1️⃣ Verificando autenticación...")
        token, sign = client.autenticar_wsaa(CUIT)
        print(f"✅ Autenticación exitosa")
        print(f"   Token: {token[:30]}...")
        
        # 2. Probar todos los tipos de comprobante posibles
        tipos_prioritarios = [
            (11, "Factura C"),
            (51, "Factura M"),
            (6, "Factura B"),
            (1, "Factura A"),
            (19, "Factura de Exportación"),
            (20, "Nota de Débito por Operaciones con el Exterior"),
            (21, "Nota de Crédito por Operaciones con el Exterior")
        ]
        
        print(f"\n2️⃣ Probando tipos de comprobante para factura {FACTURAS[0]}...")
        
        facturas_encontradas = []
        
        for tipo_id, tipo_desc in tipos_prioritarios:
            print(f"\n📋 Probando tipo {tipo_id} ({tipo_desc}):")
            
            try:
                # Primero verificar último autorizado
                ultimo = client.obtener_ultimo_comprobante(CUIT, tipo_id, PUNTO_VENTA)
                print(f"   📊 Último autorizado: {ultimo}")
                
                if ultimo >= max(FACTURAS):
                    print(f"   ✅ Rango válido! Último ({ultimo}) >= Factura máxima ({max(FACTURAS)})")
                    
                    # Probar cada factura específica
                    for num_factura in FACTURAS:
                        print(f"\n      🔍 Consultando {PUNTO_VENTA:04d}-{num_factura:08d} tipo {tipo_id}...")
                        
                        try:
                            comp = client.consultar_comprobante(CUIT, tipo_id, PUNTO_VENTA, num_factura)
                            
                            if comp:
                                print(f"      🎉 ¡ENCONTRADA!")
                                print(f"         CAE: {comp.get('CAE', 'N/A')}")
                                print(f"         Fecha: {comp.get('CbteFch', 'N/A')}")
                                print(f"         Total: ${comp.get('ImpTotal', 'N/A')}")
                                print(f"         Estado: {comp.get('Estado', 'N/A')}")
                                
                                facturas_encontradas.append({
                                    'numero': num_factura,
                                    'tipo': tipo_id,
                                    'tipo_desc': tipo_desc,
                                    'cae': comp.get('CAE'),
                                    'fecha': comp.get('CbteFch'),
                                    'total': comp.get('ImpTotal')
                                })
                            else:
                                print(f"      📭 No encontrada (retornó None)")
                                
                                # Intentar diagnóstico del XML crudo
                                print(f"      🔍 Diagnóstico del XML response...")
                                # Hacer una consulta manual para ver el XML
                                
                        except Exception as e:
                            print(f"      ❌ Error consultando: {e}")
                            
                else:
                    print(f"   📭 Último autorizado ({ultimo}) < Facturas buscadas")
                    
            except Exception as e:
                print(f"   ❌ Error obteniendo último: {e}")
        
        # 3. Resumen
        print(f"\n" + "=" * 70)
        print(f"📊 RESUMEN DEL DIAGNÓSTICO")
        print("=" * 70)
        
        if facturas_encontradas:
            print(f"🎉 ¡FACTURAS ENCONTRADAS! ({len(facturas_encontradas)} total)")
            for f in facturas_encontradas:
                print(f"   📄 {f['numero']} - Tipo {f['tipo']} ({f['tipo_desc']}) - CAE: {f['cae']}")
        else:
            print(f"❌ NO SE ENCONTRARON FACTURAS")
            print(f"\n💡 POSIBLES CAUSAS:")
            print(f"   1. Las facturas están en WSMTXCA (no WSFEv1)")
            print(f"   2. Están en WSFEXv1 (sin permisos)")
            print(f"   3. Bug en el parseo del XML response")
            print(f"   4. Problema con el método de consulta")
            
            # 4. Diagnóstico adicional - verificar XML raw
            print(f"\n4️⃣ Diagnóstico XML raw para factura 235...")
            try:
                # Hacer consulta manual con debug del XML
                token, sign = client.autenticar_wsaa(CUIT)
                
                params = {
                    'FeCompConsReq': {
                        'CbteTipo': 11,  # Factura C
                        'CbteNro': 235,
                        'PtoVta': 2
                    }
                }
                
                print(f"   📤 Enviando request manual...")
                xml_response = client._wsfe_request('FECompConsultar', params, token, sign, CUIT)
                
                print(f"   📥 XML Response completo:")
                print(f"   {xml_response[:1000]}...")
                
                # Buscar específicamente errores
                if 'Code' in xml_response and 'Msg' in xml_response:
                    print(f"\n   ⚠️ Errores encontrados en XML:")
                    import xml.etree.ElementTree as ET
                    root = ET.fromstring(xml_response)
                    
                    for error in root.findall('.//{http://ar.gov.afip.dif.FEV1/}Err'):
                        codigo = error.findtext('.//{http://ar.gov.afip.dif.FEV1/}Code')
                        mensaje = error.findtext('.//{http://ar.gov.afip.dif.FEV1/}Msg')
                        print(f"      Código: {codigo}")
                        print(f"      Mensaje: {mensaje}")
                        
            except Exception as e:
                print(f"   ❌ Error en diagnóstico XML: {e}")
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostico_facturas_especificas()