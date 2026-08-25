import { useEffect, useState } from "react";
import { api, DemoScenarioSummary, ScenarioResetResponse } from "../api/client";

interface ScenarioSelectorProps {
  onScenarioLoaded: (scenario: ScenarioResetResponse) => void;
}

export default function ScenarioSelector({ onScenarioLoaded }: ScenarioSelectorProps) {
  const [scenarios, setScenarios] = useState<DemoScenarioSummary[]>([]);
  const [loadingId, setLoadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listScenarios()
      .then(setScenarios)
      .catch((err) => setError(err.message));
  }, []);

  async function handleSelect(scenarioId: string) {
    setLoadingId(scenarioId);
    setError(null);
    try {
      const result = await api.resetScenario(scenarioId);
      onScenarioLoaded(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingId(null);
    }
  }

  return (
    <section className="card" aria-label="Demo scenario selector">
      <h2>Demo Scenarios</h2>
      {error && <p className="error">{error}</p>}
      <ul className="scenario-list">
        {scenarios.map((scenario) => (
          <li key={scenario.scenario_id}>
            <button
              type="button"
              onClick={() => handleSelect(scenario.scenario_id)}
              disabled={loadingId === scenario.scenario_id}
            >
              <strong>{scenario.title}</strong>
              <span>{scenario.description}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}
