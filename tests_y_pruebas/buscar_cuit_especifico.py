import sqlite3
import os

# Ir al directorio raíz del proyecto
os.chdir(r'c:\Users\DELL\Desktop\proyectos python\infofiscal')

try:
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    # Buscar el CUIT específico
    cuit_buscar = '27312238018'
    
    print(f"🔍 Buscando CUIT: {cuit_buscar}")
    
    # Buscar removiendo guiones y espacios
    cursor.execute('''
        SELECT * FROM clientes 
        WHERE REPLACE(REPLACE(CUIT, '-', ''), ' ', '') LIKE ?
    ''', (f'%{cuit_buscar}%',))
    
    resultados = cursor.fetchall()
    
    if resultados:
        print(f"✅ Encontrado {len(resultados)} resultado(s):")
        for cliente in resultados:
            print(f"   - ID: {cliente[0]}")
            print(f"   - Tipo Doc: {cliente[1]}")
            print(f"   - Nro Doc: {cliente[2]}")
            print(f"   - CUIT: {cliente[3]}")
            print(f"   - Nombre: {cliente[4]}, {cliente[5]}")
            print(f"   - Fecha Nac: {cliente[6]}")
            print("   " + "="*50)
    else:
        print("❌ No se encontró el cliente con ese CUIT")
        
        # Mostrar los últimos CUITs para referencia
        print(f"\n📋 Últimos 10 CUITs registrados:")
        cursor.execute("SELECT CUIT, apellido, nombres FROM clientes ORDER BY id DESC LIMIT 10")
        ultimos = cursor.fetchall()
        for cliente in ultimos:
            cuit_limpio = cliente[0].replace('-', '').replace(' ', '')
            print(f"   - {cliente[0]} ({cuit_limpio}) - {cliente[1]}, {cliente[2]}")
    
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")