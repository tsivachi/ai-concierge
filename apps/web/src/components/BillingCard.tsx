import { useEffect, useState } from "react";
import { ApiError, api, ScenarioResetResponse } from "../api/client";

interface BillingCardProps {
  scenario: ScenarioResetResponse;
}

/**
 * Renders the postpaid bill estimate or prepaid renewal readiness from
 * GET /journeys/{id}/billing (FR-025/FR-026). Some scenarios seed no
 * billing/renewal snapshot for a line (e.g. one still stuck on activation
 * failure) — the endpoint 404s in that case, and this card shows an honest
 * "no data yet" state rather than fabricating numbers.
 */
export default function BillingCard({ scenario }: BillingCardProps) {
  const [billing, setBilling] = useState<Awaited<ReturnType<typeof api.getBilling>> | null>(null);
  const [unavailable, setUnavailable] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const lineId = scenario.line_ids[0];
    setBilling(null);
    setUnavailable(false);
    setError(null);
    if (!lineId) return;

    api
      .getBilling(scenario.journey_id, lineId)
      .then((data) => {
        if (!cancelled) setBilling(data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 404) {
          setUnavailable(true);
        } else {
          setError(err instanceof Error ? err.message : String(err));
        }
      });
    return () => {
      cancelled = true;
    };
  }, [scenario.journey_id, scenario.line_ids]);

  return (
    <section className="card" aria-label="Billing and renewal">
      <h2>Billing / Renewal</h2>
      {error && <p className="error">{error}</p>}
      {unavailable && <p className="status-line">No billing/renewal data available for this line yet.</p>}
      {billing && (
        <div>
          {billing.postpaid_estimate && <pre>{JSON.stringify(billing.postpaid_estimate, null, 2)}</pre>}
          {billing.prepaid_renewal && <pre>{JSON.stringify(billing.prepaid_renewal, null, 2)}</pre>}
          <p>{billing.explanation}</p>
        </div>
      )}
    </section>
  );
}
