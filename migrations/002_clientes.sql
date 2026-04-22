-- migrations/002_clientes.sql
-- Tabla clientes — migración desde SQLite a PostgreSQL.
--
-- Multi-tenant: cada cliente pertenece a un estudio (estudio_id NOT NULL).
-- Unicidad: mismo documento no puede repetirse dentro del mismo estudio.
-- Columnas renombradas a snake_case (estándar PostgreSQL).

-- ══════════════════════════════════════════════════════════════════════════════
-- CLIENTES
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS clientes (
    id                    SERIAL       PRIMARY KEY,
    estudio_id            INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    tipo_documento        TEXT         NOT NULL CHECK (tipo_documento IN ('DNI', 'LE', 'LC', 'CUIT')),
    nro_documento         TEXT         NOT NULL,
    cuit                  TEXT,
    apellido              TEXT         NOT NULL,
    nombres               TEXT         NOT NULL,
    fecha_nacimiento      DATE,
    condicion_iva         TEXT,
    categoria_monotributo TEXT,
    created_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- Un cliente no puede tener el mismo documento en el mismo estudio
    CONSTRAINT uq_cliente_doc_estudio UNIQUE (estudio_id, tipo_documento, nro_documento)
);

-- ══════════════════════════════════════════════════════════════════════════════
-- ÍNDICES
-- ══════════════════════════════════════════════════════════════════════════════

-- Filtro por estudio (path crítico: todas las queries filtran por estudio_id)
CREATE INDEX IF NOT EXISTS idx_clientes_estudio
    ON clientes (estudio_id);

-- Búsqueda por CUIT (solo filas con CUIT no nulo)
CREATE INDEX IF NOT EXISTS idx_clientes_cuit
    ON clientes (cuit)
    WHERE cuit IS NOT NULL;

-- Búsqueda por número de documento
CREATE INDEX IF NOT EXISTS idx_clientes_nro_doc
    ON clientes (nro_documento);

-- Búsqueda por apellido (LIKE LOWER)
CREATE INDEX IF NOT EXISTS idx_clientes_apellido
    ON clientes (LOWER(apellido) text_pattern_ops);
