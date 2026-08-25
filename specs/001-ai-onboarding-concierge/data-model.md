# Phase 1 Data Model: 30-Day Personalized AI Concierge

Entities marked **(spec)** come directly from `spec.md §Key Entities`. Entities marked **(plan)** are supporting structures this plan introduces to make spec behavior implementable and testable; they don't change spec scope.

## Account & Line (plan — provider-backed reference data)

Not owned/persisted by this system beyond a local cache; sourced from `CustomerProvider`/`OrderProvider` mocks and cached only as needed to drive journeys.

- **Account**: `account_id`, `customer_id`, `created_at`
- **Line**: `line_id`, `account_id`, `plan_type` (`POSTPAID` | `PREPAID`), `msisdn`/number (nullable until activation), `device_info`

## AccountJourney (spec)

- `journey_id` (PK)
- `account_id` (unique while `status = ACTIVE` — enforces "at most one active journey per account," per spec Assumptions)
- `status`: `ACTIVE` | `COMPLETE` | `EXPIRED`
- `started_at`, `expires_at` (`started_at + 30 days`)
- `completed_at` (nullable)
- Relationship: 1 → N `LineOnboardingState`

**State transitions**: `ACTIVE → COMPLETE` when every line's required+applicable activities reach `COMPLETED`/`NOT_APPLICABLE` (FR-005). `ACTIVE → EXPIRED` when `now() > expires_at` and status is still `ACTIVE` (spec Assumptions). Terminal states (`COMPLETE`, `EXPIRED`) do not transition further.

## LineOnboardingState (spec)

- `line_id` (PK, FK → Line)
- `journey_id` (FK → AccountJourney)
- `plan_type`: `POSTPAID` | `PREPAID` (denormalized from Line for fast per-line activity-catalog lookup)
- `status`: `IN_PROGRESS` | `COMPLETE` (derived: COMPLETE when all REQUIRED applicable `ActivityInstance`s are COMPLETED/NOT_APPLICABLE)
- Relationship: 1 → N `ActivityInstance`

## ActivityDefinition (spec) — seed/reference data, not per-journey rows

Static catalog, keyed by `(plan_type, activity_code)`. This is the concrete enumeration that resolves spec.md FR-004/FR-005's reference to "the defined postpaid and prepaid activity lists" (see `research.md §10`):

| activity_code | scope | POSTPAID class | PREPAID class |
|---|---|---|---|
| `SIM_ESIM_ACTIVATION` | LINE | REQUIRED | REQUIRED |
| `NUMBER_TRANSFER` | LINE | REQUIRED (NOT_APPLICABLE if no port) | REQUIRED (NOT_APPLICABLE if no port) |
| `NETWORK_VALIDATION` | LINE | REQUIRED | REQUIRED |
| `ACCOUNT_SECURITY` | ACCOUNT | REQUIRED | REQUIRED |
| `APP_ADOPTION` | LINE | RECOMMENDED | RECOMMENDED |
| `VOICEMAIL_SETUP` | LINE | RECOMMENDED | RECOMMENDED |
| `AUTOPAY_PAYMENT_SETUP` | ACCOUNT | RECOMMENDED | — |
| `PAPERLESS_BILLING` | ACCOUNT | RECOMMENDED | — |
| `FIRST_BILL_READINESS` | ACCOUNT | RECOMMENDED | — |
| `PAYMENT_METHOD_SETUP` | ACCOUNT | — | RECOMMENDED |
| `AUTO_RECHARGE_SETUP` | LINE | — | RECOMMENDED |
| `PLAN_DATA_USAGE_UNDERSTANDING` | LINE | — | RECOMMENDED |
| `BALANCE_RENEWAL_READINESS` | LINE | — | RECOMMENDED |
| `DEVICE_PROTECTION_DECISION` | LINE | OPTIONAL | OPTIONAL (if eligible) |
| `PREMIUM_FEATURE_ADOPTION` | LINE | OPTIONAL | OPTIONAL |

`—` means the activity is not part of that plan type's catalog at all (never instantiated for that plan type, distinct from `NOT_APPLICABLE` which is a runtime outcome for an instantiated activity like a port-less number transfer).

## ActivityInstance (spec)

- `instance_id` (PK)
- `journey_id`, `line_id` (nullable for ACCOUNT-scoped activities — scoped to the journey directly)
- `activity_code` (FK → ActivityDefinition)
- `requirement_class`: `REQUIRED` | `RECOMMENDED` | `OPTIONAL` (copied from `ActivityDefinition` at instantiation time, so later catalog edits don't retroactively change an in-flight journey)
- `status`: `NOT_STARTED` | `IN_PROGRESS` | `COMPLETED` | `FAILED` | `NOT_APPLICABLE`
- `updated_at`

**State transitions**: `NOT_STARTED → IN_PROGRESS → COMPLETED`, or `→ FAILED` from `NOT_STARTED`/`IN_PROGRESS`, or set to `NOT_APPLICABLE` at instantiation (e.g., no port requested). A terminal `COMPLETED` is never overwritten by a later-arriving out-of-order `FAILED` event for an earlier point in time (spec Assumptions; enforced by comparing the incoming event's `occurred_at` against the instance's last-applied event timestamp, not wall-clock receipt order).

## DomainEvent + ProcessedEvent (spec "Event", split for idempotency)

- **DomainEvent** (append-only log): `event_id` (PK), `event_type`, `customer_id`, `account_id`, `line_id` (nullable), `journey_id` (nullable), `occurred_at`, `source`, `correlation_id`, `attributes` (JSON)
- **ProcessedEvent** (dedupe index): `event_id` (PK, FK → DomainEvent), `processed_at` — existence of a row here is the idempotency check (FR-008); a second delivery with the same `event_id` short-circuits before any state mutation.
- **DeadLetterEvent** (plan, implements FR-009a): `event_id`, `event_type`, `account_id`, `line_id`, raw payload, `reason` (`UNKNOWN_ACCOUNT` | `UNKNOWN_LINE`), `logged_at`. A later resubmission with the same `event_id`, once the entity exists, is processed normally (not treated as a duplicate, since it never reached `ProcessedEvent`).

## StateTransitionLog (plan, implements FR-009/Constitution Principle VI)

- `id` (PK), `journey_id`, `line_id` (nullable), `entity_type` (`ACTIVITY_INSTANCE` | `ACCOUNT_JOURNEY` | `HEALTH_SCORE` | `NEXT_BEST_ACTION` | `ESCALATION_CASE`), `entity_id`, `before_state`, `after_state`, `triggering_event_id` (nullable), `occurred_at`, `correlation_id`.

## NextBestActionRecord (spec "NextBestAction")

- `id` (PK), `journey_id`, `line_id`, `action_code`, `priority` (int, per FR-011 base-priority table), `tie_break_rank` (int, per FR-012 order), `reason_codes` (JSON list), `message` (LLM-personalized text, nullable if `StubLLMProvider`/no personalization applied), `computed_at`, `superseded_at` (nullable — set when a later evaluation replaces this as the line's current NBA, preserving history for the audit trail/dashboard).

Computed per line (FR-010, per Clarifications Q2); the "current" NBA for a line is the latest non-superseded record.

## HealthScoreRecord (spec "HealthScore")

- `id` (PK), `journey_id`, `line_id` (nullable for account-level score), `score` (0-100, clamped), `band` (`GREEN` | `YELLOW` | `RED`), `reason_codes` (JSON list of `{code, deduction, label}`), `computed_at`.

Both a per-line and a per-account (aggregate) record are computed (FR-016, resolves checklist CHK025): the account-level score is the minimum of its lines' scores, so the account never reads healthier than its worst line.

## OutreachAttempt (spec)

- `id` (PK), `customer_id`, `line_id`, `next_best_action_id` (FK), `channel`, `attempted_at`, `status`: `DELIVERED` | `SUPPRESSED`, `suppression_reason` (nullable: `DAILY_CAP` | `WEEKLY_CAP` | `QUIET_HOURS` | `OPTED_OUT` | `ESCALATION_OPEN`).

`ESCALATION_OPEN` implements FR-028a; the daily/weekly cap counters (FR-014) only increment on `DELIVERED` attempts — a suppressed attempt does not consume a customer's contact-cap slot (resolves checklist CHK019 in the customer's favor: suppression is free).

## EscalationCase (spec)

- `case_id` (PK), `journey_id`, `line_id` (nullable), `reason` (enum: `EXPLICIT_REQUEST` | `UNSUPPORTED_LOW_CONFIDENCE` | `TWO_FAILED_TROUBLESHOOTING` | `UNRESOLVED_ACTIVATION_OR_PORT` | `BILLING_DISPUTE` | `SENSITIVE_ACCOUNT_SECURITY`), `priority`, `journey_snapshot` (JSON), `relevant_event_ids` (JSON list), `attempted_action_ids` (JSON list), `conversation_summary` (text, nullable if not chat-originated), `status`: `OPEN` | `RESOLVED` | `CLOSED`, `created_at`, `resolved_at` (nullable).

## ConsentPreference (spec)

- `customer_id` (PK), `opted_out`: bool, `updated_at`.

## BillingSnapshot / RenewalSnapshot (spec)

- **BillingSnapshot** (POSTPAID): `line_id`, `recurring_charges`, `one_time_charges`, `device_installment`, `taxes_fees`, `promotional_credits`, `cycle_start`, `cycle_end`, `fetched_at` (cache of `BillingProvider` output; the deterministic estimate shown to the customer is computed from these fields, never invented).
- **RenewalSnapshot** (PREPAID): `line_id`, `balance`, `renewal_date`, `data_allowance`, `auto_recharge_enabled`, `expiration_date`, `add_ons` (JSON), `fetched_at`.

## KnowledgeDocument (spec)

- `doc_id` (PK), `topic` (one of the 14 curated topics), `title`, `body` (markdown, source of truth in `knowledge_base/*.md`), `chroma_embedding_id` (FK-by-convention into the Chroma collection).

## RiskScoreSnapshot (spec)

- `id` (PK), `account_id` or `line_id`, `churn_score`, `call_likelihood_score`, `retail_visit_likelihood_score`, `adoption_score` (all 0-1 or 0-100, deterministic/mock), `computed_at`.

## DemoScenario (spec) — file-based, not a DB table

Each of the 11 scenarios is a JSON/YAML file under `seeds/scenarios/` containing: `scenario_id`, `title`, seeded `Account`/`Line`(s) with `plan_type`, a backdated `AccountJourney.started_at` (per `research.md §6`), an ordered list of pre-existing `DomainEvent`s to replay on load, and any seeded `ConsentPreference`/provider fixture overrides. `POST /api/demo/scenarios/{id}/reset` truncates all per-scenario tables and reloads exactly this file (implements FR-032, SC-011).

## ConversationSession / ConversationTurn (plan — required by User Story 4 AC5 and FR-024, not itemized in spec §Key Entities)

- **ConversationSession**: `session_id` (PK), `customer_id` (nullable if unauthenticated), `started_at`.
- **ConversationTurn**: `turn_id` (PK), `session_id` (FK), `role` (`user` | `concierge`), `text`, `retrieved_source_ids` (JSON list, populated when RAG was used — implements "RAG returns source metadata"), `troubleshooting_topic` (nullable — set when a turn attempts to resolve a specific issue, used to count "two unsuccessful troubleshooting attempts on the same issue" for FR-027), `resolved`: bool, `created_at`.

## Entity Relationship Summary

```text
Account 1──N Line
Account 1──1 AccountJourney (while ACTIVE)
AccountJourney 1──N LineOnboardingState
LineOnboardingState 1──N ActivityInstance (LINE-scoped) ; AccountJourney 1──N ActivityInstance (ACCOUNT-scoped)
AccountJourney/LineOnboardingState 1──N NextBestActionRecord, HealthScoreRecord, OutreachAttempt, EscalationCase
DomainEvent 1──0..1 ProcessedEvent ; DomainEvent 1──0..1 DeadLetterEvent
ConversationSession 1──N ConversationTurn
KnowledgeDocument N──N ConversationTurn (via retrieved_source_ids)
```
