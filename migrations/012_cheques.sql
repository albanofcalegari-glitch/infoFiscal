-- migrations/012_cheques.sql
-- Gestión de cheques emitidos y recibidos.

CREATE TABLE IF NOT EXISTS cheques (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id      INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Tipo
    tipo            TEXT         NOT NULL CHECK (tipo IN ('emitido', 'recibido')),
    -- Datos del cheque
    banco           TEXT,
    nro_cheque      TEXT         NOT NULL,
    fecha_emision   DATE         NOT NULL,
    fecha_cobro     DATE,        -- fecha de vencimiento / cobro
    -- Importes
    importe         NUMERIC(15,2) NOT NULL,
    moneda          TEXT         NOT NULL DEFAULT 'ARS',
    -- Titulares
    librador        TEXT,        -- quien firma
    beneficiario    TEXT,        -- a favor de quien
    cuit_librador   TEXT,
    -- Estado
    estado          TEXT         NOT NULL DEFAULT 'cartera',
    -- cartera, depositado, cobrado, rechazado, endosado, vencido
    -- Metadata
    observaciones   TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cheques_estudio
    ON cheques (estudio_id, fecha_cobro);
CREATE INDEX IF NOT EXISTS idx_cheques_estado
    ON cheques (estudio_id, estado);
