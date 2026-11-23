-- =====================================================================
-- Esquema de la base de datos del Monitoreo Microclimático de Querétaro
-- =====================================================================
-- Este script se ejecuta AUTOMÁTICAMENTE la primera vez que se crea el
-- contenedor de PostgreSQL (carpeta /docker-entrypoint-initdb.d).
-- Si la base ya existía, NO se vuelve a ejecutar: para aplicarlo de nuevo
-- hay que borrar el volumen con:  docker compose down -v
--
-- Convenciones:
--   * Todas las fechas se guardan como TIMESTAMPTZ (con zona horaria) y
--     PostgreSQL las almacena internamente en UTC.
--   * Unidades: temperatura en °C, humedad en %, presión en hPa,
--     radiación en W/m², iluminancia en lux.
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Estaciones de medición (hoy una sola, pero el diseño permite crecer)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS estaciones (
    id              SMALLSERIAL PRIMARY KEY,
    codigo          VARCHAR(30)  NOT NULL UNIQUE,      -- identificador corto, ej. 'QRO-CENTRO-01'
    nombre          VARCHAR(100) NOT NULL,
    latitud         NUMERIC(8, 5) NOT NULL CHECK (latitud BETWEEN -90 AND 90),
    longitud        NUMERIC(8, 5) NOT NULL CHECK (longitud BETWEEN -180 AND 180),
    altitud_m       NUMERIC(6, 1),
    -- Hash del token de autenticación del ESP32 (nunca se guarda el token en texto plano)
    token_hash      VARCHAR(128),
    activa          BOOLEAN NOT NULL DEFAULT TRUE,
    creada_en       TIMESTAMPTZ NOT NULL DEFAULT now()
);


-- ---------------------------------------------------------------------
-- 2. Lecturas en tiempo real enviadas por el ESP32
-- ---------------------------------------------------------------------
-- Los CHECK rechazan valores físicamente imposibles: es la última línea
-- de defensa contra sensores dañados o datos falsos.
CREATE TABLE IF NOT EXISTS lecturas (
    estacion_id         SMALLINT    NOT NULL REFERENCES estaciones (id),
    ts                  TIMESTAMPTZ NOT NULL,              -- momento de la medición
    temperatura_dht     NUMERIC(4, 1) CHECK (temperatura_dht BETWEEN -10 AND 60),
    temperatura_bmp     NUMERIC(4, 1) CHECK (temperatura_bmp BETWEEN -10 AND 60),
    humedad             NUMERIC(4, 1) CHECK (humedad BETWEEN 0 AND 100),
    presion_hpa         NUMERIC(6, 1) CHECK (presion_hpa BETWEEN 700 AND 1100),
    iluminancia_lux     NUMERIC(8, 1) CHECK (iluminancia_lux BETWEEN 0 AND 200000),
    recibida_en         TIMESTAMPTZ NOT NULL DEFAULT now(), -- momento en que llegó a la API
    -- Una estación no puede tener dos lecturas en el mismo instante
    PRIMARY KEY (estacion_id, ts)
);


-- ---------------------------------------------------------------------
-- 3. Histórico horario del reanálisis ERA5-Land (2023-2025)
-- ---------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS historico_era5 (
    ts              TIMESTAMPTZ PRIMARY KEY,
    latitud         NUMERIC(8, 5) NOT NULL,
    longitud        NUMERIC(8, 5) NOT NULL,
    temperatura     NUMERIC(4, 1) CHECK (temperatura BETWEEN -10 AND 60),
    humedad         NUMERIC(4, 1) CHECK (humedad BETWEEN 0 AND 100),
    presion_hpa     NUMERIC(6, 1) CHECK (presion_hpa BETWEEN 700 AND 1100),
    radiacion_wm2   NUMERIC(6, 1) CHECK (radiacion_wm2 BETWEEN 0 AND 1500)
);


-- ---------------------------------------------------------------------
-- 4. TimescaleDB (opcional): convierte las tablas de series de tiempo en
--    "hypertables", que particionan los datos por fecha y aceleran las
--    consultas por rango. Si la extensión no está instalada, el esquema
--    funciona igual con PostgreSQL normal.
-- ---------------------------------------------------------------------
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'timescaledb') THEN
        CREATE EXTENSION IF NOT EXISTS timescaledb;
        PERFORM create_hypertable('lecturas', 'ts', if_not_exists => TRUE);
        PERFORM create_hypertable('historico_era5', 'ts', if_not_exists => TRUE);
        RAISE NOTICE 'TimescaleDB activado: hypertables creadas.';
    ELSE
        RAISE NOTICE 'TimescaleDB no disponible: se usan tablas normales de PostgreSQL.';
    END IF;
END
$$;


-- ---------------------------------------------------------------------
-- 5. Climatología: comportamiento "normal" de cada mes y hora del día,
--    calculado a partir de los 3 años del histórico.
--    Es la referencia contra la que se compara cada lectura del sensor.
-- ---------------------------------------------------------------------
-- Es una vista materializada: guarda el resultado como una tabla y se
-- actualiza con:  REFRESH MATERIALIZED VIEW climatologia;
CREATE MATERIALIZED VIEW IF NOT EXISTS climatologia AS
SELECT
    EXTRACT(MONTH FROM ts AT TIME ZONE 'America/Mexico_City')::SMALLINT AS mes,
    EXTRACT(HOUR  FROM ts AT TIME ZONE 'America/Mexico_City')::SMALLINT AS hora,
    COUNT(*)                                                       AS n_registros,
    ROUND(AVG(temperatura), 2)                                     AS temperatura_media,
    ROUND(STDDEV_SAMP(temperatura), 2)                             AS temperatura_desv,
    ROUND(PERCENTILE_CONT(0.10) WITHIN GROUP (ORDER BY temperatura)::NUMERIC, 2) AS temperatura_p10,
    ROUND(PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY temperatura)::NUMERIC, 2) AS temperatura_p90,
    ROUND(AVG(humedad), 1)                                         AS humedad_media,
    ROUND(STDDEV_SAMP(humedad), 1)                                 AS humedad_desv,
    ROUND(AVG(presion_hpa), 1)                                     AS presion_media_hpa,
    ROUND(AVG(radiacion_wm2), 1)                                   AS radiacion_media_wm2
FROM historico_era5
GROUP BY 1, 2;   -- vacía al inicio; se actualiza al cargar el histórico (data_science/cargar_bd.py)

-- Índice único: necesario para REFRESH ... CONCURRENTLY y para búsquedas rápidas por (mes, hora)
CREATE UNIQUE INDEX IF NOT EXISTS idx_climatologia_mes_hora ON climatologia (mes, hora);


-- ---------------------------------------------------------------------
-- 6. Estación inicial
-- ---------------------------------------------------------------------
-- TODO: reemplazar las coordenadas por la ubicación real de instalación del ESP32.
INSERT INTO estaciones (codigo, nombre, latitud, longitud, altitud_m)
VALUES ('QRO-CENTRO-01', 'Centro Histórico de Querétaro', 20.59065, -100.39132, 1824.9)
ON CONFLICT (codigo) DO NOTHING;
