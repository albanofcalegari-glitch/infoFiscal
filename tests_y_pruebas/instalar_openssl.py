"""
Instalador de OpenSSL para Windows - InfoFiscal
Descarga e instala OpenSSL necesario para AFIP
"""

import os
import sys
import urllib.request
import zipfile
import shutil
from pathlib import Path

def descargar_openssl_portable():
    """Descargar OpenSSL portable para Windows"""
    
    print("📥 DESCARGANDO OPENSSL PARA WINDOWS...")
    print("=" * 45)
    
    # URL de OpenSSL portable (Win32/Win64)
    openssl_url = "https://slproweb.com/download/Win64OpenSSL_Light-3_1_4.exe"
    openssl_portable_url = "https://indy.fulgan.com/SSL/openssl-1.0.2ze-x64_86-win32.zip"
    
    # Directorio donde instalar OpenSSL
    openssl_dir = Path(__file__).parent / "openssl_portable"
    openssl_dir.mkdir(exist_ok=True)
    
    print(f"📁 Directorio destino: {openssl_dir}")
    
    try:
        # Opción 1: Usar OpenSSL que viene con Git (si está instalado)
        git_openssl = Path("C:/Program Files/Git/usr/bin/openssl.exe")
        if git_openssl.exists():
            print("✅ OpenSSL encontrado en Git!")
            print(f"   Ruta: {git_openssl}")
            return str(git_openssl)
        
        # Opción 2: Buscar en Program Files
        program_files_paths = [
            Path("C:/Program Files/OpenSSL-Win64/bin/openssl.exe"),
            Path("C:/Program Files (x86)/OpenSSL-Win32/bin/openssl.exe"),
            Path("C:/OpenSSL-Win64/bin/openssl.exe"),
            Path("C:/OpenSSL-Win32/bin/openssl.exe")
        ]
        
        for path in program_files_paths:
            if path.exists():
                print(f"✅ OpenSSL encontrado en: {path}")
                return str(path)
        
        # Opción 3: Crear OpenSSL portable simple usando Python
        print("💡 Creando versión Python de OpenSSL...")
        return crear_openssl_python()
        
    except Exception as e:
        print(f"❌ Error descargando OpenSSL: {e}")
        return None

def crear_openssl_python():
    """Crear un wrapper de OpenSSL usando la librería cryptography de Python"""
    
    print("🐍 CREANDO WRAPPER PYTHON PARA OPENSSL...")
    
    # Verificar si cryptography está instalada
    try:
        from cryptography.hazmat.primitives import serialization, hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        from cryptography.hazmat.primitives.serialization import pkcs7
        print("✅ Librería cryptography disponible")
        
        # Crear script wrapper
        wrapper_script = Path(__file__).parent / "openssl_wrapper.py"
        
        wrapper_content = '''#!/usr/bin/env python3
"""
Wrapper de OpenSSL usando Python cryptography
Reemplaza openssl para firmar TRA de AFIP
"""

import sys
import argparse
from pathlib import Path
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography import x509

def firmar_tra_python(tra_path, cert_path, key_path, output_path):
    """Firmar TRA usando cryptography de Python"""
    try:
        # Leer archivos
        with open(tra_path, 'rb') as f:
            tra_data = f.read()
        
        with open(cert_path, 'rb') as f:
            cert_data = f.read()
            cert = x509.load_pem_x509_certificate(cert_data)
        
        with open(key_path, 'rb') as f:
            key_data = f.read()
            private_key = serialization.load_pem_private_key(key_data, password=None)
        
        # Crear PKCS#7 signature
        options = [pkcs7.PKCS7Options.DetachedSignature]
        builder = pkcs7.PKCS7SignatureBuilder().set_data(tra_data)
        builder = builder.add_signer(cert, private_key, hashes.SHA256())
        
        # Firmar
        signature = builder.sign(serialization.Encoding.DER, options)
        
        # Guardar
        with open(output_path, 'wb') as f:
            f.write(signature)
        
        return True
        
    except Exception as e:
        print(f"Error firmando: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 8:
        print("Uso: python openssl_wrapper.py smime -sign -signer cert.pem -inkey key.pem -outform DER -nodetach")
        sys.exit(1)
    
    # Parsear argumentos básicos
    if "smime" in sys.argv and "-sign" in sys.argv:
        try:
            signer_idx = sys.argv.index("-signer") + 1
            inkey_idx = sys.argv.index("-inkey") + 1
            
            cert_path = sys.argv[signer_idx]
            key_path = sys.argv[inkey_idx]
            
            # Leer TRA desde stdin y escribir a stdout
            import tempfile
            
            # Crear archivos temporales
            with tempfile.NamedTemporaryFile(delete=False) as tra_temp:
                tra_temp.write(sys.stdin.buffer.read())
                tra_temp_path = tra_temp.name
            
            with tempfile.NamedTemporaryFile(delete=False) as out_temp:
                out_temp_path = out_temp.name
            
            # Firmar
            if firmar_tra_python(tra_temp_path, cert_path, key_path, out_temp_path):
                with open(out_temp_path, 'rb') as f:
                    sys.stdout.buffer.write(f.read())
                print("Firma exitosa", file=sys.stderr)
            else:
                print("Error en firma", file=sys.stderr)
                sys.exit(1)
                
            # Limpiar
            os.unlink(tra_temp_path)
            os.unlink(out_temp_path)
            
        except Exception as e:
            print(f"Error procesando argumentos: {e}", file=sys.stderr)
            sys.exit(1)
'''
        
        wrapper_script.write_text(wrapper_content, encoding='utf-8')
        print(f"✅ Wrapper creado: {wrapper_script}")
        
        # Crear batch file para invocar el wrapper
        batch_file = Path(__file__).parent / "openssl.bat"
        batch_content = f'''@echo off
"{sys.executable}" "{wrapper_script}" %*
'''
        batch_file.write_text(batch_content, encoding='utf-8')
        print(f"✅ Comando openssl.bat creado: {batch_file}")
        
        return str(batch_file)
        
    except ImportError:
        print("❌ Librería cryptography no disponible")
        print("💡 Instalar con: pip install cryptography")
        return None

def configurar_openssl_path(openssl_path):
    """Configurar OpenSSL en el PATH del sistema"""
    
    if not openssl_path:
        return False
        
    print(f"🔧 CONFIGURANDO OPENSSL...")
    
    # Agregar al PATH de la sesión actual
    openssl_dir = str(Path(openssl_path).parent)
    current_path = os.environ.get('PATH', '')
    
    if openssl_dir not in current_path:
        os.environ['PATH'] = f"{openssl_dir};{current_path}"
        print(f"✅ OpenSSL agregado al PATH: {openssl_dir}")
    
    return True

def verificar_openssl():
    """Verificar que OpenSSL funcione correctamente"""
    
    print("🧪 PROBANDO OPENSSL...")
    
    import subprocess
    
    try:
        # Probar versión
        result = subprocess.run(['openssl', 'version'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ OpenSSL funcionando: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ Error ejecutando OpenSSL: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("❌ OpenSSL no encontrado en PATH")
        return False
    except Exception as e:
        print(f"❌ Error probando OpenSSL: {e}")
        return False

def main():
    """Función principal del instalador"""
    
    print("🔐 INSTALADOR OPENSSL PARA INFOFISCAL")
    print("=" * 45)
    print("Este script configura OpenSSL para firmar certificados AFIP\\n")
    
    # Paso 1: Descargar/encontrar OpenSSL
    openssl_path = descargar_openssl_portable()
    
    if not openssl_path:
        print("\\n❌ No se pudo configurar OpenSSL")
        print("\\n💡 SOLUCIONES MANUALES:")
        print("1. Instalar Git para Windows (incluye OpenSSL)")
        print("2. Descargar OpenSSL desde: https://slproweb.com/products/Win32OpenSSL.html")
        print("3. Instalar cryptography: pip install cryptography")
        return False
    
    # Paso 2: Configurar PATH
    if not configurar_openssl_path(openssl_path):
        print("\\n❌ No se pudo configurar PATH")
        return False
    
    # Paso 3: Verificar funcionamiento
    if verificar_openssl():
        print("\\n🎉 ¡OPENSSL CONFIGURADO CORRECTAMENTE!")
        print("Ya puedes usar servicios AFIP de producción")
        return True
    else:
        print("\\n⚠️ OpenSSL configurado pero con problemas")
        return False

if __name__ == "__main__":
    main()