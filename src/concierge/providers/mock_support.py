"""Deterministic mock for SupportProvider (FR-029). Accepts an escalation
payload and returns a mock case handle/status — no real ticketing system."""

import hashlib


class MockSupportProvider:
    def create_case(self, escalation_payload: dict) -> dict:
        seed = escalation_payload.get("case_id") or str(sorted(escalation_payload.items()))
        handle = hashlib.sha256(seed.encode()).hexdigest()[:12].upper()
        return {"support_case_handle": f"CASE-{handle}", "status": "RECEIVED"}
