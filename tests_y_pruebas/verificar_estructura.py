import sqlite3
import os

# Ir al directorio raíz del proyecto
os.chdir(r'c:\Users\DELL\Desktop\proyectos python\infofiscal')

try:
    # Conectar a la base de datos
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    print("🔍 Verificando estructura de la tabla clientes...")
    
    # Obtener información de la tabla
    cursor.execute("PRAGMA table_info(clientes)")
    columnas = cursor.fetchall()
    
    print("\n📊 Columnas de la tabla 'clientes':")
    for col in columnas:
        print(f"   - {col[1]} ({col[2]})")
    
    # Mostrar algunos registros
    print(f"\n📋 Últimos 5 clientes registrados:")
    cursor.execute("SELECT * FROM clientes ORDER BY rowid DESC LIMIT 5")
    clientes = cursor.fetchall()
    
    for cliente in clientes:
        print(f"   - Registro: {cliente}")
    
    conn.close()
    print("\n✅ Verificación completada")
    
except Exception as e:
    print(f"❌ Error: {e}")