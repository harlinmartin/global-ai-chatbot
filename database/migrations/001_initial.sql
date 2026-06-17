-- 001_initial.sql
-- Core multi-tenant schema for Phase 1B (auth + history).
-- Runs automatically on first Postgres init via docker-compose
-- (mounted at /docker-entrypoint-initdb.d). PG16 has gen_random_uuid() built in.
--
-- Tenancy rule: every content row carries workspace_id. No chat or message
-- is ever created without one.

CREATE TABLE IF NOT EXISTS users (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email       TEXT UNIQUE NOT NULL,
  password    TEXT NOT NULL,              -- bcrypt/argon2 hash, never plaintext
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workspaces (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  api_key     TEXT UNIQUE NOT NULL DEFAULT gen_random_uuid()::TEXT,  -- public widget key (read/chat scope)
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chats (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
  user_id      UUID REFERENCES users(id) ON DELETE SET NULL,  -- NULL for anonymous widget sessions
  session_id   TEXT,                                          -- anonymous widget session identifier
  title        TEXT NOT NULL DEFAULT 'New Chat',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chat_id      UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
  role         TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
  content      TEXT NOT NULL,
  metadata     JSONB NOT NULL DEFAULT '{}',
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes for the common access paths
CREATE INDEX IF NOT EXISTS idx_workspaces_owner   ON workspaces(owner_id);
CREATE INDEX IF NOT EXISTS idx_workspaces_api_key ON workspaces(api_key);
CREATE INDEX IF NOT EXISTS idx_chats_workspace    ON chats(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chats_user         ON chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_session      ON chats(session_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat      ON messages(chat_id);
