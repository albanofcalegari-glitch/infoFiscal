-- migrations/013_notificaciones.sql
-- Sistema de notificaciones y alertas internas.

CREATE TABLE IF NOT EXISTS notificaciones (
    id              SERIAL       PRIMARY KEY,
    estudio_id      INTEGER      NOT NULL REFERENCES estudios(id) ON DELETE CASCADE,
    usuario_id      INTEGER      REFERENCES usuarios(id) ON DELETE CASCADE,
    -- Contenido
    titulo          TEXT         NOT NULL,
    mensaje         TEXT         NOT NULL,
    tipo            TEXT         NOT NULL DEFAULT 'info',
    -- info, warning, danger, success
    categoria       TEXT         NOT NULL DEFAULT 'sistema',
    -- sistema, vencimiento, limite, membresia, monotributo, cheque
    -- Referencia (opcional)
    url             TEXT,
    -- Estado
    leida           BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notif_usuario
    ON notificaciones (usuario_id, leida, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_notif_estudio
    ON notificaciones (estudio_id, created_at DESC);
