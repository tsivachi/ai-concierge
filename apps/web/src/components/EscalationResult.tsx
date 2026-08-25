import { useState } from "react";
import { api, EscalationCase, ScenarioResetResponse } from "../api/client";

interface EscalationResultProps {
  scenario: ScenarioResetResponse;
}

const REASONS = [
  "EXPLICIT_REQUEST",
  "UNSUPPORTED_LOW_CONFIDENCE",
  "TWO_FAILED_TROUBLESHOOTING",
  "UNRESOLVED_ACTIVATION_OR_PORT",
  "BILLING_DISPUTE",
  "SENSITIVE_ACCOUNT_SECURITY",
] as const;

export default function EscalationResult({ scenario }: EscalationResultProps) {
  const [reason, setReason] = useState<(typeof REASONS)[number]>("EXPLICIT_REQUEST");
  const [caseData, setCaseData] = useState<EscalationCase | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleEscalate() {
    setSubmitting(true);
    setError(null);
    try {
      const lineId = scenario.line_ids[0];
      const result = await api.createEscalation(scenario.journey_id, lineId, reason);
      setCaseData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card" aria-label="Escalation">
      <h2>Escalation</h2>
      <label>
        Reason
        <select value={reason} onChange={(e) => setReason(e.target.value as (typeof REASONS)[number])}>
          {REASONS.map((r) => (
            <option key={r} value={r}>
              {r.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={handleEscalate} disabled={submitting}>
        Escalate to Human Agent
      </button>
      {error && <p className="error">{error}</p>}
      {caseData && (
        <div className="escalation-case">
          <p>
            <strong>Case {caseData.case_id}</strong> — {caseData.status}
          </p>
          <p>Reason: {caseData.reason}</p>
          <p>Priority: {caseData.priority}</p>
          {caseData.conversation_summary && <p>Summary: {caseData.conversation_summary}</p>}
          <p>Relevant events: {caseData.relevant_event_ids.length}</p>
        </div>
      )}
    </section>
  );
}
