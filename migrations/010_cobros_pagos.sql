-- migrations/010_cobros_pagos.sql
-- Cobros y pagos: cuentas corrientes de clientes y proveedores.

CREATE TABLE IF NOT EXISTS cuentas_corrientes (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id      INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Proveedor (si no es cliente)
    cuit            TEXT,
    nombre          TEXT         NOT NULL,
    tipo            TEXT         NOT NULL CHECK (tipo IN ('cliente', 'proveedor')),
    -- Saldo actual (se actualiza con cada movimiento)
    saldo           NUMERIC(15,2) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_cc UNIQUE (estudio_id, tipo, cuit)
);

CREATE TABLE IF NOT EXISTS movimientos_cc (
    id              SERIAL       PRIMARY KEY,
    cuenta_id       INTEGER      NOT NULL REFERENCES cuentas_corrientes(id) ON DELETE CASCADE,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    -- Movimiento
    fecha           DATE         NOT NULL,
    tipo_mov        TEXT         NOT NULL CHECK (tipo_mov IN ('factura', 'pago', 'cobro', 'nota_credito', 'nota_debito', 'ajuste')),
    descripcion     TEXT,
    -- Referencia a comprobante (opcional)
    comprobante_ref TEXT,
    -- Importes
    debe            NUMERIC(15,2) NOT NULL DEFAULT 0,
    haber           NUMERIC(15,2) NOT NULL DEFAULT 0,
    saldo_parcial   NUMERIC(15,2),
    -- Metadata
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mov_cc_cuenta
    ON movimientos_cc (cuenta_id, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_cc_estudio
    ON cuentas_corrientes (estudio_id);
