import { useEffect, useState } from "react";
import { AccountJourneyView, api } from "../api/client";

interface JourneyTimelineProps {
  journeyId: string;
  refreshKey?: number;
}

const STATUS_LABELS: Record<string, string> = {
  NOT_STARTED: "Not started",
  IN_PROGRESS: "In progress",
  COMPLETED: "Completed",
  FAILED: "Failed",
  NOT_APPLICABLE: "N/A",
};

function ActivityRow({ activityCode, status, requirementClass }: { activityCode: string; status: string; requirementClass: string }) {
  return (
    <li className={`activity-row status-${status.toLowerCase()}`}>
      <span className="activity-code">{activityCode.replaceAll("_", " ")}</span>
      <span className="activity-requirement">{requirementClass}</span>
      <span className="activity-status">{STATUS_LABELS[status] ?? status}</span>
    </li>
  );
}

export default function JourneyTimeline({ journeyId, refreshKey }: JourneyTimelineProps) {
  const [journey, setJourney] = useState<AccountJourneyView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setJourney(null);
    setError(null);
    api
      .getJourney(journeyId)
      .then((data) => {
        if (!cancelled) setJourney(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, [journeyId, refreshKey]);

  if (error) return <p className="error">{error}</p>;
  if (!journey) return <p>Loading journey…</p>;

  return (
    <section className="card" aria-label="Journey timeline">
      <h2>Account Journey</h2>
      <p>
        Status: <strong>{journey.status}</strong> · Day {journey.current_day} of 30
      </p>

      {journey.account_activities.length > 0 && (
        <>
          <h3>Account-Level Activities</h3>
          <ul className="activity-list">
            {journey.account_activities.map((a) => (
              <ActivityRow key={a.activity_code} activityCode={a.activity_code} status={a.status} requirementClass={a.requirement_class} />
            ))}
          </ul>
        </>
      )}

      {journey.lines.map((line) => (
        <div key={line.line_id} className="line-block">
          <h3>
            Line {line.line_id} ({line.plan_type}) — {line.status}
          </h3>
          <ul className="activity-list">
            {line.activities.map((a) => (
              <ActivityRow key={a.activity_code} activityCode={a.activity_code} status={a.status} requirementClass={a.requirement_class} />
            ))}
          </ul>
        </div>
      ))}
    </section>
  );
}
