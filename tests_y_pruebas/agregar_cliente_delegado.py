"""
Script para agregar el CUIT delegado a la base de datos
"""

import sqlite3
from pathlib import Path

def agregar_cliente_delegado():
    """Agregar CUIT de VEGA MARTIN MATIAS a la base de datos"""
    
    db_path = Path(__file__).parent / 'infofiscal.db'
    
    # Datos del cliente delegado
    cliente_data = {
        'tipoDocumento': 'cuit',
        'nroDocumento': '23333730219', 
        'CUIT': '23333730219',
        'apellido': 'VEGA',
        'nombres': 'MARTIN MATIAS',
        'fechaNacimiento': '1990-01-01',  # Fecha estimada
        'condicionIVA': 'Responsable Inscripto',  # Asumir RI por facturación electrónica
        'categoriaMonotriibuto': ''  # No aplica si es RI
    }
    
    print("Agregando cliente delegado a la base de datos...")
    print(f"CUIT: {cliente_data['CUIT']}")
    print(f"Nombre: {cliente_data['nombres']} {cliente_data['apellido']}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar si ya existe
        cursor.execute('SELECT COUNT(*) FROM clientes WHERE CUIT = ?', (cliente_data['CUIT'],))
        existe = cursor.fetchone()[0]
        
        if existe:
            print("✅ El cliente ya existe en la base de datos")
        else:
            # Insertar nuevo cliente
            cursor.execute('''
                INSERT INTO clientes (tipoDocumento, nroDocumento, CUIT, apellido, nombres, fechaNacimiento, condicionIVA, categoriaMonotriibuto)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                cliente_data['tipoDocumento'],
                cliente_data['nroDocumento'], 
                cliente_data['CUIT'],
                cliente_data['apellido'],
                cliente_data['nombres'],
                cliente_data['fechaNacimiento'],
                cliente_data['condicionIVA'],
                cliente_data['categoriaMonotriibuto']
            ))
            
            conn.commit()
            print("✅ Cliente agregado exitosamente")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    agregar_cliente_delegado()