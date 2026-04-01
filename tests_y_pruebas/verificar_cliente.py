import sqlite3
import os

# Ir al directorio raíz del proyecto
os.chdir(r'c:\Users\DELL\Desktop\proyectos python\infofiscal')

try:
    # Conectar a la base de datos
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    # Buscar el cliente específico
    cuit_buscar = '27312238018'
    
    print(f"🔍 Buscando cliente con CUIT: {cuit_buscar}")
    
    # Buscar con diferentes patrones
    resultado1 = cursor.execute('SELECT * FROM clientes WHERE cuit_dni = ?', (cuit_buscar,)).fetchall()
    resultado2 = cursor.execute('SELECT * FROM clientes WHERE cuit_dni LIKE ?', (f'%{cuit_buscar}%',)).fetchall()
    
    print(f"\n📊 Búsqueda exacta: {len(resultado1)} resultados")
    for cliente in resultado1:
        print(f"   - ID: {cliente[0]}, Nombre: {cliente[1]}, CUIT: {cliente[2]}")
    
    print(f"\n📊 Búsqueda con LIKE: {len(resultado2)} resultados")
    for cliente in resultado2:
        print(f"   - ID: {cliente[0]}, Nombre: {cliente[1]}, CUIT: {cliente[2]}")
    
    # Mostrar todos los clientes para referencia
    print(f"\n📋 Todos los clientes en la base:")
    todos = cursor.execute('SELECT * FROM clientes ORDER BY id DESC LIMIT 10').fetchall()
    for cliente in todos:
        print(f"   - ID: {cliente[0]}, Nombre: {cliente[1]}, CUIT: {cliente[2]}")
    
    conn.close()
    print("\n✅ Consulta completada")
    
except Exception as e:
    print(f"❌ Error: {e}")