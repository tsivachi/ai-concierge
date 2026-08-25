"""Deterministic mock for RiskScoringProvider (FR-031): no ML training, a
fixed formula over the id's hash, stable across repeated calls with the
same input — this is the "future replacement seam," not a live signal
consumed by NBA/health in this MVP (spec.md FR-031, data-model.md
§RiskScoreSnapshot)."""

import hashlib


def _stable_unit_float(*parts: str) -> float:
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return int(digest[:8], 16) / 0xFFFFFFFF


class MockRiskScoringProvider:
    def score(self, account_id: str | None, line_id: str | None) -> dict:
        key = account_id or line_id or "unknown"
        return {
            "churn_score": round(_stable_unit_float(key, "churn"), 4),
            "call_likelihood_score": round(_stable_unit_float(key, "call"), 4),
            "retail_visit_likelihood_score": round(_stable_unit_float(key, "retail"), 4),
            "adoption_score": round(_stable_unit_float(key, "adoption"), 4),
        }
