# src/db.py
# Pool de conexiones PostgreSQL con psycopg v3.
#
# Diseño:
#   - Un único pool global por proceso Flask.
#   - init_pool() se llama una vez desde app.py al crear la app.
#   - close_pool() se llama al teardown de la app (registrado en app.py).
#   - get_cursor() es el único punto de entrada a la DB en el sistema.
#     Ningún módulo abre conexiones directamente.
#
# Transacciones:
#   - psycopg v3 usa autocommit=False por defecto.
#   - get_cursor() hace commit al salir limpiamente, rollback ante excepción.
#   - Esto hace que cada bloque "with get_cursor() as cur:" sea una transacción.
#
# row_factory:
#   - Por defecto se usa dict_row: cada fila es un dict {columna: valor}.
#   - Más verboso pero elimina errores de índice numérico en queries complejas.
#   - Se puede pasar row_factory=tuple_row si se prefiere tupla en algún caso.

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

import psycopg
import psycopg.rows
from psycopg_pool import ConnectionPool

from src.config import Config

# Pool único por proceso. Se inicializa en init_pool().
_pool: ConnectionPool | None = None


def init_pool() -> None:
    """
    Crea e inicializa el pool de conexiones.
    Llama a pool.wait() para verificar que la DB es alcanzable al arrancar.
    Falla rápido con mensaje claro si la DB no está disponible.
    """
    global _pool

    _pool = ConnectionPool(
        conninfo=Config.DATABASE_URL,
        min_size=2,
        max_size=10,
        # kwargs que se pasan a cada conexión del pool:
        kwargs={
            # row_factory global: todos los cursores devuelven dicts por defecto.
            "row_factory": psycopg.rows.dict_row,
        },
        # No abrir conexiones en background antes de que alguien las pida.
        # open=False porque luego llamamos wait() explícitamente.
        open=False,
    )

    _pool.open()

    try:
        # Verifica que al menos una conexión puede establecerse.
        # Falla aquí si DATABASE_URL es incorrecta o PostgreSQL no está corriendo.
        _pool.wait(timeout=10)
    except Exception as e:
        raise RuntimeError(
            f"No se pudo conectar a PostgreSQL.\n"
            f"Verificá que el servicio esté corriendo (docker compose up -d).\n"
            f"DATABASE_URL: {Config.DATABASE_URL}\n"
            f"Error: {e}"
        ) from e


def close_pool() -> None:
    """Cierra el pool al apagar la app. Registrar en app.py con teardown_appcontext."""
    if _pool is not None:
        _pool.close()


@contextmanager
def get_cursor(
    row_factory=None,
    estudio_id: int | None = None,
) -> Generator[psycopg.Cursor, None, None]:
    """
    Context manager que provee un cursor dentro de una transacción.

        with get_cursor(estudio_id=g.user['estudio_id']) as cur:
            cur.execute("SELECT * FROM clientes WHERE estudio_id = %s", (estudio_id,))
            rows = cur.fetchall()

    - Commit automático al salir sin excepción.
    - Rollback automático si se lanza una excepción.
    - row_factory: None usa dict_row (default del pool).
    - estudio_id: si se pasa, setea app.estudio_id en la sesión PostgreSQL
      para que las RLS policies filtren automáticamente por tenant.
      Si es None (superadmin o scripts), no se setea y RLS permite todo.
    """
    assert _pool is not None, "init_pool() no fue llamado antes de get_cursor()"

    with _pool.connection() as conn:
        if row_factory is not None:
            conn.row_factory = row_factory

        # RLS: setear contexto de tenant para esta transacción
        if estudio_id is not None:
            conn.execute(
                "SET LOCAL app.estudio_id = %s", (str(estudio_id),)
            )

        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def health_check() -> dict:
    """
    Verifica la conexión a la DB. Útil para un endpoint /health.
    Retorna {"status": "ok", "db": "ok"} o {"status": "error", "db": str(error)}.
    """
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1 AS chk")
            row = cur.fetchone()
            assert row["chk"] == 1
        return {"status": "ok", "db": "ok"}
    except Exception as e:
        return {"status": "error", "db": str(e)}
