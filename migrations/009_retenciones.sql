-- migrations/009_retenciones.sql
-- Retenciones sufridas y practicadas.

CREATE TABLE IF NOT EXISTS retenciones (
    id                  SERIAL       PRIMARY KEY,
    estudio_id          INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id          INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Tipo
    tipo                TEXT         NOT NULL CHECK (tipo IN ('sufrida', 'practicada')),
    -- Régimen
    regimen_codigo      TEXT,
    regimen_descripcion TEXT,
    -- Agente
    cuit_agente         TEXT         NOT NULL,
    nombre_agente       TEXT,
    -- Sujeto retenido
    cuit_retenido       TEXT,
    nombre_retenido     TEXT,
    -- Comprobante origen
    tipo_comprobante    INTEGER,
    nro_comprobante     TEXT,
    -- Certificado de retención
    nro_certificado     TEXT,
    fecha               DATE         NOT NULL,
    -- Importes
    importe_base        NUMERIC(15,2),
    alicuota            NUMERIC(8,4),
    importe_retenido    NUMERIC(15,2) NOT NULL,
    -- Impuesto
    impuesto            TEXT         NOT NULL DEFAULT 'iva',  -- iva, ganancias, iibb, suss
    jurisdiccion        TEXT,  -- para IIBB: 'CABA', 'PBA', 'CBA', etc.
    -- Origen
    origen              TEXT         DEFAULT 'manual',  -- manual, importacion, padron
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_retenciones_estudio
    ON retenciones (estudio_id, fecha DESC);
CREATE INDEX IF NOT EXISTS idx_retenciones_cliente
    ON retenciones (cliente_id);

-- Consultas a padrones de retención (cache)
CREATE TABLE IF NOT EXISTS padron_retenciones_cache (
    id              SERIAL       PRIMARY KEY,
    jurisdiccion    TEXT         NOT NULL,    -- 'AGIP', 'ARBA', 'CBA'
    cuit            TEXT         NOT NULL,
    alicuota_ret    NUMERIC(8,4),
    alicuota_perc   NUMERIC(8,4),
    desde           DATE,
    hasta           DATE,
    grupo           TEXT,
    consultado_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_padron_cache UNIQUE (jurisdiccion, cuit, desde)
);
