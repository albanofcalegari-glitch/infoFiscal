import sqlite3
import os

# Script para agregar un CUIT empresarial de ejemplo

os.chdir(r'c:\Users\DELL\Desktop\proyectos python\infofiscal')

try:
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    # Agregar un CUIT empresarial de ejemplo (Empresa ficticia)
    cursor.execute('''
        INSERT INTO clientes (tipoDocumento, nroDocumento, CUIT, apellido, nombres, 
                             fechaNacimiento, condicionIVA, categoriaMonotriibuto)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        'CUIT', 
        '30500001733',
        '30-50000173-3', 
        'EMPRESA DEMO S.A.', 
        'FACTURACION ELECTRONICA',
        '2000-01-01',
        'Responsable Inscripto',
        ''
    ))
    
    conn.commit()
    conn.close()
    
    print("✅ Cliente empresarial agregado:")
    print("   CUIT: 30-50000173-3")
    print("   Razón Social: EMPRESA DEMO S.A.")
    print("   Condición: Responsable Inscripto")
    print("   💡 Este CUIT es más probable que tenga facturas electrónicas")
    
except Exception as e:
    print(f"❌ Error: {e}")