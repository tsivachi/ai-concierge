// Typed fetch client covering every backend endpoint this demo UI uses.
// Mirrors contracts/openapi.yaml plus the journeys/{id} view endpoint added
// during Phase 10 to give the UI something real to render.

const API_BASE = "/api";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let authToken: string | null = null;

export function setAuthToken(token: string | null): void {
  authToken = token;
}

export function getAuthToken(): string | null {
  return authToken;
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> | undefined),
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new ApiError(response.status, body.detail ?? response.statusText);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

// ---- Types (mirrors apps/api/schemas/*.py) --------------------------------

export interface DemoScenarioSummary {
  scenario_id: string;
  title: string;
  description: string;
}

export interface ScenarioResetResponse {
  scenario_id: string;
  title: string;
  account_id: string;
  customer_id: string;
  journey_id: string;
  line_ids: string[];
  events_applied: number;
}

export interface EventAck {
  event_id: string;
  outcome: "applied" | "duplicate" | "dead_lettered";
}

export const SUPPORTED_EVENT_TYPES = [
  "OrderCompleted",
  "DeviceDelivered",
  "DeviceActivationStarted",
  "DeviceActivationCompleted",
  "DeviceActivationFailed",
  "NumberTransferRequested",
  "NumberTransferPending",
  "NumberTransferCompleted",
  "NumberTransferFailed",
  "CustomerLoggedIn",
  "MobileAppDownloaded",
  "VoicemailConfigured",
  "AutoPayEnabled",
  "AutoRechargeEnabled",
  "HelpArticleViewed",
  "SetupAbandoned",
  "ChatStarted",
  "SupportCaseCreated",
] as const;
export type SupportedEventType = (typeof SUPPORTED_EVENT_TYPES)[number];

export interface LoginResponse {
  access_token: string;
  customer_id: string;
}

export interface ActivityInstanceOut {
  activity_code: string;
  status: string;
  requirement_class: string;
}

export interface LineOnboardingStateOut {
  line_id: string;
  plan_type: string;
  status: string;
  activities: ActivityInstanceOut[];
}

export interface AccountJourneyView {
  journey_id: string;
  account_id: string;
  status: string;
  started_at: string;
  expires_at: string;
  current_day: number;
  account_activities: ActivityInstanceOut[];
  lines: LineOnboardingStateOut[];
}

export interface ReasonCode {
  code: string;
  label: string;
  deduction: number | null;
}

export interface NextBestAction {
  line_id: string;
  action_code: string;
  priority: number;
  tie_break_rank: number;
  reason_codes: ReasonCode[];
  message: string | null;
  computed_at: string;
}

export interface HealthScore {
  scope: "ACCOUNT" | "LINE";
  line_id: string | null;
  score: number;
  band: "GREEN" | "YELLOW" | "RED";
  reason_codes: ReasonCode[];
}

export interface HealthScoreView {
  account: HealthScore;
  lines: HealthScore[];
}

export interface KnowledgeSourceRef {
  doc_id: string;
  title: string;
  topic: string;
}

export interface ChatResponse {
  session_id: string;
  authenticated: boolean;
  answer: string;
  sources: KnowledgeSourceRef[];
  escalated: boolean;
  escalation_case_id: string | null;
}

export interface EscalationCase {
  case_id: string;
  journey_id: string;
  line_id: string | null;
  reason: string;
  priority: number;
  journey_snapshot: Record<string, unknown>;
  relevant_event_ids: string[];
  attempted_action_ids: string[];
  conversation_summary: string | null;
  status: "OPEN" | "RESOLVED" | "CLOSED";
  created_at: string;
}

export interface DashboardView {
  simulated: boolean;
  enrolled_customers: number;
  engagement: { proactive_contacts_delivered: number; chat_sessions: number };
  onboarding_completion_rate: number;
  digital_resolutions: number;
  escalations: number;
  potential_pocr_interventions: number;
  potential_porr_interventions: number;
  label: string;
}

export interface KnowledgeSearchResult {
  doc_id: string;
  title: string;
  topic: string;
  snippet: string;
  score: number;
}

// ---- Endpoints --------------------------------------------------------------

export const api = {
  listScenarios: () => request<DemoScenarioSummary[]>("/demo/scenarios"),
  resetScenario: (scenarioId: string) =>
    request<ScenarioResetResponse>(`/demo/scenarios/${scenarioId}/reset`, { method: "POST" }),

  postEvent: (event: {
    event_id: string;
    event_type: SupportedEventType;
    customer_id: string;
    account_id: string;
    line_id?: string;
    occurred_at: string;
    source: string;
    correlation_id: string;
    attributes?: Record<string, unknown>;
  }) => request<EventAck>("/events", { method: "POST", body: JSON.stringify(event) }),

  login: (customerId: string) =>
    request<LoginResponse>("/auth/login", { method: "POST", body: JSON.stringify({ customer_id: customerId }) }),

  getJourney: (journeyId: string) => request<AccountJourneyView>(`/journeys/${journeyId}`),
  // NOTE: /journeys/{id}/billing is documented in contracts/openapi.yaml but
  // not yet implemented server-side (Phase 6 billing/renewal wasn't built in
  // this MVP slice) — this will 404 until that lands. BillingCard handles
  // that explicitly rather than pretending the feature works.
  getBilling: (journeyId: string, lineId: string) =>
    request<{
      plan_type: string;
      postpaid_estimate: Record<string, unknown> | null;
      prepaid_renewal: Record<string, unknown> | null;
      explanation: string;
    }>(`/journeys/${journeyId}/billing?line_id=${encodeURIComponent(lineId)}`),
  getRecommendation: (journeyId: string) => request<NextBestAction[]>(`/journeys/${journeyId}/recommendation`),
  getHealth: (journeyId: string) => request<HealthScoreView>(`/journeys/${journeyId}/health`),

  chat: (sessionId: string, message: string) =>
    request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ session_id: sessionId, message }) }),

  createEscalation: (journeyId: string, lineId: string, reason: string) =>
    request<EscalationCase>("/escalations", {
      method: "POST",
      body: JSON.stringify({ journey_id: journeyId, line_id: lineId, reason }),
    }),
  getEscalation: (caseId: string) => request<EscalationCase>(`/escalations?case_id=${encodeURIComponent(caseId)}`),

  getDashboard: () => request<DashboardView>("/dashboard"),

  searchKnowledge: (query: string) =>
    request<KnowledgeSearchResult[]>(`/knowledge/search?q=${encodeURIComponent(query)}`),
};
