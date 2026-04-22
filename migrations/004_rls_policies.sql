-- migrations/004_rls_policies.sql
-- Row-Level Security (RLS) como red de seguridad multi-tenant.
--
-- Cada request setea: SET LOCAL app.estudio_id = '<id>';
-- Las policies garantizan que un usuario solo vea filas de su estudio,
-- incluso si el código omite el WHERE estudio_id = %s.
--
-- superadmin bypasea RLS porque se conecta sin SET app.estudio_id
-- (o se le asigna el rol superuser/bypassrls según la estrategia).
--
-- NOTA: RLS es una red de seguridad adicional, no reemplaza los filtros en código.

-- ══════════════════════════════════════════════════════════════════════════════
-- Helper: función que lee app.estudio_id del setting de sesión
-- Retorna NULL si no está seteado (superadmin o conexiones internas).
-- ══════════════════════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION current_estudio_id() RETURNS INTEGER AS $$
BEGIN
    RETURN NULLIF(current_setting('app.estudio_id', true), '')::INTEGER;
EXCEPTION
    WHEN OTHERS THEN RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ══════════════════════════════════════════════════════════════════════════════
-- RLS en CLIENTES
-- ══════════════════════════════════════════════════════════════════════════════
ALTER TABLE clientes ENABLE ROW LEVEL SECURITY;

-- Bypass para el owner del esquema (migraciones, scripts)
ALTER TABLE clientes FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_clientes ON clientes;
CREATE POLICY tenant_isolation_clientes ON clientes
    USING (
        current_estudio_id() IS NULL            -- superadmin / sin contexto
        OR estudio_id = current_estudio_id()    -- tenant match
    );

-- ══════════════════════════════════════════════════════════════════════════════
-- RLS en ESTUDIOS_AFIP
-- ══════════════════════════════════════════════════════════════════════════════
ALTER TABLE estudios_afip ENABLE ROW LEVEL SECURITY;
ALTER TABLE estudios_afip FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_estudios_afip ON estudios_afip;
CREATE POLICY tenant_isolation_estudios_afip ON estudios_afip
    USING (
        current_estudio_id() IS NULL
        OR estudio_id = current_estudio_id()
    );

-- ══════════════════════════════════════════════════════════════════════════════
-- RLS en CONSULTAS_LOG
-- ══════════════════════════════════════════════════════════════════════════════
ALTER TABLE consultas_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE consultas_log FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_consultas_log ON consultas_log;
CREATE POLICY tenant_isolation_consultas_log ON consultas_log
    USING (
        current_estudio_id() IS NULL
        OR estudio_id = current_estudio_id()
    );
