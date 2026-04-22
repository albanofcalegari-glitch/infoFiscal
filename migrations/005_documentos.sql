-- migrations/005_documentos.sql
-- Gestión documental: adjuntar archivos a clientes y comprobantes.
--
-- Almacenamiento en filesystem (uploads/<estudio_id>/<año>/), referencia en DB.
-- Scoped por estudio_id para multi-tenant.

CREATE TABLE IF NOT EXISTS documentos (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    -- Relación polimórfica: puede estar asociado a un cliente o a un comprobante
    cliente_id      INTEGER      REFERENCES clientes(id) ON DELETE SET NULL,
    -- Si es comprobante AFIP, guardar referencia
    comprobante_cuit       TEXT,
    comprobante_tipo       INTEGER,
    comprobante_pv         INTEGER,
    comprobante_nro        INTEGER,
    -- Archivo
    nombre_original TEXT         NOT NULL,
    nombre_storage  TEXT         NOT NULL,   -- nombre en disco (UUID)
    ruta_storage    TEXT         NOT NULL,   -- path relativo desde uploads/
    mime_type       TEXT,
    tamano_bytes    BIGINT,
    -- Categoría libre
    categoria       TEXT         DEFAULT 'general',  -- general, factura, contrato, recibo, otro
    descripcion     TEXT,
    -- Metadata
    subido_por      INTEGER      REFERENCES usuarios(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_documentos_estudio
    ON documentos (estudio_id);
CREATE INDEX IF NOT EXISTS idx_documentos_cliente
    ON documentos (cliente_id);
CREATE INDEX IF NOT EXISTS idx_documentos_comprobante
    ON documentos (comprobante_cuit, comprobante_tipo, comprobante_pv, comprobante_nro);
