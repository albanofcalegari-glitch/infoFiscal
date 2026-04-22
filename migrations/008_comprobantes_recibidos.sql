-- migrations/008_comprobantes_recibidos.sql
-- Comprobantes recibidos (compras) para liquidación de IVA.

CREATE TABLE IF NOT EXISTS comprobantes_recibidos (
    id                  SERIAL       PRIMARY KEY,
    estudio_id          INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id          INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Emisor (proveedor)
    cuit_emisor         TEXT         NOT NULL,
    emisor_nombre       TEXT,
    -- Comprobante
    tipo_comprobante    INTEGER      NOT NULL,
    punto_venta         INTEGER      NOT NULL,
    numero              BIGINT       NOT NULL,
    fecha_emision       DATE         NOT NULL,
    -- Importes
    importe_total       NUMERIC(15,2) NOT NULL,
    importe_neto        NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_iva         NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_exento      NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_no_gravado  NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_tributos    NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- IVA discriminado
    iva_105             NUMERIC(15,2) DEFAULT 0,
    iva_21              NUMERIC(15,2) DEFAULT 0,
    iva_27              NUMERIC(15,2) DEFAULT 0,
    iva_5               NUMERIC(15,2) DEFAULT 0,
    iva_25              NUMERIC(15,2) DEFAULT 0,
    -- CAE
    cae                 TEXT,
    -- Origen
    origen              TEXT         DEFAULT 'manual',  -- manual, importacion, wsfe
    -- Metadata
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_comp_recibido UNIQUE (estudio_id, cuit_emisor, tipo_comprobante, punto_venta, numero)
);

CREATE INDEX IF NOT EXISTS idx_comp_recibidos_estudio
    ON comprobantes_recibidos (estudio_id, fecha_emision DESC);
