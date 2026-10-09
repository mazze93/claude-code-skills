-- core-sample ledger schema. One database can hold many sessions: every table
-- carries session_id, so cross-session analysis is a GROUP BY away.

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY, title TEXT, chat_title TEXT, chat_url TEXT, project TEXT,
  date TEXT, timezone TEXT, as_of TEXT, notes TEXT
);

CREATE TABLE IF NOT EXISTS exchanges (           -- one prompt that started work + the response
  session_id TEXT, exchange TEXT, ordinal INTEGER, at_local TEXT, initiator TEXT,
  prompt TEXT, prompt_provenance TEXT, kind TEXT, response_kind TEXT, response_summary TEXT,
  outputs TEXT, export_turn TEXT,
  PRIMARY KEY (session_id, exchange)
);

CREATE TABLE IF NOT EXISTS events (              -- context injections: compaction, hooks, skill loads
  session_id TEXT, at_utc TEXT, kind TEXT, exchange TEXT, text TEXT
);

CREATE TABLE IF NOT EXISTS tool_calls (
  session_id TEXT, call_id TEXT, exchange TEXT, seq INTEGER, tool TEXT, tool_short TEXT, family TEXT,
  description TEXT, input TEXT,
  started_at TEXT, ended_at TEXT, duration_s REAL,
  outcome TEXT,          -- ok | error | error_unflagged | attested_fail | unrecorded
  outcome_source TEXT,   -- tool-flag | output-scan | <failure link basis> | none
  error_signature TEXT, error_excerpt TEXT,
  record_source TEXT,    -- export | manual | transcript | hook
  tool_use_id TEXT,     -- stable native Claude tool-use ID where available
  evidence_sources TEXT, -- transcript+hook when both independently witnessed
  failure_id TEXT,       -- set when a failure in the ledger points at this call
  PRIMARY KEY (session_id, call_id)
);

CREATE TABLE IF NOT EXISTS failures (
  session_id TEXT, failure_id TEXT, exchange TEXT, call_id TEXT, link_basis TEXT,
  layer TEXT, class TEXT, summary TEXT, detection TEXT, detected_by TEXT, detected_in TEXT,
  exchanges_to_detect INTEGER, caught TEXT, severity INTEGER, status TEXT, evidence TEXT,
  PRIMARY KEY (session_id, failure_id)
);

CREATE TABLE IF NOT EXISTS findings (
  session_id TEXT, finding_id TEXT, "set" TEXT, ref TEXT, subject TEXT, detail TEXT,
  how_found TEXT, resolution TEXT, status TEXT, exchange TEXT,
  PRIMARY KEY (session_id, finding_id)
);

CREATE TABLE IF NOT EXISTS sources (
  session_id TEXT, source_id TEXT, title TEXT, year TEXT, url TEXT, finding TEXT, bearing TEXT, checked TEXT,
  PRIMARY KEY (session_id, source_id)
);

CREATE TABLE IF NOT EXISTS deliverables (
  session_id TEXT, deliverable_id TEXT, name TEXT, version TEXT, type TEXT, destination TEXT,
  exchange TEXT, provenance TEXT,
  PRIMARY KEY (session_id, deliverable_id)
);

CREATE TABLE IF NOT EXISTS open_items (
  session_id TEXT, item_id TEXT, item TEXT, kind TEXT, status TEXT, owner TEXT, next_action TEXT, exchange TEXT,
  PRIMARY KEY (session_id, item_id)
);

-- ── Views for the questions asked most often ─────────────────────────────
CREATE VIEW IF NOT EXISTS v_outcome_coverage AS
  SELECT session_id, record_source, outcome, COUNT(*) AS calls
  FROM tool_calls GROUP BY session_id, record_source, outcome;

CREATE VIEW IF NOT EXISTS v_failures_by_layer_detection AS
  SELECT session_id, layer, detection, caught, COUNT(*) AS failures, SUM(severity) AS severity_points
  FROM failures GROUP BY session_id, layer, detection, caught;

CREATE VIEW IF NOT EXISTS v_tool_reliability AS
  SELECT session_id, tool, family, COUNT(*) AS calls,
         SUM(outcome = 'ok') AS ok,
         SUM(outcome IN ('error', 'error_unflagged', 'attested_fail')) AS failed,
         SUM(outcome = 'error_unflagged') AS failed_unflagged,
         SUM(outcome = 'unrecorded') AS unrecorded
  FROM tool_calls GROUP BY session_id, tool, family;
