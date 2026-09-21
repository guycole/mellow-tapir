BEGIN;

CREATE SCHEMA IF NOT EXISTS spectrum;

CREATE TABLE IF NOT EXISTS spectrum.band (
    band_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    lower_hz bigint NOT NULL CHECK (lower_hz >= 0),
    upper_hz bigint NOT NULL CHECK (upper_hz > lower_hz),
    service_name text NOT NULL,
    use_name text NOT NULL,
    channel_spacing_hz integer CHECK (channel_spacing_hz IS NULL OR channel_spacing_hz > 0),
    channel_offset_hz integer,
    priority smallint NOT NULL DEFAULT 50 CHECK (priority BETWEEN 0 AND 100),
    notes text,
    UNIQUE (lower_hz, upper_hz, service_name, use_name)
);

CREATE INDEX IF NOT EXISTS band_frequency_idx
    ON spectrum.band (lower_hz, upper_hz);

CREATE INDEX IF NOT EXISTS band_service_idx
    ON spectrum.band (service_name);

CREATE TABLE IF NOT EXISTS spectrum.band_emission (
    band_id bigint NOT NULL REFERENCES spectrum.band(band_id) ON DELETE CASCADE,
    emission_designator text NOT NULL,
    modulation_label text NOT NULL,
    occupied_bandwidth_hz integer CHECK (occupied_bandwidth_hz IS NULL OR occupied_bandwidth_hz > 0),
    is_typical boolean NOT NULL DEFAULT true,
    notes text,
    PRIMARY KEY (band_id, emission_designator)
);

CREATE TABLE IF NOT EXISTS spectrum.channel (
    channel_id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    center_hz bigint NOT NULL CHECK (center_hz >= 0),
    label text NOT NULL,
    service_name text NOT NULL,
    emission_designator text,
    channel_spacing_hz integer CHECK (channel_spacing_hz IS NULL OR channel_spacing_hz > 0),
    notes text,
    UNIQUE (center_hz, label)
);

CREATE INDEX IF NOT EXISTS channel_frequency_idx
    ON spectrum.channel (center_hz);

CREATE OR REPLACE VIEW spectrum.band_catalog AS
SELECT
    b.band_id,
    b.lower_hz,
    b.upper_hz,
    b.lower_hz / 1000000.0 AS lower_mhz,
    b.upper_hz / 1000000.0 AS upper_mhz,
    b.service_name,
    b.use_name,
    b.channel_spacing_hz,
    b.channel_offset_hz,
    b.priority,
    b.notes,
    COALESCE(
        jsonb_agg(
            jsonb_build_object(
                'designator', e.emission_designator,
                'modulation', e.modulation_label,
                'occupied_bandwidth_hz', e.occupied_bandwidth_hz,
                'typical', e.is_typical,
                'notes', e.notes
            ) ORDER BY e.is_typical DESC, e.emission_designator
        ) FILTER (WHERE e.band_id IS NOT NULL),
        '[]'::jsonb
    ) AS emissions
FROM spectrum.band b
LEFT JOIN spectrum.band_emission e USING (band_id)
GROUP BY b.band_id;

CREATE OR REPLACE FUNCTION spectrum.classify_frequency(query_hz bigint)
RETURNS SETOF spectrum.band_catalog
LANGUAGE sql
STABLE
AS $$
    SELECT *
    FROM spectrum.band_catalog
    WHERE query_hz >= lower_hz AND query_hz < upper_hz
    ORDER BY priority DESC, (upper_hz - lower_hz), service_name, use_name;
$$;

COMMIT;
