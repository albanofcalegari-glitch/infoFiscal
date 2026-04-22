-- migrations/011_iibb.sql
-- Ingresos Brutos: declaraciones mensuales y anuales.

CREATE TABLE IF NOT EXISTS iibb_actividades (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id      INTEGER      REFERENCES clientes(id) ON DELETE CASCADE,
    -- Actividad
    codigo          TEXT         NOT NULL,
    descripcion     TEXT,
    jurisdiccion    TEXT         NOT NULL,  -- '901' CABA, '902' PBA, etc.
    alicuota        NUMERIC(8,4) NOT NULL,
    -- Vigencia
    desde           DATE,
    hasta           DATE,
    activa          BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS iibb_declaraciones (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id      INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Periodo
    periodo         TEXT         NOT NULL,   -- 'YYYY-MM' para CM03, 'YYYY' para CM05
    tipo            TEXT         NOT NULL CHECK (tipo IN ('CM03', 'CM05')),
    -- Jurisdicciones (JSON array)
    detalle_json    JSONB,
    -- Totales
    base_imponible  NUMERIC(15,2) NOT NULL DEFAULT 0,
    impuesto        NUMERIC(15,2) NOT NULL DEFAULT 0,
    retenciones     NUMERIC(15,2) NOT NULL DEFAULT 0,
    percepciones    NUMERIC(15,2) NOT NULL DEFAULT 0,
    saldo_anterior  NUMERIC(15,2) NOT NULL DEFAULT 0,
    total_a_pagar   NUMERIC(15,2) NOT NULL DEFAULT 0,
    -- Estado
    estado          TEXT         NOT NULL DEFAULT 'borrador',  -- borrador, presentada, rectificativa
    -- XML para SIFERE
    xml_sifere      TEXT,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_iibb_decl UNIQUE (estudio_id, cliente_id, periodo, tipo)
);

CREATE INDEX IF NOT EXISTS idx_iibb_decl_estudio
    ON iibb_declaraciones (estudio_id, periodo DESC);
