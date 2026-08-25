# ai-concierge Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-08-24

## Active Technologies

- Python 3.12+ (backend), TypeScript 5.x (frontend, via React 18 + Vite) + FastAPI, Pydantic v2, SQLAlchemy 2.0 (repository-pattern data access), Chroma (local embedded vector store), React + Vite, httpx (test client + optional real-LLM HTTP calls) (001-ai-onboarding-concierge)

## Project Structure

```text
src/
tests/
```

## Commands

cd src && pytest && ruff check .

## Code Style

Python 3.12+ (backend), TypeScript 5.x (frontend, via React 18 + Vite): Follow standard conventions

## Recent Changes

- 001-ai-onboarding-concierge: Added Python 3.12+ (backend), TypeScript 5.x (frontend, via React 18 + Vite) + FastAPI, Pydantic v2, SQLAlchemy 2.0 (repository-pattern data access), Chroma (local embedded vector store), React + Vite, httpx (test client + optional real-LLM HTTP calls)

<!-- MANUAL ADDITIONS START -->
## Actual Project Structure (001-ai-onboarding-concierge)

See `specs/001-ai-onboarding-concierge/plan.md §Project Structure` for the authoritative layout. Summary:

- `src/concierge/{domain,journey,events,decisioning,conversation,knowledge,providers,analytics,persistence}` — deterministic core + providers, no FastAPI imports
- `apps/api` — FastAPI app, routers, DI wiring, auth
- `apps/web` — React + Vite frontend, CSS-variable theme tokens in `src/theme/`
- `seeds/scenarios/` — 11 curated demo scenarios (JSON/YAML)
- `knowledge_base/*.md` — 14 curated wireless knowledge docs (RAG source)
- `tests/{unit,integration,e2e}` — see `plan.md §Test Strategy` for ordering (unit/integration before UI polish, per Constitution Principle VIII)
- `docs/` — Mermaid architecture + sequence diagrams

Constitution non-negotiable to never violate while implementing: the LLM (`src/concierge/conversation`) only ever reads a finalized `ConciergeContext` DTO and a whitelisted action list — it must never write to persistence, compute health/billing, or decide NBA/escalation. See `.specify/memory/constitution.md` Principle I.
<!-- MANUAL ADDITIONS END -->
