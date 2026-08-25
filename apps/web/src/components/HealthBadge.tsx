import { useEffect, useState } from "react";
import { api, HealthScoreView } from "../api/client";

interface HealthBadgeProps {
  journeyId: string;
  refreshKey?: number;
}

const BAND_COLOR_VAR: Record<string, string> = {
  GREEN: "var(--color-health-green)",
  YELLOW: "var(--color-health-yellow)",
  RED: "var(--color-health-red)",
};

export default function HealthBadge({ journeyId, refreshKey }: HealthBadgeProps) {
  const [health, setHealth] = useState<HealthScoreView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setHealth(null);
    setError(null);
    api
      .getHealth(journeyId)
      .then((data) => {
        if (!cancelled) setHealth(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [journeyId, refreshKey]);

  if (error) return <p className="error">{error}</p>;
  if (!health) return <p>Loading health…</p>;

  return (
    <section className="card" aria-label="Health score">
      <h2>Health Score</h2>
      <div className="health-account" style={{ borderColor: BAND_COLOR_VAR[health.account.band] }}>
        <strong>Account: {health.account.score}</strong>
        <span style={{ color: BAND_COLOR_VAR[health.account.band] }}>{health.account.band}</span>
      </div>
      {health.lines.map((line) => (
        <div key={line.line_id} className="health-line" style={{ borderColor: BAND_COLOR_VAR[line.band] }}>
          <strong>
            Line {line.line_id}: {line.score}
          </strong>
          <span style={{ color: BAND_COLOR_VAR[line.band] }}>{line.band}</span>
          <ul className="reason-codes">
            {line.reason_codes.map((rc) => (
              <li key={rc.code}>
                {rc.label} ({rc.deduction})
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
