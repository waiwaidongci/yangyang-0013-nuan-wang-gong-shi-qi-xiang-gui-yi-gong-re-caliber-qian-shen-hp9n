CREATE TABLE IF NOT EXISTS heating_periods (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code text NOT NULL UNIQUE,
    starts_on date NOT NULL,
    ends_on date NOT NULL,
    CHECK (ends_on-starts_on BETWEEN 0 AND 30)
);

CREATE TABLE IF NOT EXISTS heated_zones (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id bigint NOT NULL REFERENCES heating_periods(id),
    zone_code text NOT NULL,
    zone_name text NOT NULL,
    area_m2 integer NOT NULL CHECK (area_m2 BETWEEN 100 AND 1000000),
    UNIQUE (period_id,zone_code)
);

CREATE TABLE IF NOT EXISTS daily_inputs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    zone_id bigint NOT NULL REFERENCES heated_zones(id),
    day date NOT NULL,
    channel text NOT NULL CHECK (channel IN ('weather','heat')),
    amount numeric(12,3) NOT NULL,
    source_ref text NOT NULL,
    revision integer NOT NULL CHECK (revision > 0),
    entered_by text NOT NULL,
    UNIQUE(zone_id,day,channel,revision),
    CHECK ((channel='weather' AND amount BETWEEN -60 AND 55)
        OR (channel='heat' AND amount BETWEEN 0 AND 25000))
);

CREATE TABLE IF NOT EXISTS normalization_specs (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id bigint NOT NULL REFERENCES heating_periods(id),
    spec_code text NOT NULL,
    base_celsius numeric(4,1) NOT NULL CHECK (base_celsius BETWEEN 0 AND 35),
    description text NOT NULL,
    UNIQUE (period_id,spec_code)
);

CREATE TABLE IF NOT EXISTS heat_calculations (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    spec_id bigint NOT NULL REFERENCES normalization_specs(id),
    zone_ids bigint[] NOT NULL,
    entry_ids bigint[] NOT NULL,
    phase text NOT NULL CHECK (phase IN ('queued','ready')) DEFAULT 'queued',
    total_mwh numeric(16,3),
    scope_area integer,
    area_hdd numeric(18,3),
    period_hdd numeric(16,6),
    raw_kwh_m2 numeric(18,6),
    normalized numeric(18,6),
    stamped_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS zone_calculations (
    calculation_id bigint NOT NULL REFERENCES heat_calculations(id),
    zone_id bigint NOT NULL REFERENCES heated_zones(id),
    total_mwh numeric(16,3) NOT NULL,
    hdd numeric(10,3) NOT NULL CHECK (hdd > 0),
    normalized numeric(18,6) NOT NULL,
    PRIMARY KEY (calculation_id,zone_id)
);

CREATE TABLE IF NOT EXISTS public_notices (
    period_id bigint PRIMARY KEY REFERENCES heating_periods(id),
    calculation_id bigint NOT NULL UNIQUE REFERENCES heat_calculations(id),
    notice_code text NOT NULL UNIQUE,
    note text NOT NULL,
    signed_by text NOT NULL,
    signed_at timestamptz NOT NULL DEFAULT now()
);
