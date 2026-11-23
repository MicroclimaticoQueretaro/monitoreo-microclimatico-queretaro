-- =====================================================================
-- Fase 4: datos del modelo meteorológico en tiempo real (Open-Meteo)
-- =====================================================================
-- Este script es IDEMPOTENTE: se puede ejecutar varias veces sin error y
-- sin borrar datos. Funciona de dos maneras:
--   * Base nueva: Docker lo ejecuta solo, después de 01_esquema.sql.
--   * Base existente (con lecturas reales): se aplica a mano, SIN borrar nada:
--       docker exec -i microclima_db psql -U microclima_admin -d microclima_db < db/init/02_modelo.sql
--
-- A esto se le llama "migración": cambiar el esquema de una base que ya
-- tiene datos sin perderlos.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Valores horarios del modelo para cada estación
-- ---------------------------------------------------------------------
-- Open-Meteo ajusta (escala) el modelo a la altitud de la estación, por lo
-- que la comparación sensor vs. modelo no tiene sesgo por diferencia de altura.
CREATE TABLE IF NOT EXISTS modelo_horario (
    estacion_id         SMALLINT    NOT NULL REFERENCES estaciones (id),
    hora                TIMESTAMPTZ NOT NULL,          -- inicio de la hora (UTC)
    temperatura         NUMERIC(4, 1) CHECK (temperatura BETWEEN -30 AND 60),
    humedad             NUMERIC(4, 1) CHECK (humedad BETWEEN 0 AND 100),
    presion_nivel_mar   NUMERIC(6, 1) CHECK (presion_nivel_mar BETWEEN 900 AND 1100),
    presion_superficie  NUMERIC(6, 1) CHECK (presion_superficie BETWEEN 600 AND 1100),
    radiacion_wm2       NUMERIC(6, 1) CHECK (radiacion_wm2 BETWEEN 0 AND 1500),
    actualizado_en      TIMESTAMPTZ NOT NULL DEFAULT now(),  -- última descarga
    PRIMARY KEY (estacion_id, hora)
);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('modelo_horario', 'hora', if_not_exists => TRUE);
    END IF;
END
$$;


-- ---------------------------------------------------------------------
-- 2. Índice para consultar rápido las lecturas de una estación por fecha
--    (lo usa el cálculo de la brecha térmica por hora)
-- ---------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_lecturas_estacion_ts ON lecturas (estacion_id, ts DESC);
