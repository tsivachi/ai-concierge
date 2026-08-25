import { useEffect, useState } from "react";
import KpiTiles from "../components/KpiTiles";
import { DashboardView, api } from "../api/client";

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardView | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDashboard()
      .then(setDashboard)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="dashboard-page">
      <h1>Outcome Dashboard</h1>
      {error && <p className="error">{error}</p>}
      {dashboard ? <KpiTiles dashboard={dashboard} /> : <p>Loading dashboard…</p>}
    </div>
  );
}
