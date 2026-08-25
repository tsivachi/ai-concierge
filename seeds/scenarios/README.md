# Demo Scenario Seed Files

Each `<scenario-id>.json` file in this directory seeds one curated demo scenario (see `specs/001-ai-onboarding-concierge/spec.md` §Demo Scenario Catalog and `data-model.md` §DemoScenario).

## Schema

```json
{
  "scenario_id": "postpaid-device-port-in",
  "title": "New postpaid device + port-in",
  "description": "Human-readable summary shown in the scenario selector.",
  "account": {
    "account_id": "acct-demo-1",
    "customer_id": "cust-demo-1"
  },
  "lines": [
    {
      "line_id": "line-demo-1",
      "plan_type": "POSTPAID",
      "number_port_requested": true
    }
  ],
  "journey_started_at_offset_days": 0,
  "events": [
    {
      "event_id": "seed-evt-1",
      "event_type": "OrderCompleted",
      "customer_id": "cust-demo-1",
      "account_id": "acct-demo-1",
      "line_id": "line-demo-1",
      "occurred_at_offset_days": 0,
      "source": "seed",
      "correlation_id": "seed-corr-1",
      "attributes": {}
    }
  ],
  "consent": { "cust-demo-1": { "opted_out": false } }
}
```

- `journey_started_at_offset_days`: how many days in the past to backdate the journey's `started_at`, so day-3/5/7/10/21 NBA and health thresholds are already true on load (research.md §6) — no real-time waiting required.
- `events[].occurred_at_offset_days`: same backdating convention, relative to `journey_started_at_offset_days`.
- `POST /api/demo/scenarios/{id}/reset` truncates all prior scenario state and replays this file's `events` in order through the same idempotent ingestion path as live events.
