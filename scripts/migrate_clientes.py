"""
scripts/migrate_clientes.py
Migra datos de la tabla clientes desde SQLite a PostgreSQL.

Fase 2: ejecutar DESPUÉS de haber corrido 002_clientes.sql en PostgreSQL
y haber verificado que la app funciona con la tabla vacía.

Uso:
    python scripts/migrate_clientes.py

Requisitos:
    - .env con DATABASE_URL configurado
    - PostgreSQL corriendo con tabla clientes creada (002_clientes.sql)
    - infofiscal.db accesible en la raíz del proyecto
    - Al menos un estudio existente en PostgreSQL
"""

import sqlite3
import sys
from pathlib import Path

# Agregar src al path para importar módulos del proyecto
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv(project_root / '.env')

from src.db import init_pool, close_pool, get_cursor

# Mapeo de valores sucios en SQLite → valores válidos del CHECK en PostgreSQL.
# Las claves van en minúscula porque se comparan con .lower().
_TIPO_DOC_MAP = {
    'dni': 'DNI', 'doc': 'DNI', 'documento': 'DNI',
    'le': 'LE', 'libreta de enrolamiento': 'LE',
    'lc': 'LC', 'libreta civica': 'LC', 'libreta cívica': 'LC',
    'cuit': 'CUIT',
}

_VALORES_VALIDOS = {'DNI', 'LE', 'LC', 'CUIT'}


def _normalizar_tipo_documento(valor: str | None) -> str | None:
    """Normaliza tipo_documento al formato que acepta el CHECK de PostgreSQL."""
    if not valor or not valor.strip():
        return None
    limpio = valor.strip()
    # Lookup por lowercase
    mapeado = _TIPO_DOC_MAP.get(limpio.lower())
    if mapeado:
        return mapeado
    # Ya es un valor válido tal cual
    if limpio in _VALORES_VALIDOS:
        return limpio
    return None  # Valor no reconocido → se saltea en insert


def get_sqlite_clientes(db_path: Path) -> list[dict]:
    """Lee todos los clientes de SQLite."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, tipoDocumento, nroDocumento, CUIT, apellido, nombres,
               fechaNacimiento, condicionIVA, categoriaMonotriibuto
        FROM clientes
        ORDER BY id
    """)

    clientes = []
    for row in cursor.fetchall():
        clientes.append({
            'tipo_documento_orig': row['tipoDocumento'],
            'tipo_documento': _normalizar_tipo_documento(row['tipoDocumento']),
            'nro_documento': row['nroDocumento'],
            'cuit': row['CUIT'] if row['CUIT'] else None,
            'apellido': row['apellido'],
            'nombres': row['nombres'],
            'fecha_nacimiento': row['fechaNacimiento'] if row['fechaNacimiento'] else None,
            'condicion_iva': row['condicionIVA'] if row['condicionIVA'] else None,
            'categoria_monotributo': row['categoriaMonotriibuto'] if row['categoriaMonotriibuto'] else None,
        })

    conn.close()
    return clientes


def get_estudios() -> list[dict]:
    """Lista estudios disponibles en PostgreSQL."""
    with get_cursor() as cur:
        cur.execute("SELECT id, nombre, email FROM estudios ORDER BY id")
        return cur.fetchall()


def insert_clientes(clientes: list[dict], estudio_id: int) -> dict:
    """Inserta clientes en PostgreSQL con SAVEPOINT por fila.
    Retorna {'inserted': int, 'skipped': int, 'errors': list[str]}."""
    inserted = 0
    skipped = 0
    errors = []

    with get_cursor() as cur:
        for c in clientes:
            label = f"{c['apellido']}, {c['nombres']} ({c.get('tipo_documento_orig', '?')})"

            # Saltear si tipo_documento no se pudo normalizar
            if not c['tipo_documento']:
                skipped += 1
                print(f"  SKIP: {label} — tipo_documento no reconocido")
                continue

            try:
                cur.execute("SAVEPOINT cliente_sp")
                cur.execute("""
                    INSERT INTO clientes (estudio_id, tipo_documento, nro_documento, cuit,
                                          apellido, nombres, fecha_nacimiento,
                                          condicion_iva, categoria_monotributo)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (estudio_id, tipo_documento, nro_documento) DO NOTHING
                """, (
                    estudio_id,
                    c['tipo_documento'],
                    c['nro_documento'],
                    c['cuit'],
                    c['apellido'],
                    c['nombres'],
                    c['fecha_nacimiento'],
                    c['condicion_iva'],
                    c['categoria_monotributo'],
                ))
                cur.execute("RELEASE SAVEPOINT cliente_sp")
                inserted += 1
            except Exception as e:
                cur.execute("ROLLBACK TO SAVEPOINT cliente_sp")
                errors.append(label)
                print(f"  ERROR: {label} — {e}")

    return {'inserted': inserted, 'skipped': skipped, 'errors': errors}


def main():
    db_path = project_root / 'infofiscal.db'

    if not db_path.exists():
        print(f"ERROR: No se encontró {db_path}")
        sys.exit(1)

    # Leer clientes de SQLite
    clientes = get_sqlite_clientes(db_path)
    print(f"Clientes encontrados en SQLite: {len(clientes)}")

    if not clientes:
        print("No hay clientes para migrar.")
        return

    # Mostrar preview
    print("\nPreview de los primeros 5 clientes:")
    for c in clientes[:5]:
        print(f"  {c['apellido']}, {c['nombres']} — {c['tipo_documento']} {c['nro_documento']} — CUIT: {c['cuit'] or 'N/A'}")

    # Conectar a PostgreSQL
    init_pool()

    try:
        # Listar estudios disponibles
        estudios = get_estudios()
        if not estudios:
            print("\nERROR: No hay estudios en PostgreSQL. Cree uno primero con create_admin.py")
            sys.exit(1)

        print(f"\nEstudios disponibles:")
        for e in estudios:
            print(f"  [{e['id']}] {e['nombre']} ({e['email']})")

        if len(estudios) == 1:
            estudio_id = estudios[0]['id']
            print(f"\nUsando único estudio disponible: [{estudio_id}] {estudios[0]['nombre']}")
        else:
            estudio_id = int(input("\nIngrese el ID del estudio destino: "))

        # Confirmar
        resp = input(f"\n¿Migrar {len(clientes)} clientes al estudio {estudio_id}? (s/N): ")
        if resp.lower() != 's':
            print("Cancelado.")
            return

        # Insertar
        result = insert_clientes(clientes, estudio_id)
        print(f"\n{'='*50}")
        print(f"Migración completada:")
        print(f"  Insertados: {result['inserted']}")
        print(f"  Salteados:  {result['skipped']}")
        print(f"  Errores:    {len(result['errors'])}")
        if result['errors']:
            print(f"\nClientes con error:")
            for err in result['errors']:
                print(f"  - {err}")
        print(f"\nVerifique los datos y luego puede eliminar infofiscal.db si todo está correcto.")

    finally:
        close_pool()


if __name__ == '__main__':
    main()
