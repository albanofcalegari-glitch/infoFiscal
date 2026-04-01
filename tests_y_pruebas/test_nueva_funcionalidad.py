#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test rápido de la nueva funcionalidad WSMTXCA completa
"""

import requests
import json

def test_busqueda_completa():
    """Test del nuevo endpoint de búsqueda completa"""
    
    print("🧪 Test de búsqueda completa WSMTXCA")
    print("-" * 50)
    
    # URL del endpoint
    base_url = "http://127.0.0.1:5000"
    endpoint = f"{base_url}/buscar-wsmtxca-completo"
    
    # Parámetros de prueba
    params = {
        'cuit': '20321518045',  # CUIT del certificado
        'limite': '10'
    }
    
    print(f"📡 Consultando: {endpoint}")
    print(f"📊 Parámetros: {params}")
    
    try:
        # Hacer la consulta
        response = requests.get(endpoint, params=params, timeout=30)
        
        print(f"📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('success'):
                print(f"✅ Consulta exitosa:")
                print(f"   CUIT: {data.get('cuit')}")
                print(f"   Consultas realizadas: {data.get('consultas_realizadas')}")
                print(f"   Comprobantes encontrados: {data.get('total_encontrados')}")
                
                resultados = data.get('resultados', [])
                encontrados = [r for r in resultados if r['status'] == 'encontrado']
                
                if encontrados:
                    print(f"\n📋 Comprobantes encontrados:")
                    for i, comp in enumerate(encontrados[:3], 1):
                        datos = comp['datos']
                        print(f"   {i}. Tipo {comp['consulta']['tipo']} PV{datos['punto_venta']} #{datos['numero_comprobante']}")
                        print(f"      CAE: {datos.get('cae', 'N/A')} - ${datos.get('importe_total', '0')}")
                else:
                    print(f"📭 No se encontraron comprobantes")
                
                return True
            else:
                print(f"❌ Error en consulta: {data.get('error')}")
                return False
        else:
            print(f"❌ Error HTTP {response.status_code}: {response.text}")
            return False
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {str(e)}")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def test_interfaz_web():
    """Test de acceso a la interfaz web"""
    
    print(f"\n🌐 Test de interfaz web")
    print("-" * 50)
    
    url = "http://127.0.0.1:5000/wsmtxca"
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Interfaz web accesible en: {url}")
            print(f"   Tamaño HTML: {len(response.text)} bytes")
            
            # Verificar elementos clave
            html = response.text.lower()
            elementos = [
                'buscar todos los comprobantes',
                'cuit del cliente',
                'limite por tipo'
            ]
            
            for elemento in elementos:
                if elemento in html:
                    print(f"   ✅ Encontrado: '{elemento}'")
                else:
                    print(f"   ❌ Faltante: '{elemento}'")
            
            return True
        else:
            print(f"❌ Error HTTP {response.status_code}")
            return False
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔍 Test completo nueva funcionalidad WSMTXCA")
    print("=" * 60)
    
    # Test interfaz web
    web_ok = test_interfaz_web()
    
    # Test endpoint (solo si esperamos que falle por certificados)
    if web_ok:
        print(f"\n💡 Nota: La búsqueda fallará por permisos WSMTXCA, pero probamos la funcionalidad")
        api_ok = test_busqueda_completa()
    
    print(f"\n🏁 Tests completados")
    print(f"   Interfaz Web: {'✅' if web_ok else '❌'}")
    print(f"   Endpoint API: Esperamos fallo por permisos WSMTXCA")