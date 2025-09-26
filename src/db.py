
import sqlite3
from pathlib import Path
import bcrypt

def crear_base_datos():
    db_path = Path(__file__).parent.parent / 'infofiscal.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuario (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            fechaUltimoLogin TEXT,
            cantidadDeIntentos INTEGER DEFAULT 0,
            bloqueado INTEGER DEFAULT 0
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipoDocumento TEXT NOT NULL,
            nroDocumento TEXT NOT NULL,
            CUIT TEXT,
            apellido TEXT,
            nombres TEXT,
            fechaNacimiento TEXT,
            condicionIVA TEXT,
            categoriaMonotriibuto TEXT
        )
    ''')

    conn.commit()
    conn.close()


# Funciones para manejo seguro de contraseñas
def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed

def check_password(password: str, hashed: bytes) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed)


def insertar_usuario(usuario: str, contrasena: str):
    db_path = Path(__file__).parent.parent / 'infofiscal.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    hashed = hash_password(contrasena)
    cursor.execute('''
        INSERT OR IGNORE INTO usuario (usuario, contrasena)
        VALUES (?, ?)
    ''', (usuario, hashed))
    conn.commit()
    conn.close()


if __name__ == '__main__':
    crear_base_datos()
    insertar_usuario('admin', 'admin01')
    insertar_usuario('oper', '1234')

if __name__ == '__main__':
    crear_base_datos()
