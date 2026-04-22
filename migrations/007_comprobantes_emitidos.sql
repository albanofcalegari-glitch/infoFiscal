-- migrations/007_comprobantes_emitidos.sql
-- Almacena comprobantes electrónicos emitidos con CAE.

CREATE TABLE IF NOT EXISTS comprobantes_emitidos (
    id                  SERIAL       PRIMARY KEY,
    estudio_id          INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    -- Emisor
    cuit_emisor         TEXT         NOT NULL,
    -- Receptor
    cuit_receptor       TEXT,
    receptor_nombre     TEXT,
    tipo_doc_receptor   INTEGER      DEFAULT 80,  -- 80=CUIT, 96=DNI, 99=Sin identificar
    nro_doc_receptor    TEXT,
    -- Comprobante
    tipo_comprobante    INTEGER      NOT NULL,
    punto_venta         INTEGER      NOT NULL,
    numero_desde        BIGINT       NOT NULL,
    numero_hasta        BIGINT       NOT NULL,
    fecha_emision       DATE         NOT NULL,
    -- Importes
    importe_total       NUMERIC(15,2) NOT NULL,
    importe_neto        NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_iva         NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_tributos    NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_exento      NUMERIC(15,2) NOT NULL DEFAULT 0,
    importe_no_gravado  NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Concepto
    concepto            INTEGER      NOT NULL DEFAULT 1,  -- 1=Productos, 2=Servicios, 3=Ambos
    fecha_serv_desde    DATE,
    fecha_serv_hasta    DATE,
    fecha_vto_pago      DATE,
    -- CAE
    cae                 TEXT,
    cae_vto             DATE,
    -- Estado
    estado              TEXT         NOT NULL DEFAULT 'autorizado', -- autorizado, rechazado, observado
    observaciones       TEXT,
    -- Items (JSON)
    items_json          JSONB,
    -- IVA detalle (JSON)
    iva_json            JSONB,
    -- Metadata
    moneda              TEXT         NOT NULL DEFAULT 'PES',
    cotizacion          NUMERIC(15,6) NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_comp_emitido UNIQUE (cuit_emisor, tipo_comprobante, punto_venta, numero_desde)
);

CREATE INDEX IF NOT EXISTS idx_comp_emitidos_estudio
    ON comprobantes_emitidos (estudio_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_comp_emitidos_cuit
    ON comprobantes_emitidos (cuit_emisor, fecha_emision DESC);
