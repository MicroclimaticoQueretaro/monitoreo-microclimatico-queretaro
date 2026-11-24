-- =====================================================================
-- Administración: cuentas de administrador, sesiones y registro de comandos
-- =====================================================================
-- Script IDEMPOTENTE (se puede ejecutar varias veces sin borrar datos).
--   * Base nueva: Docker lo ejecuta solo, después de 01 y 02.
--   * Base existente (local o Neon): se aplica a mano, ver docs/despliegue.md
-- =====================================================================

-- Cuentas de administrador. La contraseña NUNCA se guarda: solo su hash (scrypt con sal).
CREATE TABLE IF NOT EXISTS administradores (
    id               SMALLSERIAL PRIMARY KEY,
    usuario          VARCHAR(40) NOT NULL UNIQUE CHECK (usuario ~ '^[a-z0-9_.-]{3,40}$'),
    hash_contrasena  TEXT        NOT NULL,
    activo           BOOLEAN     NOT NULL DEFAULT TRUE,
    creado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Sesiones abiertas desde el sitio web. Solo se guarda el hash del token, y caducan.
CREATE TABLE IF NOT EXISTS sesiones_admin (
    token_hash        CHAR(64)    PRIMARY KEY,
    administrador_id  SMALLINT    NOT NULL REFERENCES administradores (id) ON DELETE CASCADE,
    creada_en         TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_en         TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sesiones_expiracion ON sesiones_admin (expira_en);

-- Auditoría: quién activó o detuvo la estación y cuándo
CREATE TABLE IF NOT EXISTS comandos (
    id                BIGSERIAL   PRIMARY KEY,
    estacion_id       SMALLINT    NOT NULL REFERENCES estaciones (id),
    administrador_id  SMALLINT    REFERENCES administradores (id) ON DELETE SET NULL,
    accion            VARCHAR(10) NOT NULL CHECK (accion IN ('activar', 'detener')),
    enviado_en        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_comandos_estacion ON comandos (estacion_id, enviado_en DESC);
