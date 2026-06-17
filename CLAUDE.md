# AI Chatbot — Project Guide & Implementation Plan v2.1

> This file is the source of truth for **what we're building, why, and in what order.**
> It supersedes the v2.0 plan. It was written after a full audit of the actual code
> in this repo (not just the plan on paper). Where the plan and the code disagreed,
> this document records the *reality* and the *decision*.

---

## 0. Product, in one sentence

An **embeddable AI chat widget** (think Intercom/Crisp, but the brain is *your* AI and the
knowledge is *your* content): a customer drops a `<script>` tag on any website, and their
visitors get an assistant that knows that site's docs, pages, and products. There is also an
**admin dashboard** (Next.js) for managing workspaces, knowledge bases, models, and analytics.

Two surfaces, one backend:
- **Widget** (public, API-key auth) — the actual product, embedded on customer sites.
- **Admin dashboard** (protected, JWT auth) — where *you/customers* configure everything.

---

## 1. Where the project actually is today (audited 2026-06-17)

**Phase 1A is built and green: 18/18 pytest passing.** Run:

```bash
cd backend && source venv/bin/activate && python -m pytest tests/ -v
```

What exists and works:

| Area | Reality |
| --- | --- |
| Backend | FastAPI, `main.py`, routers `health` + `chat`. Runs on **:8001** (see note). |
| AI layer | `ai/providers/base.py` (ABC) + `groq_provider.py` + `ollama_provider.py` + `ai/factory.py` env-driven selector. **The Phase-2 abstraction layer already exists** — it was built early in 1A. |
| Default model | **Groq `llama-3.1-8b-instant`** (cloud). *Not* Ollama/Qwen3 as the v2.0 plan stated. |
| Streaming | SSE via `sse-starlette`. Events: `status` (with `state: active|done`), `token`, `done` (carries `model`), `error`. Last-10-message windowing already done in `api/chat.py`. |
| System prompt | Lives in `api/chat.py`. Clarify-once + coreference directive. Matches the "no custom NLP" decision. |
| Frontend | Next.js 16 + React 19 + Tailwind 4 + framer-motion + react-markdown. `ChatWindow`, `MessageBubble`, `InputBar`, `AIProcessPanel`, `useChat`, `useStream`. |
| Frontend→backend | Next route `app/api/chat/stream/route.ts` **proxies** to `http://localhost:8001/api/chat/stream` and pipes SSE through. |
| Infra | `docker-compose.yml` brings up Postgres 16 + Qdrant. Mounts `./database/migrations` as Postgres init (dir does **not exist yet**). |

### Known drift / latent bugs to fix before they bite (do these in Phase 1B)

1. **Port mismatch.** Plan says `:8000`; frontend proxy calls `:8001`. **Decision: standardize on `:8001`** (frontend already expects it). Add `BACKEND_PORT` to `.env` and a documented run command. Update any `:8000` references.
2. **`ai/factory.py` references `OpenAIProvider` from `ai/providers/openai_provider.py`, which doesn't exist.** Selecting `AI_PROVIDER=openai` crashes with `ImportError`. **Decision:** either implement the provider (Phase 2) or make the factory raise a clean "not yet implemented" error. Don't leave a landmine.
3. **`health.py` only reports `groq_model`/`ollama_model`,** never the openai model. Make it read the active provider's `model_name` instead of branching on strings.
4. **`database/` directory is missing** but compose mounts it. Create it with `migrations/` before first `docker compose up`, or Postgres init silently does nothing.
5. **CORS is a static localhost list** (`config.py`). That's fine for the dashboard, but the widget is cross-origin by definition. CORS must become **per-workspace dynamic** before the widget ships (Phase 7). Flagged now so we design for it.

---

## 2. Strategic analysis — what the v2.0 plan gets right, and what to change

### What's right (keep it)
- **The pivot to an embeddable widget.** That's a real, sellable product with a moat (your content + your brand), unlike a ChatGPT clone.
- **Provider abstraction from day one.** Already paying off — swapping Groq↔Ollama is one env var.
- **Dropping spaCy coreference / custom confidence engines.** Last-10-messages + a one-line system directive is the correct, modern approach. Don't reintroduce NLP plumbing.
- **Test-after-every-phase discipline.** `test_phase_N.py`, green before moving on. Keep this as a hard gate.
- **"You can't improve what you don't measure"** (evaluation). Correct instinct.

### The single biggest change: **pull the widget forward as a "walking skeleton."**

In v2.0 the widget — *the actual product* — doesn't appear until **Month 3 (Phase 7)**. That's
backwards. The riskiest, most product-defining parts of this build are not the chat UI (mostly
done) — they are: **cross-origin embedding, iframe/Shadow-DOM isolation, per-workspace API-key
auth, dynamic CORS, multi-tenant data isolation, and LLM cost/abuse control.** Those are exactly
what gets deferred to Month 3+.

**Decision:** Add a thin **Phase 1.5 — "Embed Spike"** at the end of Month 1. Goal is *not* a
polished widget; it's to prove the end-to-end product path on a throwaway HTML page:

```
test.html on a different origin
  → <script> injects a bubble (Shadow DOM) + panel (iframe)
  → calls backend /api/widget/chat directly (cross-origin), authed by a workspace API key
  → streams a reply back
```

If that works, every later phase is decoration. If it doesn't, we find out in Week 4, not Month 3.
This de-risks the whole product for ~2–3 days of work and forces the multi-tenant + CORS + API-key
design to exist early (where it's cheap) instead of being retrofitted (where it's expensive).

### The second biggest change: **security & cost controls are first-class, not an afterthought.**

An embeddable widget hands a credential to the public internet. The v2.0 plan barely mentions
this. For this product, the following are **requirements, not nice-to-haves**, and are folded into
the roadmap below:

- **Workspace API keys are public + read/chat-scoped only.** Never expose admin scope to the widget. (Schema already separates `api_key` per workspace — good.)
- **Domain allow-list per workspace.** The widget only answers when the request `Origin`/`Referer` is on the workspace's registered domains. This is what stops someone copying your key and running up your LLM bill on their own site.
- **Rate limiting** per workspace, per session, and per IP. SSE endpoints are easy to abuse.
- **Per-workspace usage quota / budget cap.** The real financial risk here is LLM spend, not servers. A runaway loop or a malicious embed can cost real money. Cap it.
- **Prompt-injection hygiene on retrieved content.** Crawled web pages and uploaded docs are untrusted input. Keep retrieved context clearly delimited and instruct the model to treat it as data, not instructions (the RAG system prompt already moves this direction — make it explicit).
- **PII / data-handling note** for anonymous widget sessions stored via `localStorage` session IDs (relevant if customers are in the EU — GDPR).

### Smaller, worth-doing adjustments

- **Groq is the right default; say so.** The plan's tech table lists Qwen3 8B / Ollama as default, but the build chose Groq (fast, cheap, no GPU). Make Groq the **dev + hosted default** and Ollama the **self-host / privacy / air-gapped** option. Both already implemented.
- **Phase 2 is ~70% done.** The abstraction layer exists. Reframe Phase 2 as: add `OpenAIProvider`, `GeminiProvider`, `ClaudeProvider`; move per-workspace model selection into config; fix the factory landmine. Small phase, not a month.
- **Start *logging* eval data when RAG ships (Month 2), build the *dashboard* in Month 4.** Capturing `question / retrieved_chunks / latency / model / thumbs` costs almost nothing if you do it from the first RAG response. The dashboard is the slow part. Don't lose months of data waiting for the UI.
- **Widget isolation: Shadow DOM for the bubble, iframe for the panel.** Shadow DOM keeps the launcher light and style-isolated; the iframe fully sandboxes the chat panel from the host page's CSS/JS. The plan said "iframe-isolated" — this is the more precise, modern split.
- **Thread `workspace_id` through `chats`/`messages` from the very first auth migration** (it already is in the schema — just don't let any code path create a chat without it). Retrofitting tenancy later is the classic SaaS rewrite.
- **Hosted embeddings option.** `bge-small` (local) is fine, but a cloud-first stack benefits from a hosted embedding fallback so you're not forced to run a model server. Keep the embedding interface swappable like the LLM provider.

---

## 3. Decisions on the open questions (resolved — change if you disagree)

| # | Question | Decision | Rationale |
| --- | --- | --- | --- |
| 1 | Postgres: local or hosted? | **Local Docker for dev (already in compose); Neon/Supabase for prod.** Keep `DATABASE_URL` swappable (it is). | Zero-cost dev, painless prod. No code change to switch. |
| 2 | Admin auth method? | **Email/password + JWT now; Google OAuth later (Month 5+).** | Email/pass unblocks 1B immediately; OAuth is additive. |
| 3 | Widget branding? | **Per-workspace (color, logo, greeting, position) from widget v1.** | It's cheap to store in workspace config and it's a core selling point of a white-label widget. |
| 4 | Is `/home/harlin/ai-chatbot` empty? | **No — Phase 1A is built and green. Build on it.** | Audited above. |

---

## 4. Architecture (target)

```
 Customer website (any origin)                    Admin dashboard (Next.js :3000)
   <script ...workspace-id="ws_abc">                 JWT-authed
   ├─ launcher bubble  (Shadow DOM)                  manage workspaces / docs / models / eval
   └─ chat panel       (sandboxed iframe)
              │ cross-origin HTTPS/SSE                        │ (Next proxy OK for dashboard)
              ▼                                                ▼
 ┌─────────────────────────────  FastAPI backend (:8001)  ─────────────────────────────┐
 │  /api/widget/chat   public · API-key · domain-allowlist · rate-limited · quota        │
 │  /api/admin/*       protected · JWT                                                    │
 │  /health                                                                                │
 │                                                                                         │
 │  Chat+Context   AI Providers      RAG Pipeline        Eval logging                     │
 │  (last-N+sum)   (Groq default,    (hybrid retrieve →  (every answer →                  │
 │                  Ollama/OpenAI/    rerank → cite)      question/chunks/latency)         │
 │                  Gemini/Claude)                                                         │
 └───────┬───────────────────┬──────────────────────┬─────────────────────────────────────┘
         ▼                    ▼                      ▼
   PostgreSQL 16         Qdrant (collection      Ollama (optional, self-host LLM
   users/workspaces/     per workspace =         + local embeddings)
   chats/messages/       tenant isolation)
   evaluations
```

**Tenancy rule:** one Qdrant collection per workspace, and every Postgres row that holds content
carries `workspace_id`. A widget request can only ever touch its own workspace's collection. This
is the property the Phase 7 test must prove (workspace A can't read workspace B).

---

## 5. Revised roadmap

```
Month 1  1A ✅ Chat + SSE streaming (no auth)              ← DONE, 18 tests green
         1B    Auth (email/pass + JWT) + history + multi-tenant schema
               + fix drift (port, factory landmine, health, database/ dir)
         1C    Context window (last 10; summarize >30) + system-prompt clarify
         1.5   ★ EMBED SPIKE — prove cross-origin <script> → /api/widget/chat → SSE
               on a throwaway page. Forces API-key auth + dynamic CORS + tenancy early.

Month 2  2     Finish AI abstraction: OpenAI/Gemini/Claude providers, per-workspace model
         3     Doc upload → extract → chunk (512/50) → embed (bge-small) → Qdrant + PG metadata
         4     RAG: embed query → retrieve → inject [CONTEXT] → grounded answer
               + START eval logging now (question/chunks/latency/model) — table only, no UI yet

Month 3  5     Website crawler (httpx+BS4 or crawl4ai), strip nav/footer, depth 2
         6     Citations in SSE `done` event (doc page / url) + citation cards in UI
         7     Workspaces hardened + WIDGET v1 (Shadow DOM bubble + iframe panel,
               per-workspace branding, domain allow-list, rate limit, quota cap)

Month 4  7.5   Hybrid search: vector + keyword (PG FTS or Qdrant sparse) → RRF → top 5
         8     Evaluation DASHBOARD over the data you've been logging since Month 2
               (avg rating, 👍/👎, top-cited chunks, slow queries, "no info" coverage gaps)

Month 5  9     Image understanding (gpt-4o / gemini / llava) via the provider interface
         10    Session/personal memory (extract facts → inject into system prompt)
         +     Google OAuth for admin (additive)

Month 6  11    (Optional) Agent router — ONLY if the eval dashboard shows RAG quality is high
```

**Hard gate:** do not start phase N+1 until `test_phase_N.py` is fully green. Each phase ends with
a manual verification (see §7) *and* a passing test file.

---

## 6. Conventions & rules for working in this repo

- **Use the `code-review-graph` MCP tools before Grep/Glob/Read** when exploring or reviewing — it's faster and gives structural context (callers, tests, impact). Fall back to file tools only when the graph doesn't cover it. (See root `/home/harlin/CLAUDE.md`.)
- **Test command is always the same:** `cd backend && source venv/bin/activate && python -m pytest tests/ -v`.
- **Provider swaps are config, never code.** New model = new `*_provider.py` implementing `AIProvider` + one branch in `ai/factory.py`. The frontend must never learn which model is running.
- **Frontend is Next.js 16 — newer than most training data.** Per `frontend/AGENTS.md`, check `node_modules/next/dist/docs/` before writing Next code; don't assume old conventions.
- **SSE event contract is fixed:** `status` (`{step,label,state}`), `token` (`{token}`), `done` (`{model, sources?}`), `error` (`{message}`). Keep widget and dashboard consumers in sync with it.
- **Every content row carries `workspace_id`.** No chat, message, document, or vector is created without one. Tenancy is not optional.
- **Anything public-facing (the widget endpoint) is authed, origin-checked, rate-limited, and quota-capped.** No exceptions — that endpoint faces the open internet.
- **Don't commit/push unless asked.** When asked, branch off `main` first; end commit messages with the Co-Authored-By trailer.

---

## 7. Verification checklist (per phase)

- **1A ✅** `/health` 200; tokens stream to UI <1s; AIProcessPanel shows Thinking→Generating.
- **1B** Register→JWT in httpOnly cookie; sidebar history survives refresh; delete removes from DB; chat belongs to its user; port/factory/health/database drift fixed.
- **1C** 30-msg chat auto-summarizes oldest 20; "explain it more" resolves prior topic; vague query → one clarifying question.
- **1.5** `test.html` on a different origin loads the bubble, sends a message via API key, streams a reply; request from a non-allow-listed origin is rejected.
- **2** All providers satisfy `AIProvider`; model switch via env/workspace config; `AI_PROVIDER=openai` no longer crashes.
- **3** Upload PDF → chunks visible in Qdrant (`:6333/dashboard`); metadata rows in PG.
- **4** Query about a PDF → grounded answer; eval row written with question/chunks/latency/model.
- **7** Workspace A cannot retrieve workspace B's docs; widget v1 embeds with custom color/greeting; off-domain embed blocked; rate limit + quota enforced.
- **7.5** Same query vector-only vs hybrid → hybrid wins (logged in eval).
- **8** 👍/👎 persists; dashboard shows per-workspace ratings, top chunks, slow queries, coverage gaps over time.

---

*Plan v2.1 — derived from v2.0 + a full audit of the live codebase. Key changes: recorded Groq (not
Ollama) as the real default; flagged 4 concrete drift bugs to fix in 1B; added Phase 1.5 "Embed
Spike" to de-risk the actual product early; promoted security/cost controls (API-key scope, domain
allow-list, rate limit, quota) to first-class requirements; start eval logging in Month 2, dashboard
in Month 4; resolved all four open questions.*
