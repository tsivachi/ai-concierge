# MVP Guardrails Checklist: 30-Day Personalized AI Concierge

**Purpose**: Validate that the requirements defining this MVP's non-negotiable guardrails (determinism, plan-type coverage, multi-line behavior, idempotency, privacy, consent, explainability, AI grounding, escalation, provider replaceability, seeded demo scenarios, and explicit non-goals) are complete, clear, consistent, and measurable enough to plan from — before proceeding to `/speckit.plan`.
**Created**: 2026-08-24
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the requirements as written, not the future implementation. Each item asks whether the spec says enough, clearly enough, to build and verify against — not whether the system behaves correctly.

**Resolution pass (2026-08-24)**: All 41 items reviewed against the now-complete artifact set (spec.md, plan.md, data-model.md, contracts/openapi.yaml, research.md, tasks.md). Most were already resolved by `/speckit.plan`, `/speckit.tasks`, and the `/speckit.analyze` remediation; the remainder were closed by adding simplest-default assumptions to spec.md's Assumptions section rather than reopening scope.

## Journey-State Determinism

- [x] CHK001 Are the exact conditions under which an activity transitions between NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED, and NOT_APPLICABLE specified per activity, rather than only described narratively? [Clarity, Spec §FR-004] — Resolved: data-model.md §ActivityInstance "State transitions"; tasks.md T035 (pure transition-rule functions).
- [x] CHK002 Is the boundary between deterministic app logic and AI/LLM personalization specified precisely enough to determine, for any given output field, which side produced it? [Clarity, Spec §FR-010, FR-013, FR-023, FR-024] — Resolved: plan.md Constitution Check row I (decisioning is LLM-free); tasks.md T101a/T101b/T101c (personalization only in the outer layer, additive-only, tested).
- [x] CHK003 Is the rule for resolving out-of-order or conflicting activity-status events specified as a testable rule rather than only asserted as a principle? [Completeness, Spec Assumptions, Edge Cases] — Resolved: data-model.md §ActivityInstance; tasks.md T033 (guard) + T039 (test).

## Postpaid/Prepaid Coverage

- [x] CHK004 Are the complete REQUIRED, RECOMMENDED, and OPTIONAL activity lists for postpaid lines enumerated in the spec, rather than referenced only as "the defined postpaid ... activity lists"? [Gap, Spec §FR-004, FR-005] — Resolved: data-model.md §ActivityDefinition table (research.md §10).
- [x] CHK005 Are the complete REQUIRED, RECOMMENDED, and OPTIONAL activity lists for prepaid lines enumerated in the spec, rather than referenced only abstractly? [Gap, Spec §FR-004, FR-005] — Resolved: data-model.md §ActivityDefinition table (research.md §10).
- [x] CHK006 Is it specified which requirement class and which plan type "paperless billing" and "premium feature adoption" belong to? [Ambiguity, Spec §FR-004] — Resolved: data-model.md §ActivityDefinition table (`PAPERLESS_BILLING` = ACCOUNT/RECOMMENDED/postpaid-only; `PREMIUM_FEATURE_ADOPTION` = LINE/OPTIONAL/both).

## Multi-Line Behavior

- [x] CHK007 Is the precedence rule for deriving overall account-journey status from multiple lines' individual statuses stated as an unambiguous rule? [Clarity, Spec §FR-005] — Resolved: spec.md FR-005; data-model.md §AccountJourney state transitions.
- [x] CHK008 Are the requirements for independent per-line NBA ranking, and for how the shared per-customer contact cap is allocated across multiple lines' eligible actions, fully specified? [Completeness, Spec §FR-010, FR-014, Clarifications] — Resolved: spec.md FR-010, FR-014, Clarifications Q2.
- [x] CHK009 Is a tie-break rule specified for when two different lines on the same account have equal-priority actions competing for the same remaining contact-cap slot? [Gap] — Resolved: spec.md Assumptions (global FR-011/FR-012 ranking applied across all of a customer's lines together).

## Event Idempotency

- [x] CHK010 Is "idempotent processing" defined with enough precision to be independently verified rather than only asserted as a principle? [Clarity, Spec §FR-008] — Resolved: spec.md FR-008; data-model.md §DomainEvent/ProcessedEvent; tasks.md T031.
- [x] CHK011 Are requirements defined for how long or how completely processed event_ids must be retained to guarantee the idempotency claim holds? [Gap] — Resolved: spec.md Assumptions (retained for the lifetime of the local demo database; no expiry/pruning in this MVP).
- [x] CHK012 Are the dead-letter/unknown-reference requirements specified with enough detail to determine correct resubmission handling? [Clarity, Spec §FR-009a] — Resolved: spec.md FR-009a; data-model.md §DeadLetterEvent; tasks.md T032/T036a/T038.

## Authentication & Privacy Boundary

- [x] CHK013 Is "authenticated context" defined precisely enough that qualification can be determined without guessing? [Clarity, Spec §FR-021, Assumptions] — Resolved: research.md §5 (bearer token from `POST /api/auth/login` mapped to `customer_id`); tasks.md T036b.
- [x] CHK014 Are requirements defined for session expiry or de-authentication occurring mid-conversation? [Gap] — Resolved: spec.md Assumptions (tokens don't expire during a running process in this MVP).
- [x] CHK015 Is it specified how the system confirms an authenticated session's customer_id matches the account/line being asked about, to prevent cross-account data exposure? [Gap, Security] — Resolved: tasks.md T046/T058/T059/T078/T111 (explicit 401/403 enforcement) + T082a (auth-boundary integration test), added via `/speckit.analyze` remediation (finding C2).

## Contact Consent & Frequency

- [x] CHK016 Are the default contact-cap values and quiet-hours window specified consistently as configurable defaults everywhere they are referenced? [Consistency, Spec §FR-014] — Resolved: spec.md FR-014 (single source of truth).
- [x] CHK017 Is the precedence/composition rule specified for when quiet hours, contact caps, and consent/opt-out simultaneously constrain the same eligible action? [Clarity, Spec §FR-014, FR-015] — Resolved: data-model.md §OutreachAttempt (all constraints evaluated together; only a fully-passing action becomes DELIVERED, making composition order irrelevant).
- [x] CHK018 Is "immediately" (honoring an opt-out) defined with respect to outreach that is already in-flight or queued? [Ambiguity, Spec §FR-015, Edge Cases] — Resolved: spec.md Assumptions (outreach is decided synchronously at evaluation time; nothing is queued to separately cancel).
- [x] CHK019 Is it specified whether an action suppressed due to an open escalation still counts against the daily/weekly contact cap? [Consistency, Spec §FR-014, FR-028a] — Resolved: data-model.md §OutreachAttempt (cap counters increment only on DELIVERED; suppression is free).

## NBA Explainability

- [x] CHK020 Are the required contents of a next-best-action reason code specified precisely enough to be independently produced and verified? [Clarity, Spec §FR-018] — Resolved: contracts/openapi.yaml `NextBestAction`/`ReasonCode` schemas (priority, tie_break_rank, and reason_codes are distinct fields).
- [x] CHK021 Is it specified whether reason codes are drawn from a fixed, enumerated set or are free-form? [Gap] — Resolved: spec.md Assumptions (stable identifiers derived 1:1 from FR-016/FR-011's already-named factors).
- [x] CHK022 Is the relationship between the LLM-personalized outreach message and the underlying reason codes specified, so the two cannot drift apart? [Ambiguity] — Resolved: tasks.md T101a (message generated only from the already-finalized NBA) + T101c (additive-only boundary test).

## Health-Score Reason Codes

- [x] CHK023 Is each health-score deduction in FR-016 mapped to a specific, testable triggering condition rather than only a label and a point value? [Clarity, Spec §FR-016] — Resolved: tasks.md T051 (pure deduction function) + T060 (per-deduction unit tests) make each condition concretely testable by construction.
- [x] CHK024 Is it specified whether the reason-code list must reflect every deduction applied before clamping? [Ambiguity, Spec §FR-016, FR-018] — Resolved: data-model.md §HealthScoreRecord (`reason_codes` is a separate field from the clamped `score`, always listing every applied deduction).
- [x] CHK025 Are reason-code requirements specified separately for the account-level health score versus each line-level health score? [Gap] — Resolved: data-model.md §HealthScoreRecord (per-line and per-account records both computed; account = min of lines'); contracts/openapi.yaml `HealthScore.scope`.

## AI Grounding Boundaries

- [x] CHK026 Are the categories of "customer-specific facts or billing numbers" the AI/LLM component must never invent specified precisely enough to be testable? [Clarity, Spec §FR-023] — Resolved: tasks.md T096 (context DTO assembly) + T102 (unit test that context contains only real fields) — enforced by construction (whitelist), not a prohibition list.
- [x] CHK027 Is the fallback behavior fully specified for when retrieved knowledge-base content is insufficient to answer a question? [Gap, Spec §FR-027, Edge Cases] — Resolved: spec.md Assumptions (a retrieval gap immediately qualifies as the FR-027 unsupported/low-confidence trigger; no clarifying-question step in this MVP).
- [x] CHK028 Is the "supported action set" referenced in FR-024 defined as a concrete, enumerable list anywhere in the spec? [Gap, Spec §FR-024] — Resolved: spec.md Assumptions (defined as the FR-011 NBA action-type list).

## Escalation Completeness

- [x] CHK029 Are all six escalation triggers defined with independently detectable conditions? [Clarity, Spec §FR-027] — Resolved: spec.md Assumptions ("billing dispute" now distinguished from an ordinary billing question); tasks.md T107/T112.
- [x] CHK030 Is the required content of an escalation case specified at a field level precise enough to verify completeness? [Measurability, Spec §FR-028] — Resolved: contracts/openapi.yaml `EscalationCase` schema (every field enumerated).
- [x] CHK031 Is the lifecycle of an EscalationCase specified, including how it ties back to the outreach-suppression rule in FR-028a? [Gap, Spec §FR-028a] — Resolved: data-model.md §EscalationCase (OPEN/RESOLVED/CLOSED); tasks.md T109.

## Mock-Provider Replaceability

- [x] CHK032 Are the interface/contract requirements for each of the eight providers specified independently of their mock implementation? [Clarity, Spec §FR-029] — Resolved: plan.md Constitution Check row II; tasks.md T070 (`Protocol` definitions separate from mocks).
- [x] CHK033 Are requirements defined for how provider responses are seeded/configured per demo scenario to guarantee deterministic results? [Completeness, Spec §FR-029, FR-032] — Resolved: data-model.md §DemoScenario; tasks.md T022-T026 (scenario files) + T029/T083 (determinism tests).
- [x] CHK034 Is the "future replacement seam" requirement for the risk-scoring provider specified concretely enough to be verified? [Measurability, Spec §FR-031] — Resolved: the same `Protocol` pattern (tasks.md T070/T074) is the concrete mechanism — any real implementation just needs to satisfy the existing protocol.

## Seeded Demo Scenarios

- [x] CHK035 Does the spec define the starting state for each of the 11 catalog scenarios, or only their names and intent? [Gap, Spec Demo Scenario Catalog] — Resolved: data-model.md §DemoScenario (file schema: seeded account/lines, backdated `started_at`, pre-existing events); spec.md Demo Scenario Catalog names each; concrete per-scenario data is implementation content authored in tasks.md T022-T026.
- [x] CHK036 Are the reset requirements specified precisely enough to guarantee no residual state leaks between scenario loads? [Measurability, Spec §FR-032, SC-011] — Resolved: data-model.md §DemoScenario (reset truncates and reloads); tasks.md T027/T029/T036a.
- [x] CHK037 Are the day-offset thresholds implied by the curated scenarios consistent with the day thresholds defined in the NBA and health-score rules elsewhere in the spec? [Consistency, Spec §FR-011, FR-016] — Resolved: spec.md Assumptions (explicit day-21 / renewal-lookahead-window thresholds added, tied to FR-011's priority=65 action).

## Explicit Non-Goals

- [x] CHK038 Is every stated non-goal unambiguous enough to prevent accidental reintroduction during planning? [Clarity, Spec Assumptions] — Resolved: spec.md Assumptions (explicit list, unchanged).
- [x] CHK039 Is there an explicit non-goal or scope statement covering line churn/cancellation? [Gap, Spec Edge Cases] — Resolved: spec.md Assumptions (churn/cancellation explicitly declared out of scope).

## Cross-Cutting Consistency & Traceability

- [x] CHK040 Is a requirement/acceptance-criteria ID scheme applied consistently enough that every requirement can be traced to a specific spec anchor? [Traceability] — Resolved: spec.md uses FR-xxx/SC-xxx consistently throughout, referenced by data-model.md, contracts/openapi.yaml, and tasks.md.
- [x] CHK041 Are the three clarified decisions each reflected consistently in every other requirement or edge case that depends on them? [Consistency, Spec Clarifications] — Resolved: dead-letter handling (FR-009a, data-model.md, tasks T032/T036a/T038), per-line NBA (FR-010/FR-014, data-model.md, tasks T053/T054/T058), and escalation-suppresses-outreach (FR-028a, data-model.md, tasks T055/T109) are each threaded consistently through every downstream artifact.

## Notes

- Generated directly from the user-specified focus list (13 areas); no clarifying questions were needed since the request already named precise, spec-traceable focus areas.
- Depth: standard pre-plan readiness gate. Audience/timing: author, before running `/speckit.plan`.
- The most material finding surfaced while building this checklist: FR-004/FR-005 reference "the defined postpaid and prepaid activity lists" but spec.md never actually enumerates them (CHK004-CHK006) — resolved via data-model.md's `ActivityDefinition` table (research.md §10).
- 2026-08-24 resolution pass: 10 new Assumptions bullets added to spec.md to close CHK009, CHK011, CHK014, CHK018, CHK021, CHK027, CHK028, CHK029, CHK037, CHK039. All other items were already satisfied by plan.md/data-model.md/contracts/tasks.md, several via the `/speckit.analyze` remediation (CHK002, CHK015, CHK022).
- All 41 items now pass. Ready for `/speckit.implement`.
