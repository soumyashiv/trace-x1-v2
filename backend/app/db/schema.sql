-- TRACE-X database schema (PostgreSQL)
-- Mirrors app/db/models.py. Generated once via Alembic in a real deployment;
-- checked in here for reference and manual bootstrap.

CREATE TABLE IF NOT EXISTS users (
    id              VARCHAR(36) PRIMARY KEY,
    username        VARCHAR(64) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,
    role            VARCHAR(32) NOT NULL DEFAULT 'investigator',
    created_at      TIMESTAMP NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cases (
    id                      VARCHAR(36) PRIMARY KEY,
    title                   VARCHAR(200) NOT NULL,
    investigator_username   VARCHAR(64) NOT NULL REFERENCES users(username),
    suspect_wallet          VARCHAR(128) NOT NULL,
    chain                   VARCHAR(16) NOT NULL DEFAULT 'MOCK',
    status                  VARCHAR(32) NOT NULL DEFAULT 'open',
    notes                   TEXT DEFAULT '',
    created_at              TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_cases_suspect_wallet ON cases(suspect_wallet);

CREATE TABLE IF NOT EXISTS investigation_runs (
    id              VARCHAR(36) PRIMARY KEY,
    case_id         VARCHAR(36) NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    result_json     JSONB NOT NULL,
    risk_score      DOUBLE PRECISION NOT NULL,
    risk_level      VARCHAR(16) NOT NULL,
    generated_at    TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_runs_case_id ON investigation_runs(case_id);

CREATE TABLE IF NOT EXISTS audit_log (
    id              VARCHAR(36) PRIMARY KEY,
    username        VARCHAR(64) NOT NULL,
    action          VARCHAR(64) NOT NULL,
    resource        VARCHAR(200),
    detail          TEXT DEFAULT '',
    ip_address      VARCHAR(64),
    timestamp       TIMESTAMP NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_log(username);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp);
