import sqlite3
import os

# Ir al directorio raíz del proyecto
os.chdir(r'c:\Users\DELL\Desktop\proyectos python\infofiscal')

try:
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    # Buscar por el DNI exacto
    dni_buscar = '31223801'
    
    print(f"🔍 Buscando DNI: {dni_buscar}")
    
    # Buscar exacto
    cursor.execute('SELECT * FROM clientes WHERE nroDocumento = ?', (dni_buscar,))
    resultado_exacto = cursor.fetchall()
    
    # Buscar con LIKE
    cursor.execute('SELECT * FROM clientes WHERE nroDocumento LIKE ?', (f'%{dni_buscar}%',))
    resultado_like = cursor.fetchall()
    
    # Buscar por CUIT que contenga el DNI
    cursor.execute('SELECT * FROM clientes WHERE CUIT LIKE ?', (f'%{dni_buscar}%',))
    resultado_cuit = cursor.fetchall()
    
    print(f"\n📊 Resultados:")
    print(f"   Búsqueda exacta por nroDocumento: {len(resultado_exacto)} resultados")
    print(f"   Búsqueda LIKE por nroDocumento: {len(resultado_like)} resultados") 
    print(f"   Búsqueda por CUIT conteniendo DNI: {len(resultado_cuit)} resultados")
    
    # Mostrar todos los resultados
    todos_resultados = resultado_exacto + resultado_like + resultado_cuit
    
    if todos_resultados:
        print(f"\n✅ Clientes encontrados:")
        for cliente in set(todos_resultados):  # usar set para evitar duplicados
            print(f"   - ID: {cliente[0]}")
            print(f"   - Tipo Doc: {cliente[1]}")
            print(f"   - Nro Doc: {cliente[2]}")  
            print(f"   - CUIT: {cliente[3]}")
            print(f"   - Nombre: {cliente[4]}, {cliente[5]}")
            print("   " + "="*40)
    else:
        print(f"\n❌ No se encontró cliente con DNI {dni_buscar}")
        
        # Mostrar todos los clientes para referencia
        print(f"\n📋 Todos los clientes en la base:")
        cursor.execute("SELECT nroDocumento, CUIT, apellido, nombres FROM clientes")
        todos = cursor.fetchall()
        for cliente in todos:
            print(f"   - DNI: {cliente[0]}, CUIT: {cliente[1]}, Nombre: {cliente[2]}, {cliente[3]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()