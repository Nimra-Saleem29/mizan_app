-- ═══════════════════════════════════════════════════════════════════════════════
-- Wakeel وکیل — Supabase / PostgreSQL Schema
-- ───────────────────────────────────────────────────────────────────────────────
-- Run this in: Supabase Dashboard → SQL Editor → New Query
-- Order matters — enums first, then tables, then RLS, then triggers.
-- ═══════════════════════════════════════════════════════════════════════════════


-- ─────────────────────────────────────────────────────────────────────────────
-- 0. EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- uuid_generate_v4()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- fuzzy text search on queries


-- ─────────────────────────────────────────────────────────────────────────────
-- 1. ENUMS
-- ─────────────────────────────────────────────────────────────────────────────
DO $$ BEGIN
  CREATE TYPE language_pref AS ENUM ('urdu', 'english', 'roman_urdu');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  CREATE TYPE input_type AS ENUM ('text', 'voice');
EXCEPTION WHEN duplicate_object THEN NULL; END $$;


-- ─────────────────────────────────────────────────────────────────────────────
-- 2. HELPER: updated_at auto-trigger function
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 1: users
-- Extends Supabase auth.users with app-specific profile data.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.users (
  id                 UUID          PRIMARY KEY
                                   REFERENCES auth.users(id) ON DELETE CASCADE,
  full_name          TEXT          NOT NULL DEFAULT '',
  phone              TEXT,
  preferred_language language_pref NOT NULL DEFAULT 'urdu',
  city               TEXT,                          -- Lahore, Karachi, etc.
  province           TEXT,                          -- Punjab, Sindh, KPK, etc.
  created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  CONSTRAINT users_phone_format CHECK (
    phone IS NULL OR phone ~ '^\+92[0-9]{10}$'     -- Pakistani mobile format
  )
);

-- Auto-update updated_at
CREATE TRIGGER users_set_updated_at
  BEFORE UPDATE ON public.users
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_users_preferred_language
  ON public.users(preferred_language);


-- ── RLS: users ────────────────────────────────────────────────────────────────
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

-- Users can read their own profile
CREATE POLICY "users: select own row"
  ON public.users FOR SELECT
  USING (auth.uid() = id);

-- Users can update their own profile
CREATE POLICY "users: update own row"
  ON public.users FOR UPDATE
  USING (auth.uid() = id)
  WITH CHECK (auth.uid() = id);

-- Insert is handled by the trigger below — no direct insert policy needed
-- but we allow it so the trigger works under SECURITY DEFINER context
CREATE POLICY "users: insert own row"
  ON public.users FOR INSERT
  WITH CHECK (auth.uid() = id);


-- ── Trigger: auto-create user profile on signup ───────────────────────────────
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.users (id, full_name, preferred_language)
  VALUES (
    NEW.id,
    COALESCE(NEW.raw_user_meta_data->>'full_name', ''),
    COALESCE(
      (NEW.raw_user_meta_data->>'preferred_language')::language_pref,
      'urdu'
    )
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

-- Drop before recreate to keep the migration idempotent
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 2: queries
-- Every legal question asked — authenticated or anonymous.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.queries (
  id                  UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id             UUID          REFERENCES public.users(id) ON DELETE SET NULL,
                                    -- nullable → allows anonymous queries

  -- Input
  query_text          TEXT          NOT NULL
                                    CHECK (char_length(query_text) BETWEEN 3 AND 4000),
  query_language      language_pref NOT NULL DEFAULT 'urdu',
  input_type          input_type    NOT NULL DEFAULT 'text',
  audio_url           TEXT,         -- Supabase Storage path if voice input

  -- Output
  response_text       TEXT,
  response_language   language_pref,
  legal_domain        TEXT
                        CHECK (legal_domain IN (
                          'criminal', 'family', 'property', 'labour',
                          'consumer', 'cyber', 'land', 'constitutional',
                          'civil', 'tax', 'corporate', 'general'
                        )),

  -- Structured AI output
  citations           JSONB         DEFAULT '[]'::jsonb,
  -- Expected shape: [{ case_name, court, year, section, url? }]

  -- Metadata
  processing_time_ms  INTEGER       CHECK (processing_time_ms >= 0),
  model_used          TEXT,         -- e.g. 'gemini-1.5-flash'
  tokens_used         INTEGER,
  is_flagged          BOOLEAN       NOT NULL DEFAULT FALSE,  -- moderation flag
  feedback_rating     SMALLINT      CHECK (feedback_rating BETWEEN 1 AND 5),
  created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  CONSTRAINT citations_is_array CHECK (jsonb_typeof(citations) = 'array')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_queries_user_id
  ON public.queries(user_id);

CREATE INDEX IF NOT EXISTS idx_queries_created_at
  ON public.queries(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_queries_user_created
  ON public.queries(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_queries_legal_domain
  ON public.queries(legal_domain);

-- GIN index for full-text search on query text
CREATE INDEX IF NOT EXISTS idx_queries_text_gin
  ON public.queries USING GIN (to_tsvector('simple', query_text));


-- ── RLS: queries ──────────────────────────────────────────────────────────────
ALTER TABLE public.queries ENABLE ROW LEVEL SECURITY;

-- Authenticated users see only their own queries
CREATE POLICY "queries: select own rows"
  ON public.queries FOR SELECT
  USING (
    auth.uid() = user_id
    OR user_id IS NULL  -- anonymous rows: not accessible by other users
  );

-- Anyone (including anon) can insert
CREATE POLICY "queries: insert"
  ON public.queries FOR INSERT
  WITH CHECK (
    user_id IS NULL                -- anonymous query
    OR auth.uid() = user_id        -- authenticated, own row
  );

-- Users can update their own rows (e.g. feedback_rating)
CREATE POLICY "queries: update own rows"
  ON public.queries FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

-- Users can delete their own queries
CREATE POLICY "queries: delete own rows"
  ON public.queries FOR DELETE
  USING (auth.uid() = user_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 3: fir_analyses
-- Stores results of FIR (First Information Report) document scans.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.fir_analyses (
  id                   UUID         PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id              UUID         REFERENCES public.users(id) ON DELETE SET NULL,
  -- nullable → allow anonymous FIR scans

  -- OCR output
  raw_text             TEXT         NOT NULL,  -- extracted text from the FIR image
  document_url         TEXT,        -- Supabase Storage path of the uploaded image

  -- AI analysis
  sections_identified  JSONB        NOT NULL DEFAULT '[]'::jsonb,
  -- Shape: [{ section: "302", act: "PPC", title: "Murder", punishment: "Death or Life",
  --           bailable: false, cognizable: true }]

  plain_explanation    TEXT,        -- human-readable summary in user's language
  explanation_language language_pref,

  flags                JSONB        NOT NULL DEFAULT '[]'::jsonb,
  -- Shape: [{ flag_type: "procedural|rights|timeline", description: "", severity: "high|medium|low" }]

  -- Extracted FIR metadata
  fir_number           TEXT,
  fir_date             DATE,
  police_station       TEXT,
  district             TEXT,
  complainant_name     TEXT,

  -- Severity summary
  has_non_bailable     BOOLEAN      DEFAULT FALSE,
  has_capital_charge   BOOLEAN      DEFAULT FALSE,

  created_at           TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

  CONSTRAINT sections_is_array CHECK (jsonb_typeof(sections_identified) = 'array'),
  CONSTRAINT flags_is_array    CHECK (jsonb_typeof(flags) = 'array')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_fir_analyses_user_id
  ON public.fir_analyses(user_id);

CREATE INDEX IF NOT EXISTS idx_fir_analyses_created_at
  ON public.fir_analyses(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_fir_analyses_non_bailable
  ON public.fir_analyses(has_non_bailable)
  WHERE has_non_bailable = TRUE;


-- ── RLS: fir_analyses ────────────────────────────────────────────────────────
ALTER TABLE public.fir_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "fir_analyses: select own rows"
  ON public.fir_analyses FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "fir_analyses: insert"
  ON public.fir_analyses FOR INSERT
  WITH CHECK (
    user_id IS NULL
    OR auth.uid() = user_id
  );

CREATE POLICY "fir_analyses: delete own rows"
  ON public.fir_analyses FOR DELETE
  USING (auth.uid() = user_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 4: document_analyses
-- Stores analysis of scanned legal documents: contracts, agreements, notices.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.document_analyses (
  id                UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id           UUID          REFERENCES public.users(id) ON DELETE SET NULL,

  document_type     TEXT          NOT NULL
                      CHECK (document_type IN (
                        'rent_agreement', 'employment_contract', 'sale_deed',
                        'mortgage_deed', 'loan_agreement', 'partnership_deed',
                        'nda', 'court_notice', 'legal_notice',
                        'power_of_attorney', 'affidavit', 'bail_application',
                        'other'
                      )),

  document_url      TEXT,                  -- Supabase Storage path
  raw_text          TEXT          NOT NULL, -- OCR output

  -- AI analysis
  risk_flags        JSONB         NOT NULL DEFAULT '[]'::jsonb,
  -- Shape: [{ clause_text, clause_number?, risk_level: "high|medium|low",
  --           explanation, recommendation }]

  favourable_clauses JSONB        NOT NULL DEFAULT '[]'::jsonb,
  -- Shape: [{ clause_text, explanation }]

  plain_explanation TEXT,
  explanation_language language_pref,

  overall_risk_score SMALLINT     CHECK (overall_risk_score BETWEEN 0 AND 100),
  -- 0 = very low risk, 100 = extremely high risk

  parties_identified JSONB        DEFAULT '[]'::jsonb,
  -- Shape: [{ party_type: "landlord|tenant|employer|employee", name }]

  created_at        TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  CONSTRAINT risk_flags_is_array       CHECK (jsonb_typeof(risk_flags) = 'array'),
  CONSTRAINT favourable_is_array       CHECK (jsonb_typeof(favourable_clauses) = 'array')
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_document_analyses_user_id
  ON public.document_analyses(user_id);

CREATE INDEX IF NOT EXISTS idx_document_analyses_created_at
  ON public.document_analyses(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_document_analyses_type
  ON public.document_analyses(document_type);

CREATE INDEX IF NOT EXISTS idx_document_analyses_risk
  ON public.document_analyses(overall_risk_score DESC)
  WHERE overall_risk_score IS NOT NULL;


-- ── RLS: document_analyses ────────────────────────────────────────────────────
ALTER TABLE public.document_analyses ENABLE ROW LEVEL SECURITY;

CREATE POLICY "document_analyses: select own rows"
  ON public.document_analyses FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "document_analyses: insert"
  ON public.document_analyses FOR INSERT
  WITH CHECK (
    user_id IS NULL
    OR auth.uid() = user_id
  );

CREATE POLICY "document_analyses: update own rows"
  ON public.document_analyses FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "document_analyses: delete own rows"
  ON public.document_analyses FOR DELETE
  USING (auth.uid() = user_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- TABLE 5: scenario_sessions
-- Tracks "Know Your Rights" guided flowchart sessions.
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS public.scenario_sessions (
  id              UUID          PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id         UUID          REFERENCES public.users(id) ON DELETE SET NULL,

  scenario_type   TEXT          NOT NULL
                    CHECK (scenario_type IN (
                      -- Criminal / Police
                      'arrested', 'bail_request', 'police_torture',
                      'false_fir', 'under_investigation',
                      -- Civil / Housing
                      'eviction', 'rent_dispute', 'property_dispute',
                      -- Employment
                      'salary_unpaid', 'wrongful_termination', 'harassment_workplace',
                      -- Family
                      'divorce', 'custody', 'inheritance', 'domestic_violence',
                      -- Consumer / Other
                      'consumer_fraud', 'cyber_crime', 'general'
                    )),

  session_language language_pref NOT NULL DEFAULT 'urdu',

  -- The user's traversal through the decision tree
  answers_path    JSONB         NOT NULL DEFAULT '[]'::jsonb,
  -- Shape: [{ step_id, question_text, answer: "yes|no|unsure", timestamp }]

  -- Output
  final_guidance  TEXT,         -- the concluding advice / action steps
  action_steps    JSONB         DEFAULT '[]'::jsonb,
  -- Shape: [{ step_number, action, urgency: "immediate|within_24h|within_week",
  --           relevant_law?, helpline? }]

  emergency_contacts JSONB      DEFAULT '[]'::jsonb,
  -- Helplines surfaced for this scenario (police, legal aid, HRCP, etc.)

  is_completed    BOOLEAN       NOT NULL DEFAULT FALSE,
  completed_at    TIMESTAMPTZ,

  created_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

  CONSTRAINT answers_is_array       CHECK (jsonb_typeof(answers_path) = 'array'),
  CONSTRAINT action_steps_is_array  CHECK (jsonb_typeof(action_steps) = 'array')
);

-- Auto-update updated_at
CREATE TRIGGER scenario_sessions_set_updated_at
  BEFORE UPDATE ON public.scenario_sessions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Indexes
CREATE INDEX IF NOT EXISTS idx_scenario_sessions_user_id
  ON public.scenario_sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_scenario_sessions_created_at
  ON public.scenario_sessions(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_scenario_sessions_type
  ON public.scenario_sessions(scenario_type);

CREATE INDEX IF NOT EXISTS idx_scenario_sessions_completed
  ON public.scenario_sessions(is_completed, user_id)
  WHERE is_completed = FALSE;   -- partial index for in-progress sessions


-- ── RLS: scenario_sessions ────────────────────────────────────────────────────
ALTER TABLE public.scenario_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scenario_sessions: select own rows"
  ON public.scenario_sessions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "scenario_sessions: insert"
  ON public.scenario_sessions FOR INSERT
  WITH CHECK (
    user_id IS NULL
    OR auth.uid() = user_id
  );

CREATE POLICY "scenario_sessions: update own rows"
  ON public.scenario_sessions FOR UPDATE
  USING (auth.uid() = user_id)
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "scenario_sessions: delete own rows"
  ON public.scenario_sessions FOR DELETE
  USING (auth.uid() = user_id);


-- ═══════════════════════════════════════════════════════════════════════════════
-- CONVENIENCE VIEWS
-- (These run with the permissions of the calling user — RLS still applies)
-- ═══════════════════════════════════════════════════════════════════════════════

-- User's recent activity feed
CREATE OR REPLACE VIEW public.user_activity_feed AS
  SELECT
    'query'        AS activity_type,
    id,
    user_id,
    created_at,
    query_text     AS summary,
    legal_domain   AS category
  FROM public.queries
  WHERE user_id IS NOT NULL

  UNION ALL

  SELECT
    'fir_scan'     AS activity_type,
    id,
    user_id,
    created_at,
    COALESCE('FIR #' || fir_number, 'FIR Scan') AS summary,
    'criminal'     AS category
  FROM public.fir_analyses
  WHERE user_id IS NOT NULL

  UNION ALL

  SELECT
    'document'     AS activity_type,
    id,
    user_id,
    created_at,
    document_type  AS summary,
    document_type  AS category
  FROM public.document_analyses
  WHERE user_id IS NOT NULL

  UNION ALL

  SELECT
    'scenario'     AS activity_type,
    id,
    user_id,
    created_at,
    scenario_type  AS summary,
    scenario_type  AS category
  FROM public.scenario_sessions
  WHERE user_id IS NOT NULL;


-- ═══════════════════════════════════════════════════════════════════════════════
-- GRANT: expose public schema to supabase service role (default, but explicit)
-- ═══════════════════════════════════════════════════════════════════════════════
GRANT USAGE ON SCHEMA public TO postgres, anon, authenticated, service_role;

GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, service_role;

GRANT SELECT, INSERT, UPDATE, DELETE
  ON public.users,
     public.queries,
     public.fir_analyses,
     public.document_analyses,
     public.scenario_sessions
  TO authenticated;

-- Anonymous users can insert queries / analyses but not read them back
GRANT INSERT ON public.queries,
               public.fir_analyses,
               public.document_analyses,
               public.scenario_sessions
  TO anon;

GRANT SELECT ON public.user_activity_feed TO authenticated;


-- ═══════════════════════════════════════════════════════════════════════════════
-- COMMENTS — documentation in-database
-- ═══════════════════════════════════════════════════════════════════════════════
COMMENT ON TABLE  public.users                         IS 'App profile extending auth.users — created automatically on signup.';
COMMENT ON TABLE  public.queries                       IS 'Every legal question asked via text or voice — authenticated or anonymous.';
COMMENT ON TABLE  public.fir_analyses                  IS 'OCR + AI analysis of uploaded FIR (First Information Report) documents.';
COMMENT ON TABLE  public.document_analyses             IS 'Risk analysis of scanned legal documents: contracts, deeds, notices, etc.';
COMMENT ON TABLE  public.scenario_sessions             IS '"Know Your Rights" guided flowchart sessions tracking user decisions and outcomes.';

COMMENT ON COLUMN public.queries.citations             IS 'JSON array: [{ case_name, court, year, section, url? }]';
COMMENT ON COLUMN public.fir_analyses.sections_identified IS 'JSON array: [{ section, act, title, punishment, bailable, cognizable }]';
COMMENT ON COLUMN public.fir_analyses.flags            IS 'JSON array: [{ flag_type, description, severity }]';
COMMENT ON COLUMN public.document_analyses.risk_flags  IS 'JSON array: [{ clause_text, clause_number, risk_level, explanation, recommendation }]';
COMMENT ON COLUMN public.scenario_sessions.answers_path IS 'JSON array: [{ step_id, question_text, answer, timestamp }]';
COMMENT ON COLUMN public.scenario_sessions.action_steps IS 'JSON array: [{ step_number, action, urgency, relevant_law, helpline }]';
