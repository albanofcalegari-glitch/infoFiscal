-- migrations/001_initial.sql
-- Schema inicial: estudios (tenants), usuarios, sesiones.
-- Tablas de negocio (clientes, comprobantes) van en migraciones posteriores.
--
-- Diseño multi-tenant:
--   - Toda tabla de negocio lleva estudio_id.
--   - El aislamiento se enforcea en código (repo layer), no en DB (RLS no usado en MVP).
--   - superadmin tiene estudio_id NULL — único caso donde el campo puede ser NULL.

-- ══════════════════════════════════════════════════════════════════════════════
-- ENUM de roles
-- Uso de bloque DO para idempotencia (PostgreSQL no soporta CREATE TYPE IF NOT EXISTS)
-- ══════════════════════════════════════════════════════════════════════════════
DO $$ BEGIN
    CREATE TYPE rol_usuario AS ENUM ('superadmin', 'admin', 'contador', 'readonly');
EXCEPTION
    WHEN duplicate_object THEN NULL;
END $$;

-- ══════════════════════════════════════════════════════════════════════════════
-- ESTUDIOS — cada fila es un tenant (estudio contable)
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS estudios (
    id          SERIAL       PRIMARY KEY,
    nombre      TEXT         NOT NULL,
    email       TEXT         NOT NULL UNIQUE,
    activo      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ══════════════════════════════════════════════════════════════════════════════
-- USUARIOS
--
-- estudio_id NULL  → superadmin de la plataforma (no pertenece a ningún estudio)
-- estudio_id NOT NULL → usuario de un estudio específico
--
-- Unicidad de email:
--   - Dentro de un estudio: (estudio_id, email) es único → constraint de tabla
--   - Para superadmin (estudio_id NULL): índice parcial separado
--     (los constraints UNIQUE no cubren NULLs en PostgreSQL)
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS usuarios (
    id                SERIAL       PRIMARY KEY,
    estudio_id        INTEGER      REFERENCES estudios(id) ON DELETE RESTRICT,
    nombre            TEXT         NOT NULL,
    email             TEXT         NOT NULL,
    password_hash     TEXT         NOT NULL,
    rol               rol_usuario  NOT NULL,
    activo            BOOLEAN      NOT NULL DEFAULT TRUE,
    ultimo_login      TIMESTAMPTZ,
    intentos_fallidos INTEGER      NOT NULL DEFAULT 0,
    bloqueado_hasta   TIMESTAMPTZ,
    created_at        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    -- email único por estudio (cubre los casos estudio_id NOT NULL)
    CONSTRAINT uq_usuario_email_estudio UNIQUE (estudio_id, email),

    -- superadmin solo puede tener rol superadmin
    CONSTRAINT chk_superadmin_rol CHECK (
        (estudio_id IS NULL AND rol = 'superadmin') OR
        (estudio_id IS NOT NULL AND rol <> 'superadmin')
    )
);

-- Unicidad de email para superadmin (estudio_id IS NULL)
-- Índice parcial porque UNIQUE no cubre NULL en PostgreSQL.
CREATE UNIQUE INDEX IF NOT EXISTS uq_superadmin_email
    ON usuarios (email)
    WHERE estudio_id IS NULL;

-- ══════════════════════════════════════════════════════════════════════════════
-- SESIONES
--
-- id: token firmado (itsdangerous). Se guarda en DB para permitir revocación
--     sin necesidad de cambiar SECRET_KEY.
-- revocada: TRUE al hacer logout o al forzar cierre de sesión desde admin.
-- Sesiones expiradas se limpian periódicamente (ver auth/service.py).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS sesiones (
    id          TEXT         PRIMARY KEY,   -- token firmado, no predecible
    usuario_id  INTEGER      NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    ip          TEXT,
    user_agent  TEXT,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at  TIMESTAMPTZ  NOT NULL,
    revocada    BOOLEAN      NOT NULL DEFAULT FALSE
);

-- ══════════════════════════════════════════════════════════════════════════════
-- ÍNDICES
-- ══════════════════════════════════════════════════════════════════════════════

-- Búsqueda de usuario por email al hacer login
CREATE INDEX IF NOT EXISTS idx_usuarios_email
    ON usuarios (email);

-- Filtro de usuarios por estudio (listar usuarios del estudio)
CREATE INDEX IF NOT EXISTS idx_usuarios_estudio
    ON usuarios (estudio_id);

-- Validación de sesión activa (path crítico en cada request autenticado)
CREATE INDEX IF NOT EXISTS idx_sesiones_activas
    ON sesiones (id)
    WHERE revocada = FALSE;

-- Limpieza de sesiones expiradas (tarea periódica)
CREATE INDEX IF NOT EXISTS idx_sesiones_expires
    ON sesiones (expires_at)
    WHERE revocada = FALSE;
