import { useEffect, useState } from "react";
import { api, NextBestAction } from "../api/client";

interface NBACardProps {
  journeyId: string;
  refreshKey?: number;
}

export default function NBACard({ journeyId, refreshKey }: NBACardProps) {
  const [actions, setActions] = useState<NextBestAction[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setActions(null);
    setError(null);
    api
      .getRecommendation(journeyId)
      .then((data) => {
        if (!cancelled) setActions(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [journeyId, refreshKey]);

  if (error) return <p className="error">{error}</p>;
  if (!actions) return <p>Loading recommendations…</p>;

  return (
    <section className="card" aria-label="Next best action">
      <h2>Next Best Action</h2>
      {actions.length === 0 && <p>No open recommendations right now — nice work.</p>}
      {actions.map((nba) => (
        <div key={nba.line_id} className="nba-item">
          <p className="nba-line">Line {nba.line_id}</p>
          <p className="nba-action">
            {nba.action_code.replaceAll("_", " ")} <span className="nba-priority">priority {nba.priority}</span>
          </p>
          {nba.message && <p className="nba-message">{nba.message}</p>}
          <ul className="reason-codes">
            {nba.reason_codes.map((rc) => (
              <li key={rc.code}>{rc.label}</li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
