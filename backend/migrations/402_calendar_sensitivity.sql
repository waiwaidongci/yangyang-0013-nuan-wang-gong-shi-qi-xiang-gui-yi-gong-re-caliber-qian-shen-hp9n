CREATE TABLE IF NOT EXISTS schedule_marks (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id bigint NOT NULL REFERENCES heating_periods(id),
    day date NOT NULL,
    mode text NOT NULL CHECK(mode IN ('heating','standby')),
    evidence text NOT NULL,
    marked_by text NOT NULL
);
CREATE INDEX IF NOT EXISTS schedule_marks_latest ON schedule_marks(period_id,day,id DESC);
CREATE TABLE IF NOT EXISTS degree_day_scenarios (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    calculation_id bigint NOT NULL REFERENCES heat_calculations(id),
    candidate_base numeric(4,1) NOT NULL CHECK(candidate_base BETWEEN 0 AND 35),
    active_days date[] NOT NULL CHECK(cardinality(active_days)>0),
    calendar_marks bigint[] NOT NULL,
    scope_area integer NOT NULL,
    total_mwh numeric(16,3) NOT NULL,
    weighted_hdd numeric(16,6) NOT NULL,
    normalized numeric(18,6) NOT NULL,
    difference numeric(18,6) NOT NULL,
    reviewed_by text NOT NULL
);
