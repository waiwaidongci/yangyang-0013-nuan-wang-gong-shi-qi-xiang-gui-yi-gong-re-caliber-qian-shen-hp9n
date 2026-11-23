CREATE TABLE IF NOT EXISTS zone_meters (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    zone_id bigint UNIQUE NOT NULL REFERENCES heated_zones(id),
    serial text NOT NULL,
    dial_limit numeric(12,3) NOT NULL CHECK(dial_limit>0),
    multiplier numeric(9,3) NOT NULL CHECK(multiplier>0),
    UNIQUE(zone_id,serial)
);
CREATE TABLE IF NOT EXISTS meter_journal (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    meter_id bigint NOT NULL REFERENCES zone_meters(id),
    input_id bigint NOT NULL UNIQUE REFERENCES daily_inputs(id),
    day date NOT NULL,
    before_reading numeric(12,3) NOT NULL CHECK(before_reading>=0),
    after_reading numeric(12,3) NOT NULL CHECK(after_reading>=0),
    rollover boolean NOT NULL,
    previous_journal_id bigint REFERENCES meter_journal(id)
);
