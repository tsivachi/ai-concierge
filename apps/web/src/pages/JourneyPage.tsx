import { useState } from "react";
import BillingCard from "../components/BillingCard";
import EscalationResult from "../components/EscalationResult";
import EventInjector from "../components/EventInjector";
import HealthBadge from "../components/HealthBadge";
import JourneyTimeline from "../components/JourneyTimeline";
import NBACard from "../components/NBACard";
import ScenarioSelector from "../components/ScenarioSelector";
import { ScenarioResetResponse } from "../api/client";

export default function JourneyPage() {
  const [scenario, setScenario] = useState<ScenarioResetResponse | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="journey-page">
      <ScenarioSelector onScenarioLoaded={(s) => { setScenario(s); setRefreshKey((k) => k + 1); }} />

      {scenario && (
        <>
          <p className="active-scenario">
            Active: <strong>{scenario.title}</strong> (journey {scenario.journey_id})
          </p>
          <div className="journey-grid">
            <JourneyTimeline journeyId={scenario.journey_id} refreshKey={refreshKey} />
            <HealthBadge journeyId={scenario.journey_id} refreshKey={refreshKey} />
            <NBACard journeyId={scenario.journey_id} refreshKey={refreshKey} />
            <EventInjector scenario={scenario} onEventApplied={() => setRefreshKey((k) => k + 1)} />
            <BillingCard scenario={scenario} />
            <EscalationResult scenario={scenario} />
          </div>
        </>
      )}
    </div>
  );
}
