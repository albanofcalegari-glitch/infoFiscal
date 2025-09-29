#!/usr/bin/env python3
"""
Agregar tu propio CUIT como cliente en la base de datos
"""

import sqlite3
from pathlib import Path

def agregar_cuit_propio():
    """Agregar tu CUIT principal como cliente"""
    
    db_path = Path(__file__).parent / 'infofiscal.db'
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Tu CUIT principal
        cuit = "20321518045"
        nombre = "TU EMPRESA PRINCIPAL"
        
        # Verificar si ya existe
        cursor.execute("SELECT * FROM clientes WHERE CUIT = ?", (cuit,))
        if cursor.fetchone():
            print(f"✅ CUIT {cuit} ya existe en la base de datos")
        else:
            # Insertar tu CUIT
            cursor.execute("""
                INSERT INTO clientes (tipoDocumento, nroDocumento, CUIT, apellido, nombres, condicionIVA) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, ("CUIT", cuit, cuit, "EMPRESA", "PRINCIPAL", "Responsable Inscripto"))
            
            conn.commit()
            print(f"✅ CUIT {cuit} agregado exitosamente")
            print(f"   Nombre: EMPRESA PRINCIPAL")
        
        # Mostrar todos los clientes
        print("\n📋 CLIENTES EN BASE DE DATOS:")
        cursor.execute("SELECT CUIT, apellido, nombres FROM clientes ORDER BY CUIT")
        clientes = cursor.fetchall()
        
        for cuit_db, apellido, nombres in clientes:
            nombre_completo = f"{apellido}, {nombres}" if apellido and nombres else "Sin nombre"
            print(f"   {cuit_db} - {nombre_completo}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    agregar_cuit_propio()