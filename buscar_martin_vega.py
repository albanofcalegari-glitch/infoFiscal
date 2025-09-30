#!/usr/bin/env python3
"""
Script para buscar el CUIT de Martín Vega en la base de datos
"""

import sqlite3

try:
    # Conectar a la base de datos
    conn = sqlite3.connect('infofiscal.db')
    cursor = conn.cursor()
    
    # Primero ver la estructura de la tabla
    cursor.execute("PRAGMA table_info(clientes)")
    columns = cursor.fetchall()
    print("Columnas de la tabla 'clientes':")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    print()
    
    # Buscar todos los registros para ver la estructura
    cursor.execute("SELECT * FROM clientes LIMIT 5")
    sample = cursor.fetchall()
    print("Primeros 5 registros:")
    for i, row in enumerate(sample):
        print(f"  Registro {i+1}: {row}")
    print()
    
    # Intentar buscar por cualquier campo que contenga 'martin' o 'vega'
    cursor.execute("SELECT * FROM clientes")
    all_records = cursor.fetchall()
    
    print("Buscando 'martin' o 'vega' en todos los campos...")
    found = []
    for record in all_records:
        record_str = str(record).lower()
        if 'martin' in record_str or 'vega' in record_str:
            found.append(record)
    
    if found:
        print("Registros encontrados:")
        for r in found:
            print(f"  {r}")
    else:
        print("No se encontraron registros con 'martin' o 'vega'")
    
    results = cursor.fetchall()
    
    print("=== Búsqueda de Martín Vega ===")
    if results:
        print(f"Se encontraron {len(results)} cliente(s):")
        for r in results:
            print(f"  ID: {r[0]}")
            print(f"  Nombre: {r[1]}")
            print(f"  Apellido: {r[2]}")
            print(f"  CUIT: {r[3]}")
            print(f"  Condición IVA: {r[4] if len(r) > 4 else 'No especificada'}")
            print("-" * 40)
    else:
        print("No se encontró ningún cliente con ese nombre.")
        print("\nMostrando todos los clientes para referencia:")
        cursor.execute("SELECT * FROM clientes LIMIT 10")
        all_results = cursor.fetchall()
        for r in all_results:
            print(f"  {r[0]}: {r[1]} {r[2]} - CUIT: {r[3]}")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")