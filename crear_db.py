"""
Script para crear la base de datos completa
"""

import sqlite3
from pathlib import Path
import bcrypt

def crear_base_datos():
    """Crear base de datos completa con tablas y usuarios"""
    
    db_path = Path(__file__).parent / 'infofiscal.db'
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Creando tablas...")
        
        # Tabla usuarios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE,
                password_hash TEXT,
                intentos_fallidos INTEGER DEFAULT 0,
                bloqueado BOOLEAN DEFAULT 0
            )
        ''')
        
        # Tabla clientes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipoDocumento TEXT,
                nroDocumento TEXT,
                CUIT TEXT UNIQUE,
                apellido TEXT,
                nombres TEXT,
                fechaNacimiento TEXT,
                condicionIVA TEXT,
                categoriaMonotriibuto TEXT
            )
        ''')
        
        # Crear usuario admin si no existe
        cursor.execute('SELECT COUNT(*) FROM usuarios WHERE usuario = ?', ('admin',))
        if cursor.fetchone()[0] == 0:
            # Generar hash para password 'admin123'
            password = 'admin123'
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            cursor.execute('''
                INSERT INTO usuarios (usuario, password_hash, intentos_fallidos, bloqueado)
                VALUES (?, ?, 0, 0)
            ''', ('admin', password_hash))
            
            print("Usuario admin creado (password: admin123)")
        
        conn.commit()
        conn.close()
        
        print("✅ Base de datos creada exitosamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    crear_base_datos()