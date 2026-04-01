#!/usr/bin/env python3
"""
Test del cliente WSMTXCA
Verifica autenticación y funcionalidades básicas
"""

from wsmtxca_client import WSMTXCAClient, crear_cliente_wsmtxca
import os
from pathlib import Path

def test_configuracion():
    """Test 1: Verificar configuración de certificados"""
    print("🔧 TEST 1: Configuración de certificados")
    
    try:
        # Auto-detectar certificados
        if os.path.basename(os.getcwd()) == 'src':
            base_dir = Path(os.getcwd()).parent
        else:
            base_dir = Path(os.getcwd())
        
        cert_path = base_dir / 'certs' / 'certificado.crt'
        key_path = base_dir / 'certs' / 'clave_privada.key'
        
        print(f"   📄 Certificado: {cert_path}")
        print(f"   🔑 Clave: {key_path}")
        
        if cert_path.exists() and key_path.exists():
            print("   ✅ Certificados encontrados")
            
            # Verificar contenido
            with open(cert_path, 'r') as f:
                cert_content = f.read()
            
            if 'BEGIN CERTIFICATE' in cert_content:
                print("   ✅ Formato de certificado válido")
                return True
            else:
                print("   ❌ Formato de certificado inválido")
                return False
        else:
            print("   ❌ Certificados no encontrados")
            return False
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_creacion_cliente():
    """Test 2: Crear cliente WSMTXCA"""
    print("\n🏗️ TEST 2: Creación de cliente")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        print("   ✅ Cliente WSMTXCA creado exitosamente")
        print(f"   🌐 Ambiente: {client.ambiente}")
        print(f"   🔗 URL WSMTXCA: {client.urls['prod']['wsmtxca']}")
        print(f"   🗝️ Tipos de comprobante soportados: {len(client.tipos_comprobante)}")
        return client
    
    except Exception as e:
        print(f"   ❌ Error creando cliente: {e}")
        return None

def test_validaciones():
    """Test 3: Validaciones de entrada"""
    print("\n✅ TEST 3: Validaciones")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Test validación CUIT
        try:
            cuit_valido = client._validar_cuit("20321518045")
            print(f"   ✅ CUIT válido: {cuit_valido}")
        except Exception as e:
            print(f"   ❌ Error validando CUIT: {e}")
            return False
        
        # Test CUIT inválido
        try:
            client._validar_cuit("123")
            print("   ❌ Debería haber fallado con CUIT inválido")
            return False
        except ValueError:
            print("   ✅ Validación CUIT inválido funciona")
        
        # Test detección OpenSSL
        try:
            openssl_path = client._detectar_openssl()
            print(f"   ✅ OpenSSL detectado: {openssl_path}")
        except Exception as e:
            print(f"   ❌ OpenSSL no detectado: {e}")
            return False
        
        return True
    
    except Exception as e:
        print(f"   ❌ Error en validaciones: {e}")
        return False

def test_autenticacion_wsaa():
    """Test 4: Autenticación WSAA"""
    print("\n🔐 TEST 4: Autenticación WSAA")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Usar tu CUIT real
        cuit = "20321518045"
        
        print(f"   🏢 Autenticando CUIT: {cuit}")
        print("   ⏳ Esto puede tomar unos segundos...")
        
        token, sign = client.autenticar_wsaa(cuit)
        
        if token and sign:
            print("   ✅ Autenticación WSAA exitosa")
            print(f"   🎫 Token: {token[:50]}...")
            print(f"   ✍️ Sign: {sign[:50]}...")
            return True
        else:
            print("   ❌ Token o Sign vacíos")
            return False
    
    except Exception as e:
        print(f"   ❌ Error autenticación: {e}")
        return False

def test_consulta_comprobante():
    """Test 5: Consulta de comprobante (puede no existir)"""
    print("\n📋 TEST 5: Consulta de comprobante")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        cuit = "20321518045"
        
        print("   🔍 Consultando comprobante de prueba...")
        print("   📝 Nota: Es normal que no exista el comprobante de prueba")
        
        resultado = client.consultar_comprobante(
            cuit_representada=cuit,
            tipo_comprobante=1,    # Factura A
            punto_venta=1,
            numero_comprobante=1
        )
        
        if resultado:
            print("   ✅ Comprobante encontrado!")
            print(f"      Fecha: {resultado.get('fecha_emision')}")
            print(f"      Total: ${resultado.get('importe_total')}")
            print(f"      CAE: {resultado.get('cae')}")
            return True
        else:
            print("   📭 Comprobante no encontrado (esto es normal para el test)")
            return True  # No encontrar es OK para el test
    
    except Exception as e:
        if "602" in str(e):  # Error "no existe"
            print("   📭 Comprobante no existe (esto es normal para el test)")
            return True
        else:
            print(f"   ❌ Error inesperado: {e}")
            return False

def test_tipos_comprobante():
    """Test 6: Verificar tipos de comprobante"""
    print("\n📄 TEST 6: Tipos de comprobante")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        
        # Verificar algunos tipos importantes
        tipos_importantes = [1, 6, 11, 51, 52, 53]
        
        for tipo in tipos_importantes:
            if tipo in client.tipos_comprobante:
                nombre = client.tipos_comprobante[tipo]
                print(f"   ✅ Tipo {tipo}: {nombre}")
            else:
                print(f"   ❌ Tipo {tipo} no encontrado")
                return False
        
        print(f"   📊 Total tipos soportados: {len(client.tipos_comprobante)}")
        return True
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_cache_tokens():
    """Test 7: Cache de tokens"""
    print("\n💾 TEST 7: Cache de tokens")
    
    try:
        client = crear_cliente_wsmtxca(ambiente='prod')
        cuit = "20321518045"
        
        # Primera autenticación
        print("   🔐 Primera autenticación...")
        token1, sign1 = client.autenticar_wsaa(cuit)
        
        # Segunda autenticación (debería usar cache)
        print("   🔄 Segunda autenticación (debería usar cache)...")
        token2, sign2 = client.autenticar_wsaa(cuit)
        
        if token1 == token2 and sign1 == sign2:
            print("   ✅ Cache funcionando correctamente")
            return True
        else:
            print("   ❌ Cache no funciona - tokens diferentes")
            return False
    
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def ejecutar_todos_los_tests():
    """Ejecutar todos los tests"""
    print("🧪 === TESTS WSMTXCA CLIENT ===")
    print("Verificando funcionalidades del cliente...\n")
    
    tests = [
        ("Configuración", test_configuracion),
        ("Creación Cliente", test_creacion_cliente),
        ("Validaciones", test_validaciones),
        ("Autenticación WSAA", test_autenticacion_wsaa),
        ("Consulta Comprobante", test_consulta_comprobante),
        ("Tipos Comprobante", test_tipos_comprobante),
        ("Cache Tokens", test_cache_tokens)
    ]
    
    resultados = []
    
    for nombre, test_func in tests:
        try:
            resultado = test_func()
            resultados.append((nombre, resultado))
        except Exception as e:
            print(f"❌ Error crítico en {nombre}: {e}")
            resultados.append((nombre, False))
    
    # Resumen
    print(f"\n{'='*50}")
    print("📊 RESUMEN DE TESTS")
    print(f"{'='*50}")
    
    exitosos = 0
    for nombre, exito in resultados:
        status = "✅" if exito else "❌"
        print(f"{status} {nombre}")
        if exito:
            exitosos += 1
    
    print(f"\n🎯 RESULTADO: {exitosos}/{len(tests)} tests exitosos")
    
    if exitosos == len(tests):
        print("🎉 ¡Todos los tests pasaron! El cliente WSMTXCA está listo para usar.")
    elif exitosos >= len(tests) - 2:
        print("✅ La mayoría de tests pasaron. El cliente debería funcionar correctamente.")
    else:
        print("⚠️ Varios tests fallaron. Revisar configuración antes de usar en producción.")
    
    return exitosos, len(tests)

if __name__ == "__main__":
    ejecutar_todos_los_tests()