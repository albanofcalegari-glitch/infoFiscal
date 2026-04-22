-- migrations/006_monotributo_monitor.sql
-- Facturación acumulada por cliente para monitoreo de monotributo.
-- Se actualiza cada vez que se importan/consultan comprobantes.

CREATE TABLE IF NOT EXISTS monotributo_facturacion (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    cliente_id      INTEGER      NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    periodo         TEXT         NOT NULL,    -- 'YYYY-MM'
    monto_facturado NUMERIC(15,2) NOT NULL DEFAULT 0,
    cantidad_comp   INTEGER      NOT NULL DEFAULT 0,
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_mt_fact UNIQUE (estudio_id, cliente_id, periodo)
);

CREATE INDEX IF NOT EXISTS idx_mt_fact_cliente
    ON monotributo_facturacion (cliente_id, periodo);
