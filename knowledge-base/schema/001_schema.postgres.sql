-- Elderly Scam Shield knowledge base — Supabase / PostgreSQL target.
-- Generated companion to 001_schema.sqlite.sql. Same tables, same
-- constraints, Postgres types.
--
-- vector(1536) is a PLACEHOLDER dimension. Set it to the chosen embedding
-- model's dimension, and set EMBEDDING_DIM in kb/db.py to match.
-- See HANDOFF-allen.md.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE sources (
    source_id    TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    organisation TEXT NOT NULL,
    url          TEXT NOT NULL,
    retrieved_at DATE,
    licence      TEXT NOT NULL,
    attribution  TEXT NOT NULL,
    notes        TEXT
);

CREATE TABLE brand_rebuttals (
    brand_id           TEXT PRIMARY KEY,
    brand_name         TEXT NOT NULL,
    rebuttal_quote     TEXT NOT NULL,
    official_hotline   TEXT NOT NULL,
    official_url       TEXT NOT NULL,
    official_channels  TEXT,
    measured_frequency INTEGER NOT NULL,
    source_id          TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE lure_patterns (
    pattern_id     TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    description    TEXT NOT NULL,
    scam_type      TEXT NOT NULL,
    measured_share REAL NOT NULL,
    measured_count INTEGER NOT NULL,
    red_flags      TEXT NOT NULL,
    triggers_en    TEXT NOT NULL,
    triggers_tl    TEXT NOT NULL,
    source_id      TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE reporting_contacts (
    contact_id   TEXT PRIMARY KEY,
    organisation TEXT NOT NULL,
    hotline      TEXT,
    email        TEXT,
    url          TEXT NOT NULL,
    covers       TEXT NOT NULL,
    priority     INTEGER NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE advisories (
    advisory_id  TEXT PRIMARY KEY,
    title        TEXT NOT NULL,
    body         TEXT NOT NULL,
    published_at DATE,
    language     TEXT NOT NULL,
    source_id    TEXT NOT NULL REFERENCES sources(source_id)
);

CREATE TABLE message_examples (
    message_id      TEXT PRIMARY KEY,
    text            TEXT NOT NULL,
    text_norm       TEXT NOT NULL,
    label           TEXT NOT NULL CHECK (label IN ('SCAM', 'LEGIT')),
    source_category TEXT NOT NULL,
    scam_type       TEXT,
    brand_tag       TEXT,
    has_url         BOOLEAN NOT NULL DEFAULT FALSE,
    taglish_markers INTEGER NOT NULL DEFAULT 0,
    retrievable     BOOLEAN NOT NULL DEFAULT FALSE,
    eval_holdout    BOOLEAN NOT NULL DEFAULT FALSE,
    date_received   TIMESTAMP,
    source_id       TEXT NOT NULL REFERENCES sources(source_id),
    CHECK (label <> 'LEGIT' OR retrievable = FALSE),
    CHECK (eval_holdout = FALSE OR retrievable = FALSE)
);

CREATE TABLE kb_chunks (
    chunk_id    TEXT PRIMARY KEY,
    text        TEXT NOT NULL,
    parent_type TEXT NOT NULL,
    parent_id   TEXT NOT NULL,
    source_id   TEXT NOT NULL REFERENCES sources(source_id),
    keywords_en TEXT,
    keywords_tl TEXT,
    embedding   vector(1536)
);

CREATE INDEX idx_messages_label ON message_examples(label);
CREATE INDEX idx_messages_retrievable ON message_examples(retrievable);
CREATE INDEX idx_messages_scam_type ON message_examples(scam_type);
CREATE INDEX idx_messages_norm ON message_examples(text_norm);
CREATE INDEX idx_chunks_parent ON kb_chunks(parent_type, parent_id);
CREATE INDEX idx_chunks_source ON kb_chunks(source_id);
