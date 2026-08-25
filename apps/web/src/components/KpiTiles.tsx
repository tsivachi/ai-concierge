import { DashboardView } from "../api/client";

interface KpiTilesProps {
  dashboard: DashboardView;
}

export default function KpiTiles({ dashboard }: KpiTilesProps) {
  return (
    <div className="kpi-grid">
      <div className="kpi-tile">
        <span className="kpi-value">{dashboard.enrolled_customers}</span>
        <span className="kpi-label">Enrolled Customers</span>
      </div>
      <div className="kpi-tile">
        <span className="kpi-value">{dashboard.engagement.proactive_contacts_delivered}</span>
        <span className="kpi-label">Proactive Contacts Delivered</span>
      </div>
      <div className="kpi-tile">
        <span className="kpi-value">{dashboard.engagement.chat_sessions}</span>
        <span className="kpi-label">Chat Sessions</span>
      </div>
      <div className="kpi-tile">
        <span className="kpi-value">{Math.round(dashboard.onboarding_completion_rate * 100)}%</span>
        <span className="kpi-label">Onboarding Completion</span>
      </div>
      <div className="kpi-tile">
        <span className="kpi-value">{dashboard.digital_resolutions}</span>
        <span className="kpi-label">Digital Resolutions</span>
      </div>
      <div className="kpi-tile">
        <span className="kpi-value">{dashboard.escalations}</span>
        <span className="kpi-label">Escalations</span>
      </div>

      {/* POCR/PORR tiles: visibly and distinctly labeled simulated/projected
          wherever they render — never presented as measured (FR-035,
          Constitution Principle X). This label lives on the tile itself, not
          buried in a tooltip or footnote. */}
      <div className="kpi-tile kpi-tile-simulated">
        <span className="kpi-value">{dashboard.potential_pocr_interventions}</span>
        <span className="kpi-label">Potential POCR Interventions</span>
        <span className="kpi-simulated-badge">SIMULATED / PROJECTED</span>
      </div>
      <div className="kpi-tile kpi-tile-simulated">
        <span className="kpi-value">{dashboard.potential_porr_interventions}</span>
        <span className="kpi-label">Potential PORR Interventions</span>
        <span className="kpi-simulated-badge">SIMULATED / PROJECTED</span>
      </div>

      <p className="kpi-disclaimer">{dashboard.label}</p>
    </div>
  );
}
