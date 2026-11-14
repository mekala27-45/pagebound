CREATE SCHEMA IF NOT EXISTS pagebound;
CREATE TABLE IF NOT EXISTS pagebound.sessions (
  capability_hash text PRIMARY KEY CHECK(length(capability_hash)=64),
  expires_at timestamptz NOT NULL,
  attempts integer NOT NULL DEFAULT 0 CHECK(attempts>=0)
);
CREATE TABLE IF NOT EXISTS pagebound.budgets (
  day date PRIMARY KEY,
  attempts integer NOT NULL CHECK(attempts>=0)
);
CREATE TABLE IF NOT EXISTS pagebound.operations (
  operation_id uuid PRIMARY KEY,
  capability_hash text NOT NULL,
  idempotency_key text NOT NULL,
  request_digest text NOT NULL CHECK(length(request_digest)=64),
  bindings_digest text NOT NULL CHECK(length(bindings_digest)=64),
  status text NOT NULL CHECK(status IN ('reserved','running','completed','failed','interrupted')),
  attempts integer NOT NULL DEFAULT 1 CHECK(attempts BETWEEN 1 AND 2),
  lease_until timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE(capability_hash,idempotency_key)
);
CREATE TABLE IF NOT EXISTS pagebound.receipts (
  operation_id uuid PRIMARY KEY REFERENCES pagebound.operations(operation_id),
  request_digest text NOT NULL,
  output_digest text NOT NULL,
  body jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS pagebound.stage_outputs (
  run_id text NOT NULL,
  stage text NOT NULL,
  bindings_digest text NOT NULL,
  output_digest text NOT NULL,
  body jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY(run_id,stage)
);
CREATE TABLE IF NOT EXISTS pagebound.reviews (
  proposal_digest text PRIMARY KEY,
  run_id text NOT NULL,
  bindings_digest text NOT NULL,
  original_digest text NOT NULL,
  assisted_digest text NOT NULL,
  body jsonb NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);
