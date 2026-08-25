# Phase 0 Research: 30-Day Personalized AI Concierge

All Technical Context fields were fully specified by the user's tech-stack brief; no `NEEDS CLARIFICATION` markers remain. This document records the concrete decisions made to turn that brief into an implementable plan, and the alternatives considered for each.

## 1. Backend package layout & dependency direction

- **Decision**: `src/concierge/*` is a plain importable Python package with zero FastAPI/HTTP imports; `apps/api` depends on `src/concierge/*`, never the reverse. Within `src/concierge`, `domain` has no dependencies on any other `concierge` submodule; `journey`, `events`, `decisioning` depend only on `domain`; `conversation` and `knowledge` depend on `domain` + `providers`; `analytics` depends on `journey`/`events`/`decisioning` read models; `persistence` is depended on (via repository interfaces defined in `journey`/`events`/etc.) rather than depending outward.
- **Rationale**: Keeps the deterministic core (Constitution Principle I) importable and unit-testable with no web server or provider wiring, and keeps `apps/api` a thin composition layer — exactly the "modular monolith" the constitution and this plan require.
- **Alternatives considered**: A single flat `app/` package (rejected — the user explicitly enumerated 8 named modules); a `src/concierge` package that also contains the FastAPI routes (rejected — would blur the deterministic-core/API boundary and make domain logic harder to unit test without an ASGI app).

## 2. Persistence: SQLAlchemy 2.0 + SQLite + repository seam

- **Decision**: SQLAlchemy 2.0 declarative models (`Mapped[...]` typed style) in `src/concierge/persistence`, accessed only through repository classes exposing domain-shaped methods (e.g., `JourneyRepository.get(account_id)`), never raw `Session` objects, outside `persistence`. SQLite file DB by default (`sqlite:///./concierge.db`), created/seeded on startup; connection string is the only thing that changes to target PostgreSQL.
- **Rationale**: Matches the user's "SQLAlchemy 2 / SQLModel-style repository layer" instruction and the constitution's mock-first/local-first principles (zero external DB dependency to run the demo) while explicitly preserving a swap seam.
- **Alternatives considered**: SQLModel directly (rejected — adds a dependency for marginal benefit over SQLAlchemy 2.0's own typed mapped-column style, and the user said "SQLModel-*style*", not SQLModel itself); an in-memory-only store (rejected — a real DB file makes idempotency/audit-log persistence and scenario reset semantics easier to demo and inspect).

## 3. Vector store & embeddings: Chroma with a local embedding function

- **Decision**: Chroma's `PersistentClient` with a local, non-network embedding function (`chromadb.utils.embedding_functions.DefaultEmbeddingFunction`, an ONNX MiniLM model bundled/downloaded once) for the 14-document knowledge base; `EmbeddingProvider` protocol wraps this so a real hosted embedding API could be swapped in later without touching `knowledge/` call sites.
- **Rationale**: Constitution Principle VII (local-first) rules out requiring a live embeddings API key just to run RAG search; Chroma's default embedding function keeps the demo fully offline after first-run model download.
- **Alternatives considered**: OpenAI/Anthropic hosted embeddings as the default (rejected — would make the core demo path depend on an API key); a naive keyword/TF-IDF search instead of a vector store (rejected — user explicitly specified Chroma).

## 4. LLM provider strategy

- **Decision**: `LLMProvider` protocol with two implementations: `StubLLMProvider` (default, deterministic template-based responses — no network, no API key) and one optional real adapter, `AnthropicLLMProvider` (Claude, via the `anthropic` Python SDK), activated only when `ANTHROPIC_API_KEY` is set in the environment. Provider selection happens once at startup via a small factory in `apps/api/main.py`; call sites in `conversation/` are identical either way.
- **Rationale**: The user requires the app to be runnable without an API key (`StubLLMProvider`) and optionally support "one real LLM adapter through environment configuration." Anthropic is chosen as that one real adapter because this project is being built and demoed inside Claude Code / with an Anthropic-first toolchain, keeping setup friction minimal for whoever runs it.
- **Alternatives considered**: OpenAI as the real adapter (rejected — no stated preference from the user; Anthropic is the more natural default given the build environment); wiring multiple real adapters (rejected — the user asked for "one," and multiple adapters add config surface with no MVP benefit).

## 5. Demo/session authentication

- **Decision**: A minimal, explicitly non-production auth: `POST /api/auth/login` accepts a seeded `customer_id` (from `seeds/scenarios/*`) and returns an opaque bearer session token held in-memory (`{token: customer_id}`) for the process lifetime; `apps/api/deps.py` reads `Authorization: Bearer <token>` and resolves it to a customer context, or leaves the request unauthenticated if the header is absent/invalid. No passwords, no persistence, no real IAM.
- **Rationale**: FR-021/FR-023 and User Stories 4/5 require a real authenticated-vs-unauthenticated distinction to be demonstrable and testable, but production identity/IAM is an explicit non-goal. This is the simplest local-first mechanism that makes the privacy boundary genuinely enforceable (not just simulated in the UI).
- **Alternatives considered**: No real auth check, just a UI toggle (rejected — would not let integration tests actually verify FR-021's server-side enforcement); full JWT/OAuth2 (rejected — unnecessary complexity for a hackathon MVP, explicit non-goal).

## 6. Time / journey-day simulation

- **Decision**: Every journey-affecting write path accepts an explicit `occurred_at` on each event (per FR-007); "current journey day" is computed as `(as_of - journey.started_at).days`, where `as_of` defaults to wall-clock `now()` but demo scenarios seed `started_at` in the past (e.g., `now() - 8 days`) so day-3/7/10/21 thresholds are true immediately on load, with no sleep/wait required. No separate "clock service" or time-travel API is introduced.
- **Rationale**: Directly satisfies "Simulate time/journey day explicitly in scenarios so Day 3/7/10/21 behavior can be demonstrated without waiting" with the simplest possible mechanism — backdating seed data — rather than building a mockable clock abstraction the constitution's simplicity principle doesn't require.
- **Alternatives considered**: An injectable `Clock` provider used everywhere (rejected — adds a pervasive dependency for a need fully satisfied by backdating seeded `started_at`/event timestamps); real wall-clock waiting during the demo (rejected — explicitly ruled out by the user).

## 7. Structured logging & correlation IDs

- **Decision**: Standard library `logging` configured for JSON output, plus a FastAPI middleware that reads/generates a `correlation_id` (from an inbound `X-Correlation-Id` header, or a new UUID) and binds it via `contextvars` so every log line in a request emits it; each `Event`'s `correlation_id` field (FR-007) is threaded through to the same context when processing originates from an event. OpenTelemetry is left out of the MVP (optional per the brief) with a single noted extension point in `apps/api/main.py`.
- **Rationale**: Satisfies "structured logging with correlation IDs; OpenTelemetry optional" with no new dependency; keeps auditability (Constitution Principle VI) inspectable straight from stdout during a live demo.
- **Alternatives considered**: `structlog` (rejected — stdlib `logging` + a small JSON formatter is sufficient and avoids one more dependency); wiring OpenTelemetry now (rejected — explicitly optional, no consumer/collector needed for a local demo).

## 8. Frontend theming for future brand styling

- **Decision**: All colors/spacing/typography referenced through CSS custom properties defined once in `apps/web/src/theme/theme-tokens.css` (`--color-*`, `--space-*`, `--font-*`); components only ever reference `var(--token-name)`, never literal hex/px values. A second stylesheet can later override the `:root` token values to apply corporate branding without touching component code.
- **Rationale**: Directly satisfies "generating with stylesheets that's configurable so that we can apply corporate brand styles later on" with the simplest mechanism (native CSS variables), no CSS-in-JS/theming library needed.
- **Alternatives considered**: A JS theming library (e.g., styled-components ThemeProvider) (rejected — adds a dependency and runtime cost for something CSS custom properties already solve); Tailwind with a custom config (rejected — heavier setup than an MVP needs; plain CSS variables are simpler to hand off for a later brand pass).

## 9. Local run & Docker Compose

- **Decision**: Two supported paths, both documented in `README.md`/`quickstart.md`: (a) direct local run — `uvicorn apps.api.main:app --reload` and `npm run dev` in `apps/web`, both against local SQLite/Chroma files; (b) `docker-compose.yml` with an `api` service (FastAPI + SQLite/Chroma volumes) and a `web` service (Vite dev server or a static build served by nginx), for reviewers who prefer not to install Python/Node locally.
- **Rationale**: Matches "Docker Compose optional but recommended; also support direct local run" and Constitution Principle VII (documented, reproducible local setup).
- **Alternatives considered**: Docker-only (rejected — explicit requirement to also support direct local run, and direct run is faster to iterate on during the hackathon itself).

## 10. Postpaid/prepaid activity catalog (closes a spec gap surfaced by `checklists/mvp-guardrails.md` CHK004-006)

- **Decision**: The full REQUIRED/RECOMMENDED/OPTIONAL activity catalog per plan type — sourced verbatim from the original feature brief — is the seed data for `ActivityDefinition` in `data-model.md`, resolving spec.md FR-004/FR-005's reference to "the defined postpaid and prepaid activity lists" with a concrete, implementable table. See `data-model.md §ActivityDefinition` for the enumerated lists.
- **Rationale**: `spec.md` never literally enumerated these lists after its second rewrite, even though the original brief specified them precisely; re-deriving them here (rather than guessing) keeps the plan faithful to already-agreed scope without reopening it.
- **Alternatives considered**: Leaving the catalog implicit/ad hoc in code (rejected — FR-004/FR-005 and Constitution Principle V require the classification to be explicit and explainable); asking the user again (rejected — the data already exists verbatim in the original brief, so re-deriving it is not a material ambiguity).
