"""initial schema

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-05-30

The schema from spec §11. Written as explicit SQL statements (not autogenerate)
so it matches the engineering spec exactly, including PostGIS/pgvector setup,
the append-only event store, and the geo index.
"""
from __future__ import annotations

from alembic import op

revision = "001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


_UPGRADE_STATEMENTS = [
    'CREATE EXTENSION IF NOT EXISTS "uuid-ossp"',
    "CREATE EXTENSION IF NOT EXISTS postgis",
    "CREATE EXTENSION IF NOT EXISTS vector",
    # ── Users (minimal — Clerk handles auth) ────────────────────────────────
    """
    CREATE TABLE users (
        id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        clerk_user_id   TEXT UNIQUE NOT NULL,
        email           TEXT UNIQUE NOT NULL,
        full_name       TEXT,
        created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # ── Rental Searches ──────────────────────────────────────────────────────
    """
    CREATE TABLE rental_searches (
        id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id                 UUID NOT NULL REFERENCES users(id),
        requirements            JSONB NOT NULL,
        status                  TEXT NOT NULL DEFAULT 'pending',
        temporal_workflow_id    TEXT,
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        completed_at            TIMESTAMPTZ,
        failure_reason          TEXT
    )
    """,
    "CREATE INDEX idx_rental_searches_user_id ON rental_searches(user_id)",
    "CREATE INDEX idx_rental_searches_status  ON rental_searches(status)",
    # ── Landlords ──────────────────────────────────────────────────────────
    """
    CREATE TABLE landlords (
        id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        name                        TEXT,
        email                       TEXT,
        phone                       TEXT,
        social_handle               TEXT,
        total_contacts              INT NOT NULL DEFAULT 0,
        total_responses             INT NOT NULL DEFAULT 0,
        total_ghosts                INT NOT NULL DEFAULT 0,
        avg_response_hours          FLOAT,
        preferred_contact_channel   TEXT,
        behavior_embedding          vector(1536),
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    # ── Listings ─────────────────────────────────────────────────────────────
    """
    CREATE TABLE listings (
        id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rental_search_id        UUID NOT NULL REFERENCES rental_searches(id),
        landlord_id             UUID REFERENCES landlords(id),
        source                  TEXT NOT NULL,
        source_listing_id       TEXT NOT NULL,
        source_url              TEXT NOT NULL,
        street                  TEXT NOT NULL,
        unit                    TEXT,
        city                    TEXT NOT NULL,
        state                   CHAR(2) NOT NULL,
        zip_code                TEXT NOT NULL,
        location                GEOGRAPHY(POINT, 4326),
        monthly_rent_cents      INT NOT NULL,
        bedrooms                SMALLINT,
        bathrooms               FLOAT,
        square_feet             INT,
        available_date          DATE,
        lease_duration_months   SMALLINT,
        pets_allowed            BOOLEAN,
        parking_included        BOOLEAN,
        utilities_included      BOOLEAN,
        furnished               BOOLEAN,
        description             TEXT,
        photos                  TEXT[],
        status                  TEXT NOT NULL DEFAULT 'active',
        is_duplicate            BOOLEAN NOT NULL DEFAULT FALSE,
        dedup_canonical_id      UUID REFERENCES listings(id),
        created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (source, source_listing_id)
    )
    """,
    "CREATE INDEX idx_listings_location ON listings USING GIST (location)",
    "CREATE INDEX idx_listings_search_id ON listings(rental_search_id)",
    "CREATE INDEX idx_listings_status ON listings(status)",
    # ── Outreach Attempts ────────────────────────────────────────────────────
    """
    CREATE TABLE outreach_attempts (
        id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rental_search_id        UUID NOT NULL REFERENCES rental_searches(id),
        listing_id              UUID NOT NULL REFERENCES listings(id),
        landlord_id             UUID NOT NULL REFERENCES landlords(id),
        channel                 TEXT NOT NULL,
        direction               TEXT NOT NULL DEFAULT 'outbound',
        message_body            TEXT NOT NULL,
        subject                 TEXT,
        sendgrid_message_id     TEXT,
        twilio_sid              TEXT,
        bland_call_id           TEXT,
        response_body           TEXT,
        responded_at            TIMESTAMPTZ,
        response_sentiment      TEXT,
        attempt_number          SMALLINT NOT NULL DEFAULT 1,
        sent_at                 TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX idx_outreach_search_id ON outreach_attempts(rental_search_id)",
    "CREATE INDEX idx_outreach_listing_id ON outreach_attempts(listing_id)",
    # ── Event Store (immutable — never UPDATE, only INSERT) ──────────────────
    """
    CREATE TABLE domain_events (
        event_id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rental_search_id    UUID NOT NULL REFERENCES rental_searches(id),
        event_type          TEXT NOT NULL,
        sequence            BIGINT NOT NULL,
        payload             JSONB NOT NULL,
        occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE (rental_search_id, sequence)
    )
    """,
    "CREATE INDEX idx_events_search_id ON domain_events(rental_search_id)",
    "CREATE INDEX idx_events_type ON domain_events(event_type)",
    # ── Leases ───────────────────────────────────────────────────────────────
    """
    CREATE TABLE leases (
        id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        rental_search_id            UUID NOT NULL REFERENCES rental_searches(id),
        listing_id                  UUID NOT NULL REFERENCES listings(id),
        landlord_id                 UUID NOT NULL REFERENCES landlords(id),
        user_id                     UUID NOT NULL REFERENCES users(id),
        monthly_rent_cents          INT NOT NULL,
        move_in_date                DATE NOT NULL,
        lease_duration_months       SMALLINT NOT NULL,
        address_snapshot            JSONB NOT NULL,
        lease_document_s3_key       TEXT,
        signed_document_s3_key      TEXT,
        docusign_envelope_id        TEXT,
        signed_at                   TIMESTAMPTZ,
        created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
]

_DOWNGRADE_STATEMENTS = [
    "DROP TABLE IF EXISTS leases",
    "DROP TABLE IF EXISTS domain_events",
    "DROP TABLE IF EXISTS outreach_attempts",
    "DROP TABLE IF EXISTS listings",
    "DROP TABLE IF EXISTS landlords",
    "DROP TABLE IF EXISTS rental_searches",
    "DROP TABLE IF EXISTS users",
]


def upgrade() -> None:
    for statement in _UPGRADE_STATEMENTS:
        op.execute(statement)


def downgrade() -> None:
    for statement in _DOWNGRADE_STATEMENTS:
        op.execute(statement)
