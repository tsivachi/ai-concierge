# Feature Specification: 30-Day Personalized AI Concierge

**Feature Branch**: `001-ai-onboarding-concierge`
**Created**: 2026-08-24
**Status**: Draft
**Input**: User description: "Build a hackathon MVP named \"30-Day Personalized AI Concierge\" for new POSTPAID and PREPAID wireless line activations. Reverse the current support model: instead of waiting for a new wireless customer to call support or visit retail, maintain a personalized 30-day onboarding journey, detect friction, select the next best action, proactively guide the customer digitally, resolve common onboarding/billing/setup issues, and escalate with context when required. Demonstrate potential reduction opportunities in post-online call rate (POCR) and post-online retail rate (PORR)." (expanded with journey/activity model, event catalog, next-best-action rules, health scoring, an AI concierge with RAG over curated wireless knowledge, billing/renewal explanation, proactive issue detection, escalation policy, provider abstractions, a mock risk-scoring seam, a demo UI, an aggregate dashboard, and 11 curated demo scenarios)

## Clarifications

### Session 2026-08-24

- Q: When an event arrives referencing an account_id/line_id with no matching journey (e.g., delivered before OrderCompleted, or a bad ID), what should happen? → A: Log the event to an audit/dead-letter record and drop it (no state change); if the entity appears later, a resubmitted event would be processed normally.
- Q: On a multi-line account, can two different lines each generate and proactively deliver their own next best action on the same day (up to the shared cap), or is there always a single account-wide NBA? → A: Rank candidates independently per line; each line can have its own current NBA, and outreach draws from all lines' eligible actions, subject to the shared per-customer daily/weekly cap.
- Q: Once an issue on a line has an open EscalationCase, should the concierge keep generating/delivering proactive outreach for that same underlying issue? → A: Suppress — no further proactive outreach is generated for that same NBA/issue on that line until the case is resolved/closed.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guided Activation to Onboarding Completion (Priority: P1)

A customer who just purchased a new postpaid or prepaid wireless line — whether a new device with a ported-in number, a bring-your-own-device eSIM activation, or a multi-line postpaid account — is automatically enrolled in a 30-day onboarding journey the moment their order completes. As they activate their SIM/eSIM, transfer their number (if applicable), and their device connects to the network, the concierge tracks each required step per line, proactively nudges them toward whichever step is next, and confirms completion once every required activity for every line on the account is done.

**Why this priority**: This is the foundational golden path. Without a working journey that enrolls a customer and tracks required activities to completion per line, there is nothing to detect friction against, rank actions for, explain via the concierge, or escalate — every other capability builds on this one.

**Independent Test**: Can be fully tested by completing an order for a single-line postpaid account with number port, a single-line prepaid BYOD/eSIM account, and a multi-line postpaid account, sending the corresponding activation/network/security events for each, and verifying each journey reaches onboarding completion with no required activity left incomplete — deliverable and demoable on its own.

**Acceptance Scenarios**:

1. **Given** a customer completes an order for a new postpaid line with a number port request, **When** the order-completed event is received, **Then** a 30-day AccountJourney is created for the account, a line-level onboarding state is created for that line, and all required and applicable recommended/optional postpaid activities are initialized as NOT_STARTED, including a number-transfer activity.
2. **Given** a customer completes an order for a new prepaid BYOD line activating via eSIM with no number port, **When** the order-completed event is received, **Then** the line's number-transfer activity is initialized as NOT_APPLICABLE and does not block completion, while SIM/eSIM activation, network validation, and account security remain REQUIRED.
3. **Given** an account journey with a line whose SIM/eSIM activation is NOT_STARTED, **When** device activation start and completion events arrive for that line, **Then** the line's activation activity transitions NOT_STARTED → IN_PROGRESS → COMPLETED.
4. **Given** an account with two or more postpaid lines, **When** one line finishes all required activities but another still has an incomplete required activity, **Then** the account journey overall status remains incomplete while each line's own status accurately reflects its individual progress.
5. **Given** an account where every line has completed all of its required, applicable activities, **When** the last required activity completes, **Then** the account journey is marked onboarding-complete.

---

### User Story 2 - Friction Detection, Proactive Resolution, and Contextual Escalation (Priority: P2)

When a customer's onboarding hits friction — a failed activation, a stalled or failed number transfer, repeated visits to help content, an abandoned setup step, or repeated chat sessions on the same unresolved topic — the concierge detects it, determines it is the most urgent thing to address, proactively reaches out (within consent, contact-frequency, and quiet-hours limits) with a specific next best action, and offers a digital resolution path. If the issue meets one of the defined escalation triggers, the concierge escalates to a human agent with full context — including journey state, relevant events, attempted actions, and a conversation summary — so the customer never has to re-explain what already happened. A customer may also opt out of proactive contact at any time, which the concierge must honor immediately.

**Why this priority**: Friction detection paired with proactive, digitally-resolved intervention and well-contextualized escalation is the core mechanism that reduces post-online call rate (POCR) and post-online retail rate (PORR) — the business outcome this MVP exists to demonstrate. It depends on User Story 1's journey/activity tracking already existing.

**Independent Test**: Can be fully tested by seeding a journey already in progress and independently exercising: (a) a device-activation failure repeated across attempts, (b) a delayed/failed number transfer, (c) repeated help-article views or repeated chat starts on the same topic, (d) an abandoned setup step, (e) an explicit customer opt-out, and (f) an escalation trigger — verifying in each case that the concierge surfaces the correctly-ranked next best action, respects contact governance, and (where applicable) produces a complete escalation case.

**Acceptance Scenarios**:

1. **Given** a line's device activation fails, **When** the failure event is processed, **Then** the line's activation activity is marked FAILED, the line's health score is recalculated with reason codes reflecting the failure, and a next best action with the highest available priority is generated for that line.
2. **Given** a line's device activation fails repeatedly, **When** each subsequent failure event is processed, **Then** the health-score deduction and next-best-action urgency for that line do not decrease, and the repeated-failure pattern is retained as context available to escalation.
3. **Given** a number transfer stays in a pending state beyond the configured threshold, or a number-transfer-failed event is received, **When** the journey is evaluated, **Then** the affected line's health score reflects a "port pending too long" or transfer-failure deduction and a correspondingly prioritized next best action is generated.
4. **Given** a customer has an unresolved number-transfer failure and an app-adoption gap open at the same time, **When** the next best action is selected, **Then** the number-transfer failure is chosen over the app-adoption gap, consistent with the defined tie-break order (critical issue > required setup > billing/renewal > digital adoption > optional adoption).
5. **Given** a customer views help articles on the same unresolved topic multiple times, or starts multiple chat sessions on the same unresolved topic, **When** the repeat threshold is crossed, **Then** the line/account health score reflects the corresponding "repeated help visits" or "unresolved repeated chats" deduction with reason codes.
6. **Given** a customer abandons an in-progress setup step, **When** the setup-abandoned event is received, **Then** the affected activity remains in its current non-terminal status and the abandonment is available as detection context for next-best-action and health scoring.
7. **Given** a next best action exists for a customer who has not opted out and is within contact limits, **When** proactive outreach is due, **Then** the concierge delivers a personalized message recommending that action, and the attempt is logged.
8. **Given** a customer has already received the maximum number of proactive contacts allowed for the day, or the current time falls within quiet hours, **When** another action becomes eligible for outreach, **Then** delivery is deferred until a permitted window rather than exceeding the cap or contacting during quiet hours.
9. **Given** a customer opts out of proactive contact, **When** any next best action becomes eligible (before or after the opt-out), **Then** no proactive outreach is delivered to that customer going forward, and the suppression is recorded.
10. **Given** any of the defined escalation triggers occurs — explicit request for a human, an issue the concierge cannot map to supported knowledge or actions, two unsuccessful troubleshooting attempts on the same issue, an unresolved activation or port failure, a billing dispute, or a sensitive account/security request — **When** the trigger condition is met, **Then** an escalation case is created containing the reason, a priority, the customer's current journey/line state, relevant event history, prior attempted actions, and a summary of the conversation, so a human agent has full context without asking the customer to repeat information.
11. **Given** an event for a line or account that has already been processed (duplicate delivery), **When** the same event is received again, **Then** the journey, activity, health-score, and next-best-action state are unchanged from their state after the first processing.

---

### User Story 3 - Digital Adoption Nudges and Billing/Renewal Readiness (Priority: P3)

Beyond resolving problems, the concierge proactively nudges the customer toward recommended and optional setup — like AutoPay or auto-recharge, the mobile app, voicemail, paperless billing — timed to when each nudge becomes relevant, and helps the customer understand what is coming: a postpaid customer approaching their first bill sees a plain-language breakdown of what to expect, and a prepaid customer approaching renewal sees their balance, renewal date, and auto-recharge readiness explained in plain language.

**Why this priority**: Adoption nudges and billing/renewal education raise the health score and completeness of the journey and materially inform the POCR/PORR reduction story (fewer "why is my bill higher" or "did my renewal go through" contacts), but the MVP is still valuable and demoable with just critical-issue handling (User Story 2) if this story is deferred.

**Independent Test**: Can be fully tested by seeding a journey past the relevant day thresholds (e.g., day 8 with no AutoPay/auto-recharge, day 4 with no app download, day 21 for a postpaid line approaching its first bill, and a prepaid line approaching its renewal date) and verifying the correctly-prioritized nudge or readiness explanation is produced, and that completing the underlying action (e.g., an AutoPayEnabled event) updates the activity and health score accordingly.

**Acceptance Scenarios**:

1. **Given** a postpaid line at day 8 of its journey with no AutoPay configured, **When** next best actions are evaluated, **Then** an AutoPay-setup action is generated at its defined priority, ranked below any open critical issue but above app/voicemail gaps under the tie-break order.
2. **Given** a prepaid line at day 4 with the mobile app not yet downloaded, **When** next best actions are evaluated, **Then** an app-adoption action is generated only once the app-gap day threshold has passed, not before.
3. **Given** a customer completes an AutoPay enrollment after receiving the nudge, **When** the AutoPayEnabled event is processed, **Then** the corresponding recommended activity is marked COMPLETED, the related health-score deduction is removed, and the next best action for that gap no longer appears.
4. **Given** a postpaid line approaching day 21 of its journey, **When** first-bill readiness is evaluated, **Then** the concierge produces a plain-language estimate of the upcoming bill (recurring charges, one-time charges, device installment, taxes/fees, and any promotional credits) derived from provider-supplied billing facts, clearly distinguished from a final bill amount.
5. **Given** a prepaid line approaching its plan renewal date, **When** renewal readiness is evaluated, **Then** the concierge presents the current balance, renewal date, data allowance, and auto-recharge state, and flags whether the line is ready for renewal.
6. **Given** a line has completed all required activities but has open recommended/optional gaps, **When** the journey is evaluated, **Then** onboarding completion for that line is still recognized (recommended/optional items do not block completion), while the health score and next best actions continue to reflect the open gaps.

---

### User Story 4 - Authenticated Contextual Troubleshooting via the Concierge (Priority: P4)

An authenticated customer can ask the concierge free-form questions about their own onboarding — "why isn't my number transfer done," "what does my next step mean," "help me fix my activation" — and receive an answer that combines their actual journey context (customer type, plan/device, line state, journey day, activity statuses, current next best action, health-score reasons, billing/renewal facts, and recent support context) with guidance retrieved from a curated wireless knowledge base, without the answer inventing facts about the customer's account or bill, changing their journey state, bypassing their consent settings, or proposing an action the system doesn't actually support.

**Why this priority**: Contextual AI troubleshooting is what makes the concierge feel personalized rather than generic, and demonstrates the safe use of AI directly against the deterministic core (Users Stories 1-3). It depends on those stories for the context it explains and is deferrable relative to them since a working journey/NBA/escalation system already demonstrates the core business outcome without it.

**Independent Test**: Can be fully tested by authenticating as a seeded customer with a known journey state and asking questions that require (a) explaining the current next best action, (b) retrieving general troubleshooting guidance relevant to their situation, and (c) attempting to ask the concierge to directly change journey state or invent a billing number — verifying the first two produce grounded, context-correct answers and the third is refused/redirected to a supported path.

**Acceptance Scenarios**:

1. **Given** an authenticated customer with an open next best action, **When** they ask the concierge to explain it, **Then** the response accurately reflects that action's reason codes and priority without contradicting the deterministically computed state.
2. **Given** an authenticated customer asks a troubleshooting question covered by the curated knowledge base (e.g., eSIM setup, porting, voicemail, AutoPay, auto-recharge, device protection, network troubleshooting, international usage), **When** the concierge answers, **Then** the response is grounded in retrieved knowledge-base content relevant to the question and to the customer's actual line/plan type.
3. **Given** an authenticated customer asks the concierge a question implying a specific billing number or account fact the system has not retrieved from a provider, **When** the concierge responds, **Then** it does not fabricate that number or fact, and instead relies only on provider-supplied data or states the information is unavailable.
4. **Given** an authenticated customer asks the concierge to perform an action outside the supported action set (e.g., an unsupported request), **When** the concierge responds, **Then** it does not claim to have performed the action and instead offers a supported alternative or escalation path.
5. **Given** a customer has two unsuccessful troubleshooting attempts on the same issue within a conversation, **When** the second attempt fails to resolve it, **Then** the concierge triggers escalation with a summary of what was already tried.

---

### User Story 5 - Unauthenticated Generic Concierge Help (Priority: P5)

A visitor with general wireless questions (e.g., how activation works, what a number transfer is, how eSIM setup works) can get helpful, knowledge-grounded answers from the concierge without signing in, while any request for account-specific information is declined and redirected to authentication.

**Why this priority**: This demonstrates the privacy boundary and broadens the demo's audience, but it is the smallest, most self-contained slice and the least central to the POCR/PORR business outcome relative to the authenticated stories above.

**Independent Test**: Can be fully tested by asking a generic wireless question with no authenticated session and confirming a helpful, knowledge-grounded, non-account-specific answer is returned, then asking an account-specific question in the same unauthenticated session and confirming it is declined with a prompt to authenticate.

**Acceptance Scenarios**:

1. **Given** no authenticated session, **When** a visitor asks a generic wireless question (e.g., "how do I activate my eSIM?"), **Then** the concierge answers using the curated knowledge base and does not request or reveal any customer-specific account data.
2. **Given** no authenticated session, **When** a visitor asks a question that requires customer-specific data (e.g., "is my line activated?"), **Then** the concierge declines to provide account-specific information and prompts the visitor to authenticate.

---

### User Story 6 - Demo Control and Aggregate Outcome Dashboard (Priority: P6)

A reviewer running the demo can select and reset curated scenarios, inject events to drive a journey forward, and watch the account's journey, line activities, health score with reasons, and current next best action update live. The reviewer can also open an aggregate dashboard summarizing enrolled customers, engagement, onboarding completion, digital resolutions, escalations, and the simulated/projected POCR and PORR intervention opportunities the concierge would represent, with those projected figures clearly and visibly labeled as simulated rather than measured.

**Why this priority**: This is the presentation layer that ties Users Stories 1-5 together into a demonstrable, reviewable hackathon experience. It depends on those stories producing real state to display and is last because it adds no new business logic of its own.

**Independent Test**: Can be fully tested by loading each of the 11 curated demo scenarios in turn, resetting between them, injecting the scenario's events, and confirming the journey/health/NBA views update correctly and the dashboard reflects the resulting counts with POCR/PORR figures visibly labeled as simulated/projected.

**Acceptance Scenarios**:

1. **Given** a reviewer selects a curated demo scenario, **When** the scenario loads, **Then** the account, its line(s), and their journey are seeded to that scenario's defined starting state.
2. **Given** a loaded scenario, **When** the reviewer injects one of the supported event types, **Then** the journey, activity statuses, health score, and next best action update and are visible without a page reload or manual refresh step beyond normal interaction.
3. **Given** a reviewer resets the demo, **When** the reset completes, **Then** all seeded scenario state is cleared back to its defined starting point.
4. **Given** any dashboard view showing POCR or PORR intervention figures, **When** the dashboard is displayed, **Then** those figures are visibly labeled as simulated/projected hackathon metrics, not measured results.

---

### Edge Cases

- What happens when an account has multiple lines with different plan types (e.g., one postpaid, one prepaid)? Required/recommended/optional activities are evaluated per line based on that line's own type.
- How does the system handle a device-activation failure event that arrives after a device-activation-completed event for the same line (out-of-order delivery)? Processing must not regress a line from COMPLETED back to FAILED without a clear terminal-state rule.
- An event referencing a line_id or account_id with no matching journey (e.g., arrives before OrderCompleted, or references an unknown account) is logged to an audit/dead-letter record and dropped without changing any state; a later resubmission of the same event, once the entity exists, is processed normally.
- What happens when the 30-day journey window elapses with required activities still incomplete — does the journey close, expire, or continue tracking past day 30?
- How are proactive contact caps (2/day, 5/week) and quiet hours (10 PM-8 AM local) enforced when multiple next best actions are eligible for the same customer at once — which one, if any, is sent?
- What happens when a customer opts out mid-journey after already having open next best actions — are already-scheduled outreach attempts cancelled?
- What counts as "repeated" help visits or chats for health-score and escalation purposes — same topic more than once within the active journey, within some window?
- What happens when the concierge cannot find relevant knowledge-base content for a question (a retrieval gap) — is that treated as a "low-confidence/unsupported issue" escalation trigger?
- How does billing/renewal readiness behave for a line that churns out or cancels before day 21 or before its renewal date?
- How does the concierge behave when an authenticated customer's account has no active journey (e.g., journey already completed or past day 30)?
- What happens when a demo scenario is loaded while another scenario's state is still active — is an implicit reset required first?

## Demo Scenario Catalog *(hackathon walkthrough)*

These curated scenarios are the acceptance surface a reviewer will exercise end-to-end; each maps to the user stories above.

| # | Scenario | Primarily Exercises |
|---|----------|----------------------|
| 1 | New postpaid device + port-in | User Story 1 |
| 2 | New prepaid BYOD + eSIM | User Story 1 |
| 3 | Multi-line postpaid account | User Story 1 |
| 4 | Repeated activation failure | User Story 2 |
| 5 | Delayed/failed number transfer | User Story 2 |
| 6 | App adoption gap after day 3 | User Story 3 |
| 7 | Postpaid day-21 first-bill education | User Story 3 |
| 8 | Prepaid renewal approaching | User Story 3 |
| 9 | Contextual AI troubleshooting | User Story 4 |
| 10 | Human escalation with context | User Story 2 / User Story 4 |
| 11 | Customer opt-out | User Story 2 |

## Requirements *(mandatory)*

### Functional Requirements

**Enrollment & Journey Structure**

- **FR-001**: System MUST create exactly one 30-day AccountJourney per qualifying account/order context when an OrderCompleted event is received for a new postpaid or prepaid wireless line.
- **FR-002**: System MUST attach a line-level onboarding state to its account's journey for every wireless line included in the qualifying order, and MUST support multiple lines attaching to the same account journey.
- **FR-003**: System MUST scope each onboarding activity as either ACCOUNT-level or LINE-level, and MUST evaluate LINE-level activities independently per line based on that line's own postpaid/prepaid type.
- **FR-004**: System MUST track each activity instance using the status values NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED, and NOT_APPLICABLE, and MUST classify each activity as REQUIRED, RECOMMENDED, or OPTIONAL per the defined postpaid and prepaid activity lists.
- **FR-005**: System MUST mark a line's onboarding complete only when every REQUIRED activity applicable to that line reaches COMPLETED or NOT_APPLICABLE, and MUST mark the account journey onboarding-complete only when this holds for every line on the account; RECOMMENDED and OPTIONAL activities MUST NOT block completion.

**Event Processing**

- **FR-006**: System MUST accept and process, at minimum, the following event types: OrderCompleted, DeviceDelivered, DeviceActivationStarted, DeviceActivationCompleted, DeviceActivationFailed, NumberTransferRequested, NumberTransferPending, NumberTransferCompleted, NumberTransferFailed, CustomerLoggedIn, MobileAppDownloaded, VoicemailConfigured, AutoPayEnabled, AutoRechargeEnabled, HelpArticleViewed, SetupAbandoned, ChatStarted, and SupportCaseCreated.
- **FR-007**: System MUST require every event to carry an event_id, event_type, customer_id, account_id, occurred_at timestamp, source, and correlation_id, and MAY carry a line_id and/or journey_id when known.
- **FR-008**: System MUST process each event idempotently, such that receiving the same event_id more than once produces no additional change to journey, activity, health-score, or next-best-action state beyond its first successful application.
- **FR-009**: System MUST record every activity status change and health/NBA-affecting event as an auditable entry sufficient to reconstruct, for any journey, the full sequence of what happened and why.
- **FR-009a**: System MUST, when an event references an account_id or line_id with no matching journey, record the event to an audit/dead-letter record without applying any state change, and MUST process a later resubmission of that same event normally once the referenced entity exists.

**Next Best Action**

- **FR-010**: System MUST determine next-best-action eligibility and ranking independently per line, using deterministic rules based on that line's activity state and elapsed journey days; a multi-line account MAY therefore have a distinct current next best action per line at the same time. An AI/LLM component MUST NOT decide eligibility, priority, or which action is selected.
- **FR-011**: System MUST apply the defined base priority values for each action type (activation failure=100, number-transfer failure=95, network failure=90, required security incomplete=70, billing/renewal readiness=65, payment/AutoPay/auto-recharge gap after day 7=60, app gap after day 3=50, voicemail gap after day 5=40, protection decision after day 10=30, premium feature=20) when ranking eligible actions.
- **FR-012**: System MUST break ties between equal-priority eligible actions using the defined order: critical issue > required setup > billing/renewal > digital adoption > optional adoption.
- **FR-013**: System MAY use an AI/LLM component to personalize the wording of a next best action's message, but the underlying action selection and priority MUST already be finalized by deterministic logic before the LLM is invoked.
- **FR-014**: System MUST enforce configurable proactive contact limits (default: maximum 2 contacts per day and 5 per week per customer, shared across all of that customer's lines) and MUST NOT deliver proactive outreach during configured quiet hours (default: 10 PM-8 AM local time); when multiple lines on the same account have eligible next best actions, outreach MUST draw from across all lines' eligible actions in priority order until the shared cap is reached.
- **FR-015**: System MUST suppress all proactive outreach to a customer who has not consented or who has opted out, regardless of action urgency, and MUST record that the suppression occurred and honor an opt-out immediately, including for already-eligible actions.

**Health Score**

- **FR-016**: System MUST compute each line's and/or account's health score starting from 100 and applying the defined deductions (activation incomplete -30, activation failure -25, port pending too long -20, repeated help visits -10, unresolved repeated chats -10, required setup incomplete -10, setup step abandoned -10, app not adopted -5, AutoPay/auto-recharge incomplete -5), clamped to the 0-100 range.
- **FR-017**: System MUST classify the clamped health score into GREEN (75-100), YELLOW (40-74), or RED (0-39).
- **FR-018**: System MUST return machine-readable reason codes alongside every health score and every next-best-action decision, identifying which specific factors contributed and how the action was prioritized against other eligible actions.

**Proactive Issue Detection**

- **FR-019**: System MUST detect, at minimum, the following friction patterns and factor each into health score and next-best-action eligibility: device activation failure, delayed or failed number transfer, repeated help-article views on the same unresolved topic, abandoned setup steps, and repeated chat sessions on the same unresolved topic.

**AI Concierge & Retrieval-Augmented Guidance**

- **FR-020**: System MUST allow generic, non-account-specific wireless guidance to be served without authentication, grounded in a curated wireless knowledge base covering at minimum: activation, eSIM/SIM, porting, voicemail, the mobile app, account security, billing, first-bill education, AutoPay, auto-recharge, device protection, network troubleshooting, plan/data usage, international usage, and prepaid renewal.
- **FR-021**: System MUST require authenticated context to access or return any customer-specific data or explanation, including account details, line status, journey state, health score, next-best-action detail, or billing/renewal facts tied to a specific customer or account, and MUST NOT allow an unauthenticated interaction to reveal or infer such data.
- **FR-022**: System MUST assemble authenticated concierge context from the customer's actual current state — customer type, plan/device, line state, journey day, activity statuses, current next best action, health-score reasons, billing/renewal facts, and recent support context — rather than relying on the AI component to infer or recall it.
- **FR-023**: System MUST prevent the AI/LLM component from inventing customer-specific facts or billing numbers not supplied by a provider or the assembled context; any such answer MUST be grounded in retrieved knowledge and/or provider-supplied data, or MUST state the information is unavailable.
- **FR-024**: System MUST prevent the AI/LLM component from mutating journey state, overriding consent/opt-out settings, or proposing/executing an action outside the deterministically defined supported action set; the AI/LLM component's role is limited to explaining decisions already made deterministically, answering with retrieved knowledge, personalizing outreach wording, guiding pre-approved troubleshooting steps, and summarizing context for escalation.

**Billing & Renewal**

- **FR-025**: System MUST, for postpaid lines, deterministically compute a plain-language bill estimate (recurring charges, one-time charges, device installment, taxes/fees, promotional credits, and cycle dates) from provider-supplied billing facts, and MUST have the AI/LLM component explain that already-computed estimate rather than calculate it.
- **FR-026**: System MUST, for prepaid lines, present renewal readiness (current balance, plan renewal date, data allowance, auto-recharge state, and expiration/add-on information) from provider-supplied facts, and MUST have the AI/LLM component explain renewal readiness rather than compute it.

**Escalation**

- **FR-027**: System MUST trigger escalation to a human agent when any of the following occurs: an explicit customer request for a human; an issue the concierge cannot resolve with supported knowledge or actions (low-confidence/unsupported); two unsuccessful troubleshooting attempts on the same issue; an unresolved activation or number-transfer failure; a billing dispute; or a sensitive account/security request.
- **FR-028**: System MUST create an escalation case containing the escalation reason, a priority, the customer's current journey/line state, relevant event history, prior attempted next-best-action/troubleshooting actions, and a conversation summary, so a human agent does not require the customer to repeat context already known to the system.
- **FR-028a**: System MUST suppress further proactive outreach for the same underlying issue on a line while that issue has an open, unresolved EscalationCase, resuming normal eligibility only once the case is resolved or closed.

**Provider Abstraction & Risk Scoring**

- **FR-029**: System MUST access every external dependency — customer data, order data, billing, notification delivery, support/escalation handoff, risk scoring, the language model, and embeddings/retrieval — through a defined provider interface, and MUST ship a deterministic, seeded mock implementation of each provider usable without any live external service.
- **FR-030**: The notification provider abstraction MUST support multiple delivery channels conceptually (e.g., push, SMS, email, in-app) without requiring a real integration to any of them for this MVP.
- **FR-031**: The risk-scoring provider MUST return deterministic/mock churn, call-likelihood, retail-visit-likelihood, and adoption scores without training or relying on any predictive model, while preserving an interface stable enough to be backed by a real model later without changing callers.

**Demo Control & Dashboard**

- **FR-032**: System MUST let a reviewer select a curated demo scenario (seeding account/line/journey state to that scenario's defined starting point), inject supported events against the active scenario, and reset the demo back to a clean starting state.
- **FR-033**: System MUST display, per account/journey, the account journey and its lines' activities, the current health score with reason codes, and the current next best action, updated as events are processed.
- **FR-034**: System MUST provide both an authenticated and an unauthenticated concierge chat surface consistent with the privacy boundary (FR-021), plus a billing/renewal information view and an escalation-result view.
- **FR-035**: System MUST provide an aggregate dashboard showing, at minimum: enrolled customers, engagement, onboarding completion, digital resolutions, escalations, and potential POCR and PORR intervention counts, with the POCR/PORR figures visibly and unambiguously labeled as simulated/projected hackathon metrics rather than measured results.

### Key Entities

- **AccountJourney**: The 30-day onboarding journey for one account/order context; holds overall status, start/end dates, and the set of attached lines. One per qualifying account/order.
- **LineOnboardingState**: The onboarding progress for a single wireless line within an account journey; holds the line's plan type (postpaid/prepaid), its set of activity instances, its status, and its health score.
- **ActivityDefinition**: A named onboarding activity (e.g., "SIM/eSIM activation", "AutoPay setup"), its scope (ACCOUNT or LINE), and its requirement class (REQUIRED, RECOMMENDED, OPTIONAL) per plan type.
- **ActivityInstance**: The tracked state of one ActivityDefinition for one account or line within a specific journey, including its current status and status-change history.
- **Event**: An immutable record of something that happened (e.g., DeviceActivationCompleted), carrying identifiers (event_id, customer_id, account_id, optional line_id/journey_id), timing, source, correlation_id, and attributes; processed idempotently by event_id.
- **NextBestAction**: A ranked, deterministic recommendation for a specific account or line, with its priority, reason codes, and a personalized message.
- **HealthScore**: A 0-100 score for an account or line, its color band (GREEN/YELLOW/RED), and the reason codes behind its deductions.
- **OutreachAttempt**: A record of a proactive contact delivered (or suppressed) to a customer, including which next best action it was for, delivery channel/time, and whether it was suppressed and why (contact cap, quiet hours, opt-out).
- **EscalationCase**: A record created when an escalation trigger fires, bundling the reason, priority, relevant journey/line state, event history, prior attempted actions, and a conversation summary for a human agent.
- **ConsentPreference**: A customer's proactive-contact consent/opt-out status, used to gate outreach delivery.
- **BillingSnapshot**: Provider-supplied postpaid billing facts (recurring/one-time charges, device installment, taxes/fees, promotional credits, cycle dates) used to compute a deterministic bill estimate.
- **RenewalSnapshot**: Provider-supplied prepaid facts (balance, renewal date, data allowance, auto-recharge state, expiration/add-on information) used to compute renewal readiness.
- **KnowledgeDocument**: A curated wireless help article/topic (e.g., activation, porting, AutoPay, network troubleshooting) retrievable to ground concierge answers.
- **RiskScoreSnapshot**: A mock/deterministic set of churn, call-likelihood, retail-visit-likelihood, and adoption scores for an account or line.
- **DemoScenario**: A named, seedable starting configuration (account, lines, journey state, and optionally pre-existing events) used to drive the reviewer-facing walkthrough.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In curated demo scenarios, 100% of qualifying new lines are enrolled into an onboarding journey immediately upon order completion, with no manual setup step required.
- **SC-002**: In curated demo scenarios that complete all required activities via events, the system recognizes onboarding completion for the correct line and account within one event-processing cycle of the final required activity completing.
- **SC-003**: In curated demo scenarios involving a friction event (activation failure, number-transfer failure/delay, repeated help visits, abandoned setup, or repeated chats), the concierge surfaces the correctly-prioritized next best action ahead of any lower-priority action, in 100% of the curated scenarios.
- **SC-004**: In curated demo scenarios, every health score and every next-best-action returned includes reason codes that account for 100% of the factors applied.
- **SC-005**: In curated demo scenarios, replaying a previously processed event produces no observable change in journey, activity, health-score, or next-best-action state.
- **SC-006**: In curated demo scenarios, unauthenticated requests never return customer-specific account, journey, billing, or health data, verified across 100% of the unauthenticated test scenarios.
- **SC-007**: In curated demo scenarios, every one of the defined escalation triggers produces an escalation case containing enough journey/event/conversation context that no additional customer-provided context is needed to understand what already happened.
- **SC-008**: In curated demo scenarios, concierge answers to knowledge-covered questions are grounded in the curated knowledge base and the customer's actual retrieved context, with zero instances of fabricated customer-specific facts or billing numbers.
- **SC-009**: The demo can present, per curated scenario, simulated POCR and PORR reduction figures that are visibly labeled as simulated/projected in every place they are shown.
- **SC-010**: A reviewer can run the full demo (scenario selection, event injection, journey/health/NBA observation, authenticated and unauthenticated concierge chat, billing/renewal education, escalation, and the aggregate dashboard) end-to-end from a clean local setup using only seeded/mocked data, without any live external service call.
- **SC-011**: Each of the 11 curated demo scenarios can be independently loaded, exercised, and reset without residual state from a prior scenario affecting the result.

## Assumptions

- "Qualifying new wireless line" means a newly purchased/activated postpaid or prepaid line at initial order completion; upgrades, replacements, and existing-line plan changes are out of scope for this MVP.
- An account has at most one active AccountJourney at a time (consistent with the "single 30-day account-level journey" model): if a second qualifying order arrives for an account that already has an active journey, its line(s) attach to that existing journey rather than starting a second, concurrent one.
- Customer authentication uses the account's existing standard login/session mechanism; this spec does not define a new authentication method, only that customer-specific data and actions require an authenticated session per the privacy boundary.
- Proactive outreach is delivered through the customer's available digital channels (e.g., push notification, SMS, in-app/email message) via the notification provider's channel abstraction; specific channel-selection logic beyond contact caps, quiet hours, and consent is left to implementation.
- An "unsupported/low-confidence issue" (one of the escalation triggers) means a question or request the concierge cannot ground in retrieved knowledge-base content or map to a supported deterministic action.
- "Repeated" help visits/chats (for health-score and escalation purposes) means more than one occurrence on the same unresolved topic within the active journey; exact repeat-count/window thresholds are configurable defaults, not fixed by this spec.
- If the 30-day journey window elapses with required activities still incomplete, the journey is marked expired/closed rather than continuing indefinitely; historical state remains available for reporting.
- Out-of-order events are resolved by timestamp/state precedence (a later-occurring terminal state such as COMPLETED is not overwritten by an earlier-occurring FAILED event delivered out of order), consistent with idempotent, auditable processing.
- All external dependencies (customer, order, billing, notification, support/escalation, risk scoring, language model, and embeddings/retrieval) are represented by seeded, deterministic mock providers for this MVP; no live third-party integration is in scope.
- The demo's user interface is a locally run web application (the requester specified a React/Vite-based demo); this spec describes its required screens and capabilities functionally and leaves the specific technology choice to the implementation plan.
- POCR/PORR figures shown in the demo are simulated/projected estimates derived from curated scenario modeling, not measured results from a live customer population.
- No voice channel, production CRM/order/billing/support/identity/notification integrations, production identity and access management, trained machine-learning models, generated video, retail appointment booking, or distributed microservice architecture are in scope for this MVP.
- Line or account churn, cancellation, downgrade, or suspension occurring mid-journey is out of scope for this MVP; a journey does not model a cancelled line, and billing/renewal readiness assumes the line remains active through day 30.
- Processed event_ids (idempotency dedupe keys, FR-008) are retained for the lifetime of the local demo database; this MVP implements no expiry or pruning policy.
- Demo session tokens (FR-021 authenticated context) do not expire during a running server process; there is no session-timeout or de-authentication-mid-conversation behavior in this MVP — a token remains valid until the server restarts.
- Proactive outreach is decided synchronously at each NBA/health evaluation (there is no persistent, pre-scheduled send queue); honoring an opt-out "immediately" (FR-015) means every subsequent evaluation checks `ConsentPreference` first, so there is nothing already "in flight" to separately cancel.
- When multiple lines' eligible actions compete for the same remaining daily/weekly contact-cap slot (FR-014), the tie-break is the same global ranking used within a single line — FR-011's base priority, then FR-012's tie-break order — applied across all of the customer's lines' candidate actions together; there is no separate line-level tie-break.
- Reason codes (FR-018) are short, stable identifiers matching the deduction/priority names already enumerated in FR-016 and FR-011 (e.g., `ACTIVATION_FAILURE`, `PORT_PENDING_TOO_LONG`); the full enumerated code list is an implementation detail derived 1:1 from those already-named factors, not separately fixed by this spec.
- The concierge does not ask a clarifying follow-up question before escalating a knowledge gap in this MVP: if retrieval returns no sufficiently relevant knowledge-base result for an authenticated troubleshooting request, that request immediately qualifies as the FR-027 unsupported/low-confidence escalation trigger.
- The "supported action set" referenced in FR-024 is the set of next-best-action types enumerated in FR-011 (activation/port/network resolution, required security setup, billing/renewal readiness, AutoPay/auto-recharge setup, app adoption, voicemail setup, protection decision, premium feature); the concierge may only ever claim to perform or offer actions from this list.
- A "billing dispute" (FR-027 escalation trigger) means the customer explicitly contests or disputes a charge or amount as wrong or unauthorized, as distinct from a general question about how a charge is computed, which is handled as ordinary FR-025/FR-026 billing/renewal explanation.
- The postpaid first-bill-readiness next best action (billing/renewal readiness, FR-011 priority 65) becomes eligible starting at journey day 21; the prepaid renewal-readiness next best action becomes eligible when the line's renewal date is within a configurable lookahead window (default 7 days) — both share the same FR-011 priority value.
