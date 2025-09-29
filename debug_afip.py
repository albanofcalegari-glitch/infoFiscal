#!/usr/bin/env python3
"""
Debug detallado del proceso de autenticación AFIP
"""

import sys
import os
import subprocess
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_openssl_detallado():
    """Test detallado de OpenSSL"""
    
    print("🔍 DEBUG DETALLADO - OPENSSL")
    print("=" * 40)
    
    # Test 1: Verificar ejecutable
    openssl_paths = [
        r'C:\Program Files\Git\usr\bin\openssl.exe',
        'openssl.exe',
        'openssl'
    ]
    
    openssl_found = None
    for path in openssl_paths:
        if os.path.exists(path) or path in ['openssl.exe', 'openssl']:
            try:
                result = subprocess.run([path, 'version'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    print(f"✅ OpenSSL encontrado: {path}")
                    print(f"   Versión: {result.stdout.strip()}")
                    openssl_found = path
                    break
            except Exception as e:
                print(f"❌ Error probando {path}: {e}")
    
    if not openssl_found:
        print("❌ OpenSSL no encontrado en ninguna ubicación")
        return None
    
    return openssl_found

def test_certificados_detallado():
    """Test detallado de certificados"""
    
    print(f"\n🔍 DEBUG DETALLADO - CERTIFICADOS")
    print("=" * 40)
    
    cert_path = Path("certs/certificado.crt")
    key_path = Path("certs/clave_privada.key")
    
    # Verificar existencia
    if not cert_path.exists():
        print(f"❌ Certificado no encontrado: {cert_path}")
        return False
    
    if not key_path.exists():
        print(f"❌ Clave privada no encontrada: {key_path}")
        return False
    
    print(f"✅ Certificado encontrado: {cert_path}")
    print(f"✅ Clave privada encontrada: {key_path}")
    
    # Verificar contenido básico
    try:
        cert_content = cert_path.read_text()
        if "BEGIN CERTIFICATE" in cert_content:
            print("✅ Certificado tiene formato PEM")
        else:
            print("⚠️ Certificado no parece formato PEM")
        
        key_content = key_path.read_text()
        if "BEGIN PRIVATE KEY" in key_content or "BEGIN RSA PRIVATE KEY" in key_content:
            print("✅ Clave privada tiene formato PEM")
        else:
            print("⚠️ Clave privada no parece formato PEM")
            
    except Exception as e:
        print(f"❌ Error leyendo archivos: {e}")
        return False
    
    return True

def test_firma_tra_detallado():
    """Test detallado del proceso de firma TRA"""
    
    print(f"\n🔍 DEBUG DETALLADO - FIRMA TRA")
    print("=" * 40)
    
    openssl = test_openssl_detallado()
    if not openssl:
        return False
    
    if not test_certificados_detallado():
        return False
    
    # Crear TRA de prueba
    tra_test = '''<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
    <header>
        <uniqueId>1695945600</uniqueId>
        <generationTime>2025-09-29T18:00:00</generationTime>
        <expirationTime>2025-09-29T18:30:00</expirationTime>
    </header>
    <service>wsfe</service>
</loginTicketRequest>'''
    
    print("📝 TRA de prueba creado")
    
    # Intentar firma paso a paso
    try:
        import tempfile
        
        # Crear archivos temporales
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            f.write(tra_test)
            tra_path = f.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.cms') as f:
            cms_path = f.name
        
        print(f"📄 Archivos temporales:")
        print(f"   TRA: {tra_path}")
        print(f"   CMS: {cms_path}")
        
        # Comando OpenSSL
        cmd = [
            openssl, 'smime', '-sign', '-signer', 'certs/certificado.crt',
            '-inkey', 'certs/clave_privada.key', '-outform', 'DER', '-nodetach'
        ]
        
        print(f"🔧 Comando OpenSSL:")
        print(f"   {' '.join(cmd)}")
        
        # Ejecutar con más información de debug
        with open(tra_path, 'rb') as infile, open(cms_path, 'wb') as outfile:
            result = subprocess.run(cmd, stdin=infile, stdout=outfile, 
                                  stderr=subprocess.PIPE, text=True, timeout=30)
        
        print(f"📊 Resultado OpenSSL:")
        print(f"   Return code: {result.returncode}")
        print(f"   Stderr: {result.stderr}")
        
        if result.returncode == 0:
            cms_size = os.path.getsize(cms_path)
            print(f"✅ Firma exitosa! CMS creado: {cms_size} bytes")
            
            # Verificar contenido CMS
            with open(cms_path, 'rb') as f:
                cms_data = f.read()
            
            print(f"📦 CMS datos: {len(cms_data)} bytes")
            print(f"   Primeros bytes: {cms_data[:20].hex()}")
            
        else:
            print(f"❌ Fallo en firma OpenSSL")
            print(f"   Error: {result.stderr}")
            
        # Limpiar
        os.unlink(tra_path)
        os.unlink(cms_path)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Excepción durante firma: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_wsaa_detallado():
    """Test detallado de WSAA con CMS válido"""
    
    print(f"\n🔍 DEBUG DETALLADO - WSAA")
    print("=" * 40)
    
    # Verificar que tengamos un CMS válido
    if not test_firma_tra_detallado():
        print("❌ No se puede probar WSAA sin firma válida")
        return False
    
    # Ahora probar WSAA real
    try:
        from arca_service_simple import ARCAServiceSimple
        
        print("🔧 Creando servicio AFIP...")
        service = ARCAServiceSimple(
            cuit="20321518045",
            cert_path="certs/certificado.crt", 
            key_path="certs/clave_privada.key",
            testing=False
        )
        
        print("🔐 Intentando autenticación WSAA...")
        auth_data = service.autenticar()
        
        if auth_data:
            print("✅ WSAA exitoso!")
            print(f"   Token: {auth_data.get('token', '')[:50]}...")
            print(f"   Sign: {auth_data.get('sign', '')[:50]}...")
            return True
        else:
            print("❌ WSAA falló")
            return False
            
    except Exception as e:
        print(f"❌ Error en WSAA: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Función principal de debug"""
    
    print("🔍 DEBUG COMPLETO - AUTENTICACIÓN AFIP")
    print("=" * 50)
    print("CUIT: 20321518045")
    print("Modo: PRODUCCIÓN")
    print()
    
    # Configurar ambiente
    os.environ['INFOFISCAL_MODE'] = 'production'
    
    # Tests paso a paso
    tests = [
        ("OpenSSL", test_openssl_detallado),
        ("Certificados", test_certificados_detallado), 
        ("Firma TRA", test_firma_tra_detallado),
        ("WSAA", test_wsaa_detallado)
    ]
    
    resultados = {}
    
    for nombre, test_func in tests:
        print(f"\n{'='*20} {nombre.upper()} {'='*20}")
        try:
            resultado = test_func()
            resultados[nombre] = resultado
            if resultado:
                print(f"✅ {nombre}: EXITOSO")
            else:
                print(f"❌ {nombre}: FALLIDO")
        except Exception as e:
            print(f"❌ {nombre}: EXCEPCIÓN - {e}")
            resultados[nombre] = False
    
    # Resumen final
    print(f"\n🎯 RESUMEN FINAL:")
    print("=" * 30)
    
    for nombre, resultado in resultados.items():
        status = "✅ OK" if resultado else "❌ FAIL"
        print(f"{status} {nombre}")
    
    todos_ok = all(resultados.values())
    if todos_ok:
        print(f"\n🎉 ¡TODOS LOS TESTS EXITOSOS!")
        print("El problema puede ser configuración AFIP (servicios no habilitados)")
    else:
        print(f"\n⚠️ HAY PROBLEMAS TÉCNICOS")
        print("Resolver errores antes de verificar configuración AFIP")

if __name__ == "__main__":
    main()