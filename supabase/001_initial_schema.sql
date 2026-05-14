-- Ramy's Brain - Supabase Schema
-- Run this in Supabase SQL Editor (Dashboard → SQL Editor → New query)

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- ═══════════════════════════════════════════════════════════
-- MEMORIES - Core knowledge store
-- ═══════════════════════════════════════════════════════════
CREATE TABLE memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    content TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    source TEXT NOT NULL DEFAULT 'manual',  -- manual, vscode, email, meeting, jira
    category TEXT NOT NULL DEFAULT 'general',  -- general, decision, observation, meeting, task
    embedding vector(384) NOT NULL,  -- all-MiniLM-L6-v2 output dimension
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for hybrid search
CREATE INDEX idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);
CREATE INDEX idx_memories_tags ON memories USING GIN (tags);
CREATE INDEX idx_memories_fts ON memories USING GIN (to_tsvector('english', content));
CREATE INDEX idx_memories_created ON memories (created_at DESC);
CREATE INDEX idx_memories_source ON memories (source);

-- ═══════════════════════════════════════════════════════════
-- DECISIONS - Architecture and technical decisions
-- ═══════════════════════════════════════════════════════════
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    what TEXT NOT NULL,
    why TEXT NOT NULL,
    context TEXT DEFAULT '',
    revisit_date TEXT,  -- ISO date string, nullable
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decisions_embedding ON decisions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_decisions_created ON decisions (created_at DESC);

-- ═══════════════════════════════════════════════════════════
-- ERROR JOURNAL - Errors and their fixes
-- ═══════════════════════════════════════════════════════════
CREATE TABLE error_journal (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    error TEXT NOT NULL,
    fix TEXT NOT NULL,
    tags TEXT[] DEFAULT '{}',
    embedding vector(384) NOT NULL,
    occurrences INTEGER NOT NULL DEFAULT 1,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_errors_embedding ON error_journal USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_errors_tags ON error_journal USING GIN (tags);

-- ═══════════════════════════════════════════════════════════
-- SNIPPETS - Reusable code patterns
-- ═══════════════════════════════════════════════════════════
CREATE TABLE snippets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    language TEXT NOT NULL DEFAULT 'python',
    description TEXT DEFAULT '',
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_snippets_embedding ON snippets USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
CREATE INDEX idx_snippets_language ON snippets (language);

-- ═══════════════════════════════════════════════════════════
-- PEOPLE - Team members and contacts
-- ═══════════════════════════════════════════════════════════
CREATE TABLE people (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    role TEXT,
    team TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_people_name ON people (LOWER(name));

-- ═══════════════════════════════════════════════════════════
-- PERSON NOTES - Observations about people
-- ═══════════════════════════════════════════════════════════
CREATE TABLE person_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    note TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',  -- general, strength, growth, feedback, context
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_person_notes_person ON person_notes (person_id);
CREATE INDEX idx_person_notes_created ON person_notes (created_at DESC);

-- ═══════════════════════════════════════════════════════════
-- ONE ON ONES - 1:1 meeting logs
-- ═══════════════════════════════════════════════════════════
CREATE TABLE one_on_ones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES people(id) ON DELETE CASCADE,
    notes TEXT NOT NULL,
    action_items TEXT[] DEFAULT '{}',
    embedding vector(384) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_1on1_person ON one_on_ones (person_id);
CREATE INDEX idx_1on1_created ON one_on_ones (created_at DESC);

-- ═══════════════════════════════════════════════════════════
-- DELEGATIONS - Task tracking
-- ═══════════════════════════════════════════════════════════
CREATE TABLE delegations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task TEXT NOT NULL,
    assigned_to TEXT NOT NULL,
    due TEXT,  -- ISO date string
    priority TEXT NOT NULL DEFAULT 'medium',  -- low, medium, high
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, done, overdue, cancelled
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_delegations_assignee ON delegations (LOWER(assigned_to));
CREATE INDEX idx_delegations_status ON delegations (status);
CREATE INDEX idx_delegations_created ON delegations (created_at DESC);
