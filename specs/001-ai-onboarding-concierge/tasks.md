---

description: "Task list for 30-Day Personalized AI Concierge"
---

# Tasks: 30-Day Personalized AI Concierge

**Input**: Design documents from `/specs/001-ai-onboarding-concierge/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included throughout — the spec and constitution (Principle VIII) explicitly require deterministic business-rule and end-to-end validation before polish.

**Organization**: Phased per the user's explicit 12-phase build order (technical/dependency order, not a strict one-phase-per-user-story split). Phases 1-3 are Setup/Foundational (no story label — every user story depends on them). From Phase 4 onward, each task carries a `[US#]` label identifying which spec.md user story it primarily serves; a task serving more than one story lists all applicable labels. Phase 12 is cross-cutting polish.

User stories referenced: **US1** Guided Activation to Onboarding Completion (P1) · **US2** Friction Detection, Proactive Resolution, and Contextual Escalation (P2) · **US3** Digital Adoption Nudges and Billing/Renewal Readiness (P3) · **US4** Authenticated Contextual Troubleshooting (P4) · **US5** Unauthenticated Generic Concierge Help (P5) · **US6** Demo Control and Aggregate Outcome Dashboard (P6)

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task primarily serves (omitted for Setup/Foundational/cross-cutting tasks)
- Every task names concrete file(s)/module(s)

---

## Phase 1: Repository and Application Scaffolding (Setup)

**Purpose**: Project initialization — no business logic yet.

- [X] T001 Create Python project scaffold: `pyproject.toml` (Python 3.12+, deps: fastapi, pydantic>=2, sqlalchemy>=2, chromadb, httpx, uvicorn, `anthropic` as an optional extra), matching `src/concierge/*` + `apps/api` layout from plan.md
- [X] T002 [P] Create `src/concierge/__init__.py` and empty package inits for `domain/`, `journey/`, `events/`, `decisioning/`, `conversation/`, `knowledge/`, `providers/`, `analytics/`, `persistence/`
- [X] T003 [P] Create `apps/api/__init__.py`, `apps/api/main.py` (bare `FastAPI()` app + `GET /health`), `apps/api/routers/__init__.py`, `apps/api/schemas/__init__.py`, `apps/api/deps.py` stub
- [X] T004 [P] Scaffold `apps/web` with the Vite React-TS template (`apps/web/package.json`, `apps/web/src/main.tsx`, `apps/web/index.html`)
- [X] T005 [P] Create `apps/web/src/theme/theme-tokens.css` with CSS custom properties (`--color-*`, `--space-*`, `--font-*`) per research.md §8
- [X] T006 [P] Create `seeds/scenarios/` and `knowledge_base/` directories, each with a short `README.md` documenting the expected file format
- [X] T007 Configure pytest (`pyproject.toml`/`pytest.ini`) and create `tests/unit/__init__.py`, `tests/integration/__init__.py`, `tests/e2e/__init__.py`
- [X] T008 [P] Configure Vitest + React Testing Library in `apps/web` (`apps/web/vitest.config.ts`, `apps/web/tests/setup.ts`)
- [X] T009 Create `docker-compose.yml` with `api` and `web` services per research.md §9
- [X] T010 [P] Create `.env.example` documenting `ANTHROPIC_API_KEY` (optional), `DATABASE_URL` default, `CHROMA_PERSIST_DIR`
- [X] T011 Add structured JSON logging + correlation-id middleware in `apps/api/middleware.py`, wired into `apps/api/main.py` (research.md §7)

**Checkpoint**: `uvicorn apps.api.main:app` serves `/health`; `npm run dev` in `apps/web` serves a blank page. Nothing functional yet.

---

## Phase 2: Domain Model + Persistence + Seeded Scenarios (Foundational)

**Purpose**: Blocking prerequisite for every user story — no journey, event, NBA, health, chat, or dashboard work can start until this phase is done.

- [X] T012 [P] Define enums in `src/concierge/domain/enums.py`: `ActivityStatus`, `RequirementClass`, `PlanType`, `HealthBand`, `ActivityScope`
- [X] T013 [P] Define value objects/DTOs in `src/concierge/domain/models.py`: `ReasonCode`, `ActivityDefinition` per data-model.md
- [X] T014 Create SQLAlchemy 2.0 base + engine/session factory in `src/concierge/persistence/db.py` (SQLite default, env-driven URL per research.md §2)
- [X] T015 [P] Define SQLAlchemy models in `src/concierge/persistence/models.py`: `Account`, `Line`, `AccountJourney`, `LineOnboardingState`, `ActivityInstance` per data-model.md
- [X] T016 [P] Define SQLAlchemy models in `src/concierge/persistence/event_models.py`: `DomainEvent`, `ProcessedEvent`, `DeadLetterEvent`, `StateTransitionLog`
- [X] T017 [P] Define SQLAlchemy models in `src/concierge/persistence/decision_models.py`: `NextBestActionRecord`, `HealthScoreRecord`, `OutreachAttempt`, `EscalationCase`, `ConsentPreference`
- [X] T018 [P] Define SQLAlchemy models in `src/concierge/persistence/billing_models.py`: `BillingSnapshot`, `RenewalSnapshot`, `RiskScoreSnapshot`
- [X] T019 [P] Define SQLAlchemy models in `src/concierge/persistence/conversation_models.py`: `ConversationSession`, `ConversationTurn`, `KnowledgeDocument`
- [X] T020 Implement repository classes in `src/concierge/persistence/repositories.py`: `JourneyRepository`, `EventRepository`, `DecisionRepository`, `ConsentRepository` (domain-shaped methods only, per research.md §1 — no raw `Session` leaks outside `persistence/`)
- [X] T021 Implement the postpaid/prepaid `ActivityDefinition` catalog in `src/concierge/journey/activity_catalog.py` from the table in data-model.md §ActivityDefinition
- [X] T022 [P] Author `seeds/scenarios/postpaid-device-port-in.json` and `seeds/scenarios/prepaid-byod-esim.json` per quickstart.md's scenario list
- [X] T023 [P] Author `seeds/scenarios/multi-line-postpaid.json` and `seeds/scenarios/repeated-activation-failure.json`
- [X] T024 [P] Author `seeds/scenarios/delayed-failed-port.json` and `seeds/scenarios/app-adoption-gap-day3.json`
- [X] T025 [P] Author `seeds/scenarios/postpaid-first-bill-day21.json` and `seeds/scenarios/prepaid-renewal-approaching.json`
- [X] T026 [P] Author `seeds/scenarios/contextual-troubleshooting.json`, `seeds/scenarios/human-escalation-with-context.json`, and `seeds/scenarios/customer-opt-out.json`
- [X] T027 Implement the scenario loader in `src/concierge/journey/scenario_loader.py`: reads a `seeds/scenarios/*.json` file, truncates prior scenario state, creates `Account`/`Line`/`AccountJourney`/`LineOnboardingState`/`ActivityInstance` rows with a backdated `started_at` (research.md §6), replays any pre-existing events
- [X] T028 [P] Unit test activity-catalog completeness (every plan-type × requirement-class combination from data-model.md is present) in `tests/unit/test_activity_catalog.py`
- [X] T029 [P] Unit test scenario-loader determinism/reset (loading a scenario twice yields identical state, no residue) in `tests/unit/test_scenario_loader.py`

**Checkpoint**: Database schema exists; all 11 scenario files load cleanly via the loader in a script/REPL; no API wiring yet.

---

## Phase 3: Event Ingestion + JourneyOrchestrator + Idempotency (Foundational)

**Purpose**: Blocking prerequisite for US1-US3 and US6 (the event injector) — every downstream state change flows through this. Also establishes the demo-scenario HTTP endpoints and demo auth (T036a-c) here, before any customer-specific endpoint is wired in Phase 4+, so every such endpoint can enforce authentication from the moment it's created.

- [X] T030 Define the Event Pydantic schema in `apps/api/schemas/events.py` mirroring `contracts/openapi.yaml`'s `DomainEvent`, including the 18 `event_type` enum values
- [X] T031 Implement idempotent ingestion in `src/concierge/events/ingestion.py`: check `ProcessedEvent` by `event_id`, short-circuit on duplicate, else persist `DomainEvent` + mark processed (FR-008)
- [X] T032 Implement dead-letter handling in `src/concierge/events/ingestion.py`: on unknown `account_id`/`line_id`, write `DeadLetterEvent` and return without state mutation (FR-009a); a later resubmission with the same `event_id`, once the entity exists, is processed normally
- [X] T033 Implement the out-of-order/terminal-state guard in `src/concierge/events/ingestion.py`: compare the incoming event's `occurred_at` against the `ActivityInstance`'s last-applied event timestamp before letting a non-terminal status override `COMPLETED`
- [X] T034 Implement `JourneyOrchestrator` in `src/concierge/journey/orchestrator.py`: routes an ingested event to the correct `ActivityInstance` transition(s), writes `StateTransitionLog` rows, triggers downstream health/NBA recomputation hooks, including a `StateTransitionLog` row whenever the recomputation changes a `HealthScoreRecord` or `NextBestActionRecord`, not just an `ActivityInstance`
- [X] T035 Implement activity-status transition rules in `src/concierge/journey/transitions.py`: pure functions mapping `(activity_code, current_status, event_type) → new_status`, covering `NOT_STARTED→IN_PROGRESS→COMPLETED/FAILED` and `NOT_APPLICABLE` assignment at instantiation
- [X] T036 Wire `POST /api/events` in `apps/api/routers/events.py`, calling `src/concierge/events/ingestion.py` + `JourneyOrchestrator`, returning `{event_id, outcome}` per contracts/openapi.yaml
- [X] T036a Wire `GET /api/demo/scenarios` and `POST /api/demo/scenarios/{id}/reset` in `apps/api/routers/demo.py`, calling `src/concierge/journey/scenario_loader.py` (T027); register the demo router in `apps/api/main.py`
- [X] T036b Implement demo auth in `apps/api/deps.py`: `POST /api/auth/login` issues an in-memory bearer token → `customer_id` mapping (research.md §5); a `get_current_customer` dependency resolves the `Authorization` header or returns `None` for unauthenticated requests
- [X] T036c Wire `POST /api/auth/login` in `apps/api/routers/auth.py` per contracts/openapi.yaml
- [X] T037 [P] Unit test idempotency (duplicate `event_id` produces no second state change) in `tests/unit/test_event_idempotency.py`
- [X] T038 [P] Unit test dead-letter + resubmission behavior in `tests/unit/test_event_dead_letter.py`
- [X] T039 [P] Unit test the out-of-order terminal-state guard (a `FAILED` event after `COMPLETED` does not regress the instance) in `tests/unit/test_out_of_order_events.py`
- [X] T040 [P] Unit test activity transition rules in `tests/unit/test_activity_transitions.py`
- [X] T041 Integration test `POST /api/events` → `GET /api/journeys/{id}` state progression via httpx `TestClient` in `tests/integration/test_event_to_journey.py`

**Checkpoint**: Injecting events via the API visibly progresses a seeded journey's activity states; replaying an event is a safe no-op; `GET`/`POST /api/demo/scenarios*` return the 11 seeded scenarios and reset cleanly; `POST /api/auth/login` issues a usable session token.

---

## Phase 4: Postpaid/Prepaid Templates + Multi-Line Behavior [US1]

**Goal**: A new line is enrolled at order completion, tracks its plan-type-specific required activities to completion, and multi-line accounts track each line independently.

**Independent Test**: Reset `postpaid-device-port-in`, `prepaid-byod-esim`, and `multi-line-postpaid`; inject each scenario's activation/network/security events; verify every line reaches `COMPLETE` and the account journey completes only once every line does.

- [X] T042 [US1] Implement journey enrollment on `OrderCompleted` in `src/concierge/journey/enrollment.py`: create-or-attach-to-existing `AccountJourney` (at most one active journey per account, per Clarifications), instantiate `LineOnboardingState` + `ActivityInstance` rows from the activity catalog per each line's `plan_type` (FR-001, FR-002, FR-003)
- [X] T043 [US1] Implement `NOT_APPLICABLE` assignment for number-transfer when no port is requested, in `src/concierge/journey/enrollment.py`
- [X] T044 [US1] Implement line- and account-level onboarding-completion derivation in `src/concierge/journey/status.py`: line `COMPLETE` when all REQUIRED applicable activities are `COMPLETED`/`NOT_APPLICABLE`; journey `COMPLETE` when every line is `COMPLETE` (FR-005)
- [X] T045 [US1] Implement the journey `EXPIRED` transition in `src/concierge/journey/status.py`: `ACTIVE→EXPIRED` when `now() > expires_at` and the journey is not yet `COMPLETE`
- [X] T046 [US1] Wire `GET /api/journeys/{journey_id}` in `apps/api/routers/journeys.py`, returning `AccountJourneyView` (account + per-line activities, `current_day`) per contracts/openapi.yaml, protected by the `get_current_customer` dependency (T036b): returns 401 if unauthenticated, 403 if the authenticated customer does not own this journey
- [X] T047 [P] [US1] Unit test enrollment for single-line postpaid-with-port, prepaid-BYOD-no-port, and multi-line postpaid in `tests/unit/test_enrollment.py`
- [X] T048 [P] [US1] Unit test completion derivation (line-level and account-level, including "one line incomplete keeps journey incomplete") in `tests/unit/test_completion.py`
- [X] T049 [US1] Integration test the golden-path walkthrough (reset `postpaid-device-port-in` → inject activation/network/security events → `GET` journey shows `COMPLETE`) in `tests/integration/test_golden_path.py`
- [X] T050 [US1] Integration test the `multi-line-postpaid` scenario (one line completes, the other lags, account stays incomplete) in `tests/integration/test_multiline_journey.py`

**Checkpoint**: US1 is independently demoable end-to-end.

---

## Phase 5: Health Scoring + NBA + Contact/Consent Policy [US2, US3]

**Goal**: Friction is detected and deterministically ranked into a next best action per line, respecting contact governance; recommended-activity nudges surface on schedule.

**Independent Test (US2)**: Seed a journey in progress; trigger an activation failure, a port failure/delay, repeated help/chat, and an opt-out; verify correctly-ranked NBAs, correct health deductions/reason codes, and contact-policy enforcement (caps, quiet hours, opt-out, escalation suppression). **Independent Test (US3)**: Seed a journey past day 3/7/10 thresholds with gaps open; verify the correctly-timed nudge appears and clears once the underlying event arrives.

- [X] T051 [US2] Implement health-score computation in `src/concierge/decisioning/health_score.py`: pure function applying the FR-016 deductions with reason codes, clamped 0-100, computing both per-line and per-account (account = min of its lines') scores per data-model.md
- [X] T052 [US2] Implement health-band classification (GREEN/YELLOW/RED) in `src/concierge/decisioning/health_score.py` per FR-017
- [X] T053 [US2] Implement NBA candidate generation in `src/concierge/decisioning/nba.py`: enumerate eligible actions per line from activity state + elapsed journey day per FR-011
- [X] T054 [US2] Implement NBA ranking + tie-break in `src/concierge/decisioning/nba.py`: sort by base priority then the defined tie-break order (critical > required setup > billing/renewal > digital adoption > optional adoption), independently per line (Clarifications Q2), per FR-012
- [X] T055 [US2] Implement the escalation-suppression filter in `src/concierge/decisioning/nba.py`: exclude NBA candidates whose issue has an open `EscalationCase` (FR-028a)
- [X] T056 [US2] Implement contact policy in `src/concierge/decisioning/contact_policy.py`: shared daily/weekly cap counters across a customer's lines, quiet-hours window check, consent/opt-out override, drawing outreach from all lines' eligible actions in priority order until the cap is reached (FR-014, FR-015)
- [X] T057 [US2] Implement repeated-help-visit / repeated-chat friction detection in `src/concierge/decisioning/friction.py`: counts `HelpArticleViewed`/`ChatStarted` events on the same topic within the active journey, feeding health-score deductions and NBA eligibility (FR-019)
- [X] T057a [US2] Implement abandoned-setup friction detection in `src/concierge/decisioning/friction.py`: a `SetupAbandoned` event for a still `NOT_STARTED`/`IN_PROGRESS` activity applies the setup-abandoned health deduction (FR-016) and feeds NBA eligibility (FR-019); the deduction clears once that activity later completes
- [X] T058 [US2] Wire `GET /api/journeys/{journey_id}/recommendation` in `apps/api/routers/journeys.py`, returning one `NextBestAction` per line per contracts/openapi.yaml, protected by the `get_current_customer` dependency (T036b): returns 401 if unauthenticated, 403 if the authenticated customer does not own this journey
- [X] T059 [US2] Wire `GET /api/journeys/{journey_id}/health` in `apps/api/routers/journeys.py`, returning account + per-line `HealthScore` per contracts/openapi.yaml, protected by the `get_current_customer` dependency (T036b): returns 401 if unauthenticated, 403 if the authenticated customer does not own this journey
- [X] T060 [P] [US2] Unit test health-score deductions and clamping (every FR-016 deduction individually and combined) in `tests/unit/test_health_score.py`
- [X] T061 [P] [US2] Unit test NBA base-priority ranking and tie-break order in `tests/unit/test_nba_ranking.py`
- [X] T062 [P] [US2] Unit test contact policy (daily/weekly cap, quiet hours, opt-out override, escalation suppression, suppressed attempts don't consume the cap) in `tests/unit/test_contact_policy.py`
- [X] T062a [P] [US2] Unit test abandoned-setup detection (deduction applied on `SetupAbandoned`, cleared on later completion) in `tests/unit/test_setup_abandoned.py`
- [X] T062b [P] [US2] Unit test `StateTransitionLog` rows are written when health score or NBA changes (not just `ActivityInstance` transitions), verifying FR-009's audit-trail requirement covers decisioning outputs, in `tests/unit/test_audit_trail_health_nba.py`
- [X] T063 [US2] Integration test the `repeated-activation-failure` scenario (health deduction does not decrease on repeat; NBA stays highest priority) in `tests/integration/test_repeated_failure.py`
- [X] T064 [US2] Integration test the `delayed-failed-port` scenario (port-pending-too-long deduction + correspondingly prioritized NBA) in `tests/integration/test_port_failure.py`
- [X] T065 [US2] Integration test the `customer-opt-out` scenario (no outreach delivered after opt-out; suppression recorded) in `tests/integration/test_opt_out.py`
- [X] T066 [US3] Implement day-gated recommended-activity NBA candidates (AutoPay/auto-recharge after day 7, app after day 3, voicemail after day 5, protection after day 10) in `src/concierge/decisioning/nba.py`, reusing T053's candidate generator
- [X] T067 [US3] Implement recommended-activity completion handling (e.g., `AutoPayEnabled` marks the activity `COMPLETED`, removes the deduction, removes the NBA) via a `JourneyOrchestrator` hook in `src/concierge/journey/orchestrator.py`
- [X] T068 [P] [US3] Unit test day-gated NBA eligibility (action absent before threshold day, present after) in `tests/unit/test_nba_day_gating.py`
- [X] T069 [US3] Integration test the `app-adoption-gap-day3` scenario (no app-adoption NBA before day 3, present after, cleared on `MobileAppDownloaded`) in `tests/integration/test_app_adoption_gap.py`

**Checkpoint**: US2 and US3 are independently demoable end-to-end (on top of US1).

---

## Phase 6: Provider Interfaces + Mocks + Billing/Renewal Calculations

**Purpose**: Mock-first integration seam (Constitution Principle II) for every external dependency; billing/renewal arithmetic for US3.

- [X] T070 [P] Define provider `Protocol`s in `src/concierge/providers/protocols.py`: `CustomerProvider`, `OrderProvider`, `BillingProvider`, `NotificationProvider`, `SupportProvider`, `RiskScoringProvider`, `LLMProvider`, `EmbeddingProvider` (FR-029)
- [X] T071 [P] Implement `MockCustomerProvider` and `MockOrderProvider` in `src/concierge/providers/mock_customer.py` and `mock_order.py`, seeded from scenario files
- [X] T072 [P] Implement `MockNotificationProvider` in `src/concierge/providers/mock_notification.py`: records an `OutreachAttempt` with a channel abstraction (push/SMS/email/in-app) per FR-030, no real integration
- [X] T073 [P] Implement `MockSupportProvider` in `src/concierge/providers/mock_support.py`: accepts an `EscalationCase` payload and returns a mock case-handle/status
- [X] T074 [P] Implement `MockRiskScoringProvider` in `src/concierge/providers/mock_risk_scoring.py`: deterministic churn/call/retail-visit/adoption scores from a fixed formula over journey state (no ML training), stable interface per FR-031
- [X] T075 [US3] Implement `MockBillingProvider` in `src/concierge/providers/mock_billing.py`: returns seeded `BillingSnapshot` (postpaid) / `RenewalSnapshot` (prepaid) fixtures per scenario
- [X] T076 [US3] Implement deterministic postpaid bill-estimate computation in `src/concierge/decisioning/billing.py`: sums recurring/one-time/installment/taxes/credits from `BillingSnapshot` into a plain-language estimate DTO, explicitly distinct from a final bill amount (FR-025)
- [X] T077 [US3] Implement prepaid renewal-readiness computation in `src/concierge/decisioning/billing.py`: derives a `renewal_ready` boolean + fields from `RenewalSnapshot` (FR-026)
- [X] T078 [US3] Wire `GET /api/journeys/{journey_id}/billing` in `apps/api/routers/journeys.py`, returning `BillingOrRenewalView` per contracts/openapi.yaml, protected by the `get_current_customer` dependency (T036b): returns 401 if unauthenticated, 403 if the authenticated customer does not own this journey
- [X] T079 [P] [US3] Unit test postpaid bill-estimate arithmetic against known `BillingSnapshot` fixtures in `tests/unit/test_billing_arithmetic.py`
- [X] T080 [P] [US3] Unit test prepaid renewal-readiness derivation in `tests/unit/test_renewal_readiness.py`
- [X] T081 [US3] Integration test the `postpaid-first-bill-day21` scenario (bill estimate visible and correctly computed at day 21) in `tests/integration/test_first_bill.py`
- [X] T082 [US3] Integration test the `prepaid-renewal-approaching` scenario (renewal-readiness fields correct; auto-recharge gap reflected in health/NBA) in `tests/integration/test_renewal_approaching.py`
- [X] T082a Integration test auth boundary: unauthenticated requests to `GET /api/journeys/{id}`, `.../recommendation`, `.../health`, `.../billing` return 401; an authenticated customer requesting another customer's `journey_id` returns 403 — in `tests/integration/test_auth_boundary.py`
- [X] T083 [P] Unit test each `Mock*Provider` returns deterministic output across repeated calls with the same seed input in `tests/unit/test_mock_providers.py`

**Checkpoint**: Every provider has a working seeded mock; billing/renewal views are correct and explainable.

---

## Phase 7: Local Knowledge Ingestion + Chroma Retrieval [US5]

**Goal**: Generic, unauthenticated wireless guidance is grounded in a curated local knowledge base.

**Independent Test**: With no auth header, ask a generic question per knowledge topic and confirm a grounded answer with source citations; confirm no customer-specific data path exists.

- [X] T084 [US5] Author the 14 curated `knowledge_base/*.md` documents (activation, esim-sim, porting, voicemail, app, security, billing, first-bill, autopay, auto-recharge, device-protection, network-troubleshooting, plan-data-usage, international-usage, prepaid-renewal) per FR-020's topic list
- [X] T085 [US5] Implement a `DefaultEmbeddingFunction`-backed `EmbeddingProvider` in `src/concierge/providers/embedding_local.py` (research.md §3)
- [X] T086 [US5] Implement knowledge ingestion in `src/concierge/knowledge/ingest.py`: parses `knowledge_base/*.md` into `KnowledgeDocument` rows + upserts into a Chroma `PersistentClient` collection, run idempotently on startup
- [X] T087 [US5] Implement retrieval in `src/concierge/knowledge/retrieval.py`: query the Chroma collection, return ranked `KnowledgeDocument` matches with source `doc_id`/`title`/`topic` ("RAG returns source metadata")
- [X] T088 [US5] Wire `GET /api/knowledge/search` in `apps/api/routers/knowledge.py`, returning a `KnowledgeSearchResult` list per contracts/openapi.yaml
- [X] T089 [P] [US5] Unit test retrieval ranking returns the expected topic for a canned query per knowledge topic in `tests/unit/test_knowledge_retrieval.py`
- [X] T090 [US5] Integration test `GET /api/knowledge/search` unauthenticated returns grounded, non-account-specific results in `tests/integration/test_knowledge_search_api.py`

**Checkpoint**: US5's generic-help slice is independently demoable.

---

## Phase 8: Auth-Aware AI Concierge + StubLLMProvider + Optional Real Adapter [US4, US5]

**Goal**: Authenticated customers get grounded, context-correct troubleshooting; unauthenticated visitors get generic help only; the system fully functions with no API key. (Auth itself — `POST /api/auth/login` and the `get_current_customer` dependency — was implemented earlier, in Phase 3/T036b-c, so every customer-specific endpoint from Phase 4 onward could enforce it from the start; this phase consumes that auth context.)

**Independent Test (US4)**: Authenticate as a seeded customer, ask the concierge to explain the current NBA, ask a knowledge-covered troubleshooting question, and attempt to make it invent a billing number or perform an unsupported action — verify the first two are grounded/correct and the third is refused. **Independent Test (US5)**: Same generic question, unauthenticated, still works; an account-specific question is declined with an auth prompt.

- [X] T093 [P] Implement `StubLLMProvider` in `src/concierge/providers/stub_llm.py`: deterministic templated responses referencing only fields present in the supplied `ConciergeContext` DTO, no network calls
- [X] T094 [P] Implement `AnthropicLLMProvider` in `src/concierge/providers/anthropic_llm.py`: activated only when `ANTHROPIC_API_KEY` is set (research.md §4), identical interface to `StubLLMProvider`
- [X] T095 Implement `LLMProvider` factory/selection in `apps/api/main.py` startup wiring (env-driven, per research.md §4)
- [X] T096 [US4] Implement `ConciergeContext` DTO assembly in `src/concierge/conversation/context.py`: read-only snapshot of customer type, plan/device, line state, journey day, activity statuses, current NBA, health-score reasons, billing/renewal facts, recent support context (FR-022) — conversation code never queries persistence beyond this assembly step
- [X] T097 [US4] Implement grounded-answer orchestration in `src/concierge/conversation/engine.py`: for authenticated sessions, combine `ConciergeContext` + retrieved `KnowledgeDocument` sources into a bounded prompt for the `LLMProvider`; forbid fabricated customer facts/billing numbers by only ever interpolating values already present in the context DTO (FR-023)
- [X] T098 [US4] Implement the supported-action guard in `src/concierge/conversation/engine.py`: recognize requests for actions outside the enumerated supported-action set (data-model.md) and respond with a supported alternative/escalation offer instead of claiming completion (FR-024)
- [X] T099 [US5] Implement unauthenticated-path handling in `src/concierge/conversation/engine.py`: generic questions answered from knowledge retrieval only; account-specific questions declined with an authenticate prompt; zero customer-specific data enters the unauthenticated code path (FR-020, FR-021)
- [X] T100 [US4] Implement troubleshooting-attempt tracking in `src/concierge/conversation/attempts.py`: persists `ConversationTurn.troubleshooting_topic`/`resolved`, counts consecutive unresolved attempts on the same topic within a `ConversationSession` (feeds FR-027's two-attempt escalation trigger)
- [X] T101 Wire `POST /api/chat` in `apps/api/routers/chat.py`: resolves optional auth, builds `ConciergeContext` when authenticated, calls the conversation engine, returns `ChatResponse` with sources per contracts/openapi.yaml
- [X] T101a [US2] Implement NBA-message personalization in `apps/api/routers/journeys.py`'s recommendation handler (or a thin `src/concierge/conversation/personalize.py` helper): after `decisioning.nba` (T053-T054) finalizes a `NextBestActionRecord`, call `LLMProvider` to generate its `message` field from already-computed values only; `src/concierge/decisioning/nba.py` itself stays LLM-free (Constitution Principle I) — the call happens only in this outer layer (FR-013)
- [X] T101b [US3] Implement billing/renewal explanation personalization in `apps/api/routers/journeys.py`'s billing handler (or the same `personalize.py` helper): after `decisioning.billing` (T076-T077) computes `BillingOrRenewalView`'s deterministic fields, call `LLMProvider` to generate the `explanation` field from those fields only (FR-025, FR-026)
- [X] T101c [P] Unit test personalization is additive-only — message/explanation text changes never alter the underlying deterministic priority/reason_codes/estimate fields — in `tests/unit/test_personalization_boundary.py`
- [X] T102 [P] [US4] Unit test `ConciergeContext` assembly contains only real provider/state-sourced fields (no LLM-invented values possible by construction) in `tests/unit/test_concierge_context.py`
- [X] T103 [P] [US4] Unit test the supported-action guard rejects an out-of-scope request in `tests/unit/test_supported_action_guard.py`
- [X] T104 [P] [US5] Unit test the unauthenticated engine never receives or returns customer-specific fields in `tests/unit/test_unauthenticated_chat.py`
- [X] T105 [US4] Integration test the `contextual-troubleshooting` scenario (authenticated chat explains current NBA correctly, answers a knowledge-covered question grounded in retrieved sources) in `tests/integration/test_chat_authenticated.py`
- [X] T106 [US5] Integration test `POST /api/chat` unauthenticated (generic Q&A works; account-specific question declined + auth prompt) in `tests/integration/test_chat_unauthenticated.py`

**Checkpoint**: US4 and US5 are independently demoable end-to-end.

---

## Phase 9: Escalation Workflow [US2, US4]

**Goal**: Every defined escalation trigger reliably produces a complete, context-rich `EscalationCase`.

**Independent Test**: Force each of the 6 triggers (explicit request, low-confidence, two failed troubleshooting attempts, unresolved activation/port failure, billing dispute, sensitive request) and confirm a case is created with full journey/event/conversation context, and that further proactive outreach for that issue is suppressed while it's open.

- [X] T107 [US2] Implement escalation-trigger evaluation in `src/concierge/decisioning/escalation.py`: pure functions for each of the 6 FR-027 triggers
- [X] T108 [US2] Implement `EscalationCase` creation in `src/concierge/decisioning/escalation.py`: bundles reason, priority, journey/line snapshot, relevant `event_id`s, attempted NBA/troubleshooting ids, conversation summary (FR-028)
- [X] T109 [US2] Implement `EscalationCase` lifecycle (`OPEN→RESOLVED/CLOSED`) in `src/concierge/decisioning/escalation.py`, tied to the outreach-suppression check from T055 (FR-028a)
- [X] T110 [US4] Wire the two-failed-troubleshooting-attempt trigger from T100's attempt tracker into `src/concierge/conversation/engine.py`, calling escalation creation automatically
- [X] T111 Wire `POST /api/escalations` and `GET /api/escalations` in `apps/api/routers/escalations.py` per contracts/openapi.yaml, protected by the `get_current_customer` dependency (T036b): returns 401 if unauthenticated
- [X] T112 [P] [US2] Unit test each of the 6 escalation triggers fires under its specific condition and not otherwise in `tests/unit/test_escalation_triggers.py`
- [X] T113 [P] [US2] Unit test `EscalationCase` content completeness (all required fields populated) in `tests/unit/test_escalation_case_content.py`
- [X] T114 [US2] Integration test the `human-escalation-with-context` scenario (unresolved activation failure escalates with full journey/event context, no repeated customer input needed) in `tests/integration/test_escalation_with_context.py`

**Checkpoint**: Escalation is fully wired and independently verifiable.

---

## Phase 10: React Demo UI [US1, US2, US3, US4, US5, US6]

**Goal**: A single polished demo application surfaces every capability above.

- [X] T115 [US6] Implement the typed API client in `apps/web/src/api/client.ts` covering every endpoint in contracts/openapi.yaml
- [X] T116 [US6] Implement `ScenarioSelector` in `apps/web/src/components/ScenarioSelector.tsx`: lists + resets the 11 `seeds/scenarios/*.json` scenarios via `GET`/`POST /api/demo/scenarios*`
- [X] T117 [US1] Implement `JourneyTimeline` in `apps/web/src/components/JourneyTimeline.tsx`: renders account + per-line `ActivityInstance` statuses from `GET /api/journeys/{id}`
- [X] T118 [US1] Implement `EventInjector` in `apps/web/src/components/EventInjector.tsx`: form to `POST /api/events` with the 18 supported event types against the active scenario's journey/line ids
- [X] T119 [US2] Implement `HealthBadge` in `apps/web/src/components/HealthBadge.tsx`: renders GREEN/YELLOW/RED band + reason codes from `GET /api/journeys/{id}/health`
- [X] T120 [US2] Implement `NBACard` in `apps/web/src/components/NBACard.tsx`: renders the current per-line `NextBestAction` + reason codes from `GET /api/journeys/{id}/recommendation`
- [X] T121 [US2] Implement `EscalationResult` in `apps/web/src/components/EscalationResult.tsx`: renders an `EscalationCase`'s reason/priority/context after `POST /api/escalations`
- [X] T122 [US3] Implement `BillingCard` in `apps/web/src/components/BillingCard.tsx`: renders the postpaid estimate or prepaid renewal readiness from `GET /api/journeys/{id}/billing`
- [X] T123 [US4] [US5] Implement `ChatPanel` in `apps/web/src/components/ChatPanel.tsx`: login/logout toggle (`POST /api/auth/login`), message thread, source citations, `POST /api/chat` wiring for both authenticated and unauthenticated modes
- [X] T124 [US1] Implement `JourneyPage` in `apps/web/src/pages/JourneyPage.tsx`, composing `ScenarioSelector` + `JourneyTimeline` + `EventInjector` + `HealthBadge` + `NBACard` + `BillingCard` + `EscalationResult`
- [X] T125 [US6] Implement top-level routing/layout in `apps/web/src/App.tsx` (`JourneyPage`, `ChatPage`, `DashboardPage`)
- [X] T126 [P] [US1] Component smoke test for `JourneyTimeline` in `apps/web/tests/JourneyTimeline.test.tsx`
- [X] T127 [P] [US2] Component smoke test for `NBACard` and `HealthBadge` in `apps/web/tests/NbaAndHealth.test.tsx`
- [X] T128 [P] [US4] Component smoke test for `ChatPanel`'s auth toggle in `apps/web/tests/ChatPanel.test.tsx`

**Checkpoint**: The full demo is operable end-to-end through the UI alone.

---

## Phase 11: Dashboard Metrics + POCR/PORR Simulated Labels [US6]

**Goal**: The aggregate dashboard demonstrates the business outcome with clearly labeled simulated figures.

**Independent Test**: Run several scenarios, open the dashboard, and confirm every count is correct and the POCR/PORR tiles are visibly labeled simulated/projected wherever they render.

- [X] T129 [US6] Implement dashboard aggregation in `src/concierge/analytics/dashboard.py`: `enrolled_customers`, engagement, `onboarding_completion_rate`, `digital_resolutions`, `escalations` counts computed from persisted journey/outreach/escalation state
- [X] T130 [US6] Implement simulated POCR/PORR intervention-count estimation in `src/concierge/analytics/pocr_porr.py`: deterministic formula over digital resolutions / escalations-avoided, always paired with a `simulated: true` flag + disclaimer label (FR-035, Constitution Principle X)
- [X] T131 [US6] Wire `GET /api/dashboard` in `apps/api/routers/dashboard.py`, returning `DashboardView` per contracts/openapi.yaml
- [X] T132 [US6] Implement `KpiTiles` + `DashboardPage` in `apps/web/src/pages/DashboardPage.tsx` and `apps/web/src/components/KpiTiles.tsx`: renders every dashboard field, with a visibly styled "simulated/projected" label on the POCR/PORR tiles specifically
- [X] T133 [P] [US6] Unit test POCR/PORR computation always returns `simulated=true` and a non-empty label in `tests/unit/test_pocr_porr_labeling.py`
- [X] T134 [US6] Integration test `GET /api/dashboard` reflects counts after running several scenarios in `tests/integration/test_dashboard.py`

**Checkpoint**: US6 is independently demoable; all six user stories are now complete.

---

## Phase 12: End-to-End Scenario Tests + Demo Script + Documentation (Polish & Cross-Cutting)

**Purpose**: Prove the five live-demo flows work with zero placeholders, and hand the reviewer a runnable, documented package.

- [X] T135 E2E test: postpaid activation failure full walkthrough (`repeated-activation-failure` scenario → escalation) in `tests/e2e/test_e2e_postpaid_activation_failure.py`
- [X] T136 [P] E2E test: prepaid renewal full walkthrough (`prepaid-renewal-approaching` scenario → chat explains renewal readiness) in `tests/e2e/test_e2e_prepaid_renewal.py`
- [X] T137 [P] E2E test: multi-line journey full walkthrough (`multi-line-postpaid` scenario → per-line independent NBA/health, correct account-completion timing) in `tests/e2e/test_e2e_multiline_journey.py`
- [X] T138 [P] E2E test: opt-out full walkthrough (`customer-opt-out` scenario → no outreach delivered) in `tests/e2e/test_e2e_opt_out.py`
- [X] T139 [P] E2E test: human escalation full walkthrough (`human-escalation-with-context` scenario → escalation case has full context) in `tests/e2e/test_e2e_human_escalation.py`
- [X] T140 Verify zero TODO/placeholder code paths across the 5 E2E-tested live-demo flows (grep sweep + manual review) before README finalization
- [X] T141 Author `docs/architecture.md` with a Mermaid module/component diagram matching plan.md's Project Structure
- [X] T142 [P] Author `docs/sequences.md` with Mermaid sequence diagrams: event ingestion → health/NBA recompute, proactive outreach decision, chat + RAG, escalation creation
- [X] T143 Author `README.md`: architecture summary, prerequisites, exact run commands (quickstart.md Options A/B), seeded demo users/scenarios table, curl API examples, and a 5-7 minute judge demo script walking scenarios 1, 4, 8, 9, 10
- [X] T144 Final full-suite run: `pytest` (unit+integration+e2e) and `npm test` in `apps/web`, both green, referenced in README's verification note

**Checkpoint**: The MVP is demo-ready and documented.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies.
- **Phase 2 (Foundational)**: Depends on Phase 1.
- **Phase 3 (Foundational)**: Depends on Phase 2.
- **Phase 4 [US1]**: Depends on Phase 3. Independently testable/demoable once complete — this is the MVP floor.
- **Phase 5 [US2, US3]**: Depends on Phase 4 (reads journey/activity state Phase 4 establishes).
- **Phase 6 (Providers + billing)**: Provider protocols/mocks (T070-T074) can start as soon as Phase 2 is done (parallel to Phases 3-5); billing tasks (T075-T082) depend on Phase 5's NBA/health work for the day-gated billing/renewal NBA tie-in.
- **Phase 7 [US5, knowledge]**: Depends only on Phase 2 (persistence) — can run in parallel with Phases 3-6.
- **Phase 8 [US4, US5]**: Depends on Phase 5 (NBA/health context), Phase 6 (billing context, providers), and Phase 7 (knowledge retrieval).
- **Phase 9 [US2, US4]**: Depends on Phase 5 (NBA/contact policy) and Phase 8 (troubleshooting-attempt tracking).
- **Phase 10 (UI)**: Depends on the API surface each component consumes — can start per-component as soon as its backing endpoint (Phases 4-9) is wired.
- **Phase 11 [US6]**: Depends on Phases 4-9 producing real data to aggregate.
- **Phase 12 (Polish)**: Depends on everything above.

### Parallel Opportunities

- All `[P]`-marked tasks within a phase touch different files and can run concurrently once that phase's non-`[P]` prerequisites land.
- Phase 6 (T070-T074, provider protocols/mocks) and Phase 7 (knowledge ingestion) can proceed in parallel with Phases 3-5 once Phase 2 is done, since neither depends on journey/decisioning internals.
- Within Phase 10, once its backing endpoint exists, each UI component task is independent of the others.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (Setup) + Phase 2 + Phase 3 (Foundational).
2. Complete Phase 4 (US1).
3. **STOP and VALIDATE**: run `tests/integration/test_golden_path.py` and `tests/integration/test_multiline_journey.py`; demo scenarios 1-3 manually via `curl`/quickstart.md.

### Incremental Delivery

1. Foundational phases (1-3) → nothing demoable yet, but everything downstream is unblocked.
2. Phase 4 → US1 demoable (MVP).
3. Phase 5 → US2 + US3 demoable (friction handling, adoption nudges, billing/renewal groundwork).
4. Phase 6 → billing/renewal views complete; providers ready for Phase 8.
5. Phase 7 → US5 demoable (generic help).
6. Phase 8 → US4 demoable (authenticated troubleshooting); US5 chat completed.
7. Phase 9 → escalation fully wired into US2/US4.
8. Phase 10 → all stories now have a UI.
9. Phase 11 → US6 demoable (dashboard).
10. Phase 12 → judge-ready.
