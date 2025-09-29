#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('infofiscal.db')
cursor = conn.cursor()
cursor.execute('SELECT CUIT, apellido, nombres, tipoDocumento, nroDocumento FROM clientes')
clientes = cursor.fetchall()

print('CLIENTES EN BASE DE DATOS:')
print('=' * 50)
for cuit, apellido, nombres, tipo, nro in clientes:
    print(f'{cuit} - {apellido}, {nombres}')
    print(f'  Tipo: {tipo or "NULL"} | Nro: {nro or "NULL"}')
    print()
conn.close()