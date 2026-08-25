<!--
Sync Impact Report
- Version change: [TEMPLATE] → 1.0.0 (initial ratification)
- Modified principles: none (first concrete version; template placeholders replaced)
- Added sections:
  - I. Deterministic Business Logic Before AI
  - II. Mock-First Integrations
  - III. Account-Level Journey With Line-Level State
  - IV. Privacy Boundary
  - V. Explainability
  - VI. Idempotent Event Processing and Auditable State Transitions
  - VII. Local-First Demo
  - VIII. Test Core Rules Before Polish
  - IX. Simple Architecture Over Microservices
  - X. Labeled Simulated Metrics
  - Governance (amendment procedure, versioning policy, compliance review)
- Removed sections: generic [SECTION_2_NAME]/[SECTION_3_NAME] template slots
  (not needed at this stage; no project-specific constraints beyond the
  10 principles were supplied)
- Templates requiring updates:
  - ✅ .specify/templates/plan-template.md — Constitution Check gate is
    generic ("[Gates determined based on constitution file]"), no edit needed
  - ✅ .specify/templates/spec-template.md — no principle-specific references
    present, no edit needed
  - ✅ .specify/templates/tasks-template.md — no principle-specific
    references present, no edit needed
  - ✅ .specify/templates/commands/*.md — directory does not exist, nothing
    to update
  - ⚠ README.md / docs/quickstart.md — do not exist yet; create during
    Principle VII (Local-First Demo) setup work and reference these
    principles then
- Follow-up TODOs: none blocking; ratification date set to today since this
  is the constitution's initial adoption in this repository
-->

# AI Concierge Constitution

## Core Principles

### I. Deterministic Business Logic Before AI
LLMs MUST NOT mutate journey state, calculate bills, bypass consent, choose
unsupported actions, or override escalation policy. Every state transition,
billing calculation, consent check, and escalation decision MUST be executed
by deterministic code that the LLM can call into and receive results from,
never logic the LLM performs itself inside a completion. The LLM's role is
limited to interpreting intent, selecting from an explicitly whitelisted set
of supported actions, and generating natural-language explanations of
decisions made by deterministic systems. Any action not on the whitelist MUST
be rejected before execution, regardless of how confidently the LLM proposes
it.
**Rationale**: Journey state, billing, consent, and escalation are the
system's trust boundaries. Non-deterministic components are unauditable and
unpredictable under adversarial or malformed input; keeping them out of these
paths is what makes the system safe to demo and safe to reason about under
time pressure.

### II. Mock-First Integrations
Every external dependency (billing systems, CRM, telephony, notifications,
or any third-party API) MUST be accessed through a provider interface, with a
seeded mock implementation provided and used by default. Real provider
implementations MAY be added behind the same interface, but the mock MUST
remain functional, deterministic, and the default for local development and
demos.
**Rationale**: A hackathon MVP cannot depend on live third-party
availability, credentials, or rate limits. Provider interfaces keep real
integrations swappable later without touching business logic, and seeded
mocks make every demo run reproducible.

### III. Account-Level Journey With Line-Level State
The onboarding journey is modeled as a single 30-day account-level journey,
composed of independently tracked line-level onboarding states for each line
on the account. Journey-level progress and health MUST be derived from
line-level state, never tracked as a separate, disconnected source of truth.
**Rationale**: Real accounts contain multiple lines that onboard at
different paces; collapsing them into one flat state would misrepresent
account health and produce incorrect next-best-action decisions.

### IV. Privacy Boundary
Access to customer-specific data (account details, billing, journey state,
line-level status) MUST require authenticated context. Generic guidance
(product information, general FAQs, non-account-specific help) MAY be served
without authentication. No code path may return customer-specific data as a
side effect of an unauthenticated request.
**Rationale**: Separating authenticated and generic paths keeps the privacy
boundary simple to reason about and simple to test, even under hackathon time
constraints.

### V. Explainability
Every health score and every next-best-action (NBA) decision MUST return
structured reason codes alongside the result. A score or recommendation
without an accompanying, machine-readable explanation of the factors that
produced it MUST NOT be surfaced to a user or another system.
**Rationale**: Reason codes make automated decisions auditable and let both
the demo audience and downstream code trust and debug the "why," not just the
"what."

### VI. Idempotent Event Processing and Auditable State Transitions
Event processing MUST be idempotent: replaying the same event MUST NOT
change system state beyond its first successful application. Every journey
or line state transition MUST be recorded as an auditable entry (actor,
trigger, before-state, after-state, timestamp) sufficient to reconstruct
history.
**Rationale**: Retries, replays, and duplicate webhooks are normal in
event-driven systems; idempotency and an audit trail keep state trustworthy
without requiring perfect delivery guarantees from upstream systems.

### VII. Local-First Demo
The full experience MUST run locally with documented setup and seeded demo
scenarios, without requiring live external services or network access to
third parties. Setup steps MUST be written down and kept current so the demo
can be reproduced from a clean checkout.
**Rationale**: A hackathon demo that depends on unreliable networks, live
credentials, or undocumented tribal-knowledge setup steps is a demo that
fails at the worst possible moment.

### VIII. Test Core Rules Before Polish
Core business rules (deterministic logic covered by Principle I, health
scoring, NBA selection, state transitions) and a curated set of end-to-end
scenarios MUST have test coverage before time is spent on visual or UX
polish. Polish work MUST NOT displace or delay this coverage.
**Rationale**: In a time-boxed build, correctness of the rules the whole
system depends on is worth more than surface finish, and untested business
logic is the most expensive kind of bug to discover live.

### IX. Simple Architecture Over Microservices
The MVP MUST be built as a modular monolith: internally organized into
clear, well-bounded modules, but deployed and run as a single service.
Splitting into separate services or microservices requires an explicit,
documented justification of a need that a module boundary cannot satisfy.
**Rationale**: Microservices trade simplicity for operational overhead
(deployment, networking, observability) that a hackathon MVP cannot afford;
module boundaries deliver most of the organizational benefit without that
cost, and remain refactorable later.

### X. Labeled Simulated Metrics
Any POCR/PORR (proactive outreach conversion rate / proactive outreach
resolution rate, or equivalent projected-impact) metric MUST be clearly and
visibly labeled as simulated or projected wherever it is displayed or
reported. Such metrics MUST NOT be presented, implied, or described as
measured causal reduction.
**Rationale**: These metrics are modeled estimates, not results from a
controlled experiment; mislabeling them as measured would misrepresent the
system's demonstrated impact.

## Governance

This constitution supersedes ad hoc practice for this project. All plans,
specs, and task lists MUST be checked against these principles at each
`/speckit.plan` Constitution Check gate before implementation proceeds; any
violation MUST be justified in that plan's Complexity Tracking table or the
plan MUST be revised to comply.

Amendments require: (1) the change written into this file, (2) the version
bumped per the semantic versioning policy below, (3) the Sync Impact Report
updated, and (4) propagation of any resulting changes to dependent templates
(`plan-template.md`, `spec-template.md`, `tasks-template.md`) in the same
change.

Versioning policy: MAJOR for backward-incompatible governance or principle
removals/redefinitions; MINOR for adding a new principle or materially
expanding guidance; PATCH for clarifications and non-semantic wording fixes.

**Version**: 1.0.0 | **Ratified**: 2026-08-24 | **Last Amended**: 2026-08-24
