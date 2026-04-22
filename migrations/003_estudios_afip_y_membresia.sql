-- migrations/003_estudios_afip_y_membresia.sql
-- Multi-tenant completo: credenciales AFIP por estudio + campos de membresia.
--
-- Cambios:
--   1. estudios_afip: credenciales AFIP (cert, key, portal) por estudio.
--   2. estudios: campos de membresia (plan, vencimiento, trial).
--   3. Scoping de archivos: el path incluye estudio_id (se maneja en código).

-- ══════════════════════════════════════════════════════════════════════════════
-- ENUM de planes de membresia
-- ══════════════════════════════════════════════════════════════════════════════
DO $$ BEGIN
    CREATE TYPE plan_membresia AS ENUM ('trial', 'basico', 'profesional', 'enterprise');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ══════════════════════════════════════════════════════════════════════════════
-- ESTUDIOS — agregar campos de membresia
-- ══════════════════════════════════════════════════════════════════════════════
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS cuit              TEXT;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS telefono          TEXT;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS domicilio         TEXT;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS plan              plan_membresia NOT NULL DEFAULT 'trial';
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS membresia_hasta   DATE;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS max_clientes      INTEGER NOT NULL DEFAULT 10;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS max_usuarios      INTEGER NOT NULL DEFAULT 2;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS max_consultas_mes INTEGER NOT NULL DEFAULT 100;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS consultas_mes     INTEGER NOT NULL DEFAULT 0;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS consultas_reset   DATE;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS notas_admin       TEXT;
ALTER TABLE estudios ADD COLUMN IF NOT EXISTS updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- ══════════════════════════════════════════════════════════════════════════════
-- ESTUDIOS_AFIP — credenciales AFIP por estudio
--
-- Cada estudio contable tiene su propio certificado digital y CUIT solicitante.
-- Las credenciales del portal (clave fiscal) son opcionales (para RCEL scraping).
--
-- Seguridad:
--   - portal_password se almacena encriptado (Fernet). La key de encriptación
--     está en SECRET_KEY del .env (no en la DB).
--   - cert y key se almacenan como BYTEA (blob) para no depender del filesystem.
--   - También se soporta path al filesystem (retrocompatible).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS estudios_afip (
    id                  SERIAL       PRIMARY KEY,
    estudio_id          INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    -- CUIT del estudio que firma los TRA (solicitante)
    solicitante_cuit    TEXT         NOT NULL,
    -- Certificado digital (una de las dos formas)
    cert_path           TEXT,                   -- path en filesystem (legacy)
    cert_blob           BYTEA,                  -- contenido del .crt
    key_path            TEXT,                   -- path en filesystem (legacy)
    key_blob            BYTEA,                  -- contenido del .key
    -- Ambiente AFIP
    ambiente             TEXT        NOT NULL DEFAULT 'prod' CHECK (ambiente IN ('prod', 'homo')),
    -- Portal AFIP (opcional, para RCEL scraping)
    portal_cuit          TEXT,
    portal_password_enc  TEXT,                  -- encriptado con Fernet(SECRET_KEY)
    -- Metadata
    activo               BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Un estudio puede tener varias configs (prod + homo), pero solo una activa por ambiente
    CONSTRAINT uq_estudio_afip_ambiente UNIQUE (estudio_id, ambiente, activo)
);

CREATE INDEX IF NOT EXISTS idx_estudios_afip_estudio
    ON estudios_afip (estudio_id);

-- ══════════════════════════════════════════════════════════════════════════════
-- AUDITORÍA: log de consultas AFIP por estudio (para facturación/cuota)
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS consultas_log (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE RESTRICT,
    usuario_id      INTEGER      REFERENCES usuarios(id) ON DELETE SET NULL,
    cuit_consultado TEXT         NOT NULL,
    servicio        TEXT         NOT NULL,       -- 'WSFEv1', 'RCEL_emitidos', 'RCEL_recibidos'
    cantidad        INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_consultas_log_estudio_fecha
    ON consultas_log (estudio_id, created_at);
