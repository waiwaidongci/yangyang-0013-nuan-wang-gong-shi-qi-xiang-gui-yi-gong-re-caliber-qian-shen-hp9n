CREATE TABLE IF NOT EXISTS notice_copies (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    period_id bigint NOT NULL REFERENCES public_notices(period_id),
    recipient text NOT NULL,
    channel text NOT NULL CHECK(channel IN ('wall','desk','intranet')),
    delivery_ref text,
    delivered_by text,
    registered_by text NOT NULL,
    UNIQUE(period_id,recipient,channel),
    CHECK ((delivery_ref IS NULL)=(delivered_by IS NULL))
);
CREATE TABLE IF NOT EXISTS notice_objections (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    copy_id bigint NOT NULL REFERENCES notice_copies(id),
    category text NOT NULL CHECK(category IN ('wording','source','metric')),
    question text NOT NULL,
    filed_by text NOT NULL,
    resolution text CHECK(resolution IN ('clarified','addendum','recheck_next_period')),
    answer text,
    answered_by text
);
CREATE TABLE IF NOT EXISTS notice_addenda (
    objection_id bigint PRIMARY KEY REFERENCES notice_objections(id),
    update_code text NOT NULL UNIQUE,
    replacement_text text NOT NULL,
    issued_at timestamptz NOT NULL DEFAULT now()
);
