# -*- coding: utf-8 -*-
"""Test simple de servicios AFIP"""
import os
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("TEST DE SERVICIOS AFIP")
print("=" * 60)

# 1. Test variables de entorno
print("\n[1] Verificando variables de entorno...")
from dotenv import load_dotenv
from pathlib import Path

env_path = Path(__file__).parent / '.env'
load_dotenv(env_path)

cert_path = os.getenv('AFIP_CERT_PATH')
key_path = os.getenv('AFIP_KEY_PATH')
cuit = os.getenv('AFIP_CUIT')

print(f"   - Certificado: {cert_path}")
print(f"   - Clave privada: {key_path}")
print(f"   - CUIT: {cuit}")
print(f"   - Certificado existe: {os.path.exists(cert_path) if cert_path else False}")
print(f"   - Clave existe: {os.path.exists(key_path) if key_path else False}")

# 2. Test base de datos
print("\n[2] Verificando base de datos...")
import sqlite3
db_path = 'infofiscal.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Tablas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tablas = [row[0] for row in cursor.fetchall()]
    print(f"   - Tablas: {', '.join(tablas)}")

    # Usuarios
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    num_usuarios = cursor.fetchone()[0]
    print(f"   - Usuarios: {num_usuarios}")

    # Clientes
    cursor.execute("SELECT COUNT(*) FROM clientes")
    num_clientes = cursor.fetchone()[0]
    print(f"   - Clientes: {num_clientes}")

    conn.close()
    print("   - Estado DB: OK")
else:
    print("   - Estado DB: NO ENCONTRADA")

# 3. Test WSAA (autenticación)
print("\n[3] Probando WSAA (autenticacion)...")
try:
    import sys
    import importlib.util

    # Cargar módulo sin ejecutar prints con emojis
    spec = importlib.util.spec_from_file_location("afip_simple", "src/afip_simple.py")
    if spec and spec.loader:
        afip_simple = importlib.util.module_from_spec(spec)
        # Redirigir stdout temporalmente
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            spec.loader.exec_module(afip_simple)
        finally:
            sys.stdout = old_stdout

        cliente = afip_simple.AFIPSimpleClient(cert_path, key_path, cuit)
        token = cliente._get_auth_token('wsfe')
        if token:
            print("   - WSAA: OK (token obtenido)")
        else:
            print("   - WSAA: FAIL (no se pudo obtener token)")
except Exception as e:
    print(f"   - WSAA: ERROR ({str(e)[:50]}...)")

# 4. Test WSFEv1
print("\n[4] Probando WSFEv1 (factura electronica)...")
try:
    # Probar consulta de última factura
    ultima = cliente.consultar_ultima_factura(cuit, 11)  # Tipo 11 = Factura C
    if ultima:
        print(f"   - WSFEv1: OK (ultima factura tipo C: {ultima})")
    else:
        print("   - WSFEv1: OK (sin facturas tipo C)")
except Exception as e:
    print(f"   - WSFEv1: ERROR ({str(e)[:50]}...)")

# 5. Test WSMTXCA
print("\n[5] Probando WSMTXCA (monotributo)...")
try:
    token_mtx = cliente._get_auth_token('wsmtxca')
    if token_mtx:
        print("   - WSMTXCA: OK (token obtenido)")
    else:
        print("   - WSMTXCA: FAIL (no se pudo obtener token)")
except Exception as e:
    print(f"   - WSMTXCA: ERROR ({str(e)[:50]}...)")

# 6. Test Flask
print("\n[6] Verificando Flask app...")
try:
    # Cargar app sin ejecutar prints con emojis
    spec = importlib.util.spec_from_file_location("app", "src/app.py")
    if spec and spec.loader:
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            print = old_stdout.write  # Restaurar print
            sys.stdout = old_stdout
            print("   - Flask: OK (app cargada)\n")
        except:
            sys.stdout = old_stdout
            print("   - Flask: ERROR\n")
except Exception as e:
    print(f"   - Flask: ERROR ({str(e)[:50]}...)\n")

print("=" * 60)
print("RESUMEN: Servicios verificados")
print("=" * 60)
