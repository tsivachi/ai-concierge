import { useState } from "react";
import { api, ScenarioResetResponse, SUPPORTED_EVENT_TYPES, SupportedEventType } from "../api/client";

interface EventInjectorProps {
  scenario: ScenarioResetResponse;
  onEventApplied: () => void;
}

export default function EventInjector({ scenario, onEventApplied }: EventInjectorProps) {
  const [eventType, setEventType] = useState<SupportedEventType>("DeviceActivationStarted");
  const [lineId, setLineId] = useState(scenario.line_ids[0] ?? "");
  const [status, setStatus] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setStatus(null);
    try {
      const eventId = `ui-evt-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
      const result = await api.postEvent({
        event_id: eventId,
        event_type: eventType,
        customer_id: scenario.customer_id,
        account_id: scenario.account_id,
        line_id: lineId || undefined,
        occurred_at: new Date().toISOString(),
        source: "demo-ui",
        correlation_id: eventId,
        attributes: {},
      });
      setStatus(`Event ${result.outcome}`);
      onEventApplied();
    } catch (err) {
      setStatus(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card" aria-label="Event injector">
      <h2>Inject Event</h2>
      <form onSubmit={handleSubmit}>
        <label>
          Event type
          <select value={eventType} onChange={(e) => setEventType(e.target.value as SupportedEventType)}>
            {SUPPORTED_EVENT_TYPES.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </label>
        <label>
          Line
          <select value={lineId} onChange={(e) => setLineId(e.target.value)}>
            {scenario.line_ids.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={submitting}>
          Send Event
        </button>
      </form>
      {status && <p className="status-line">{status}</p>}
    </section>
  );
}
