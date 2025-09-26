import sqlite3
from pathlib import Path
import bcrypt

def hash_password(password: str) -> bytes:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt)

db_path = Path(__file__).parent.parent / 'infofiscal.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
hashed = hash_password('1234')
cursor.execute('''
    INSERT OR REPLACE INTO usuario (usuario, contrasena, cantidadDeIntentos, bloqueado)
    VALUES (?, ?, 0, 0)
''', ('oper', hashed))
conn.commit()
conn.close()