import { useState } from "react";
import { api, ChatResponse, getAuthToken, setAuthToken } from "../api/client";

interface ChatTurn {
  role: "user" | "concierge";
  text: string;
  sources?: ChatResponse["sources"];
  escalated?: boolean;
}

interface ChatPanelProps {
  seededCustomerId?: string;
}

export default function ChatPanel({ seededCustomerId }: ChatPanelProps) {
  const [authenticated, setAuthenticated] = useState(getAuthToken() !== null);
  const [customerIdInput, setCustomerIdInput] = useState(seededCustomerId ?? "");
  const [loginError, setLoginError] = useState<string | null>(null);
  const [sessionId] = useState(() => `web-${Date.now()}`);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);

  async function handleLogin() {
    setLoginError(null);
    try {
      const result = await api.login(customerIdInput);
      setAuthToken(result.access_token);
      setAuthenticated(true);
    } catch (err) {
      setLoginError(err instanceof Error ? err.message : String(err));
    }
  }

  function handleLogout() {
    setAuthToken(null);
    setAuthenticated(false);
  }

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!draft.trim()) return;
    const message = draft;
    setDraft("");
    setTurns((prev) => [...prev, { role: "user", text: message }]);
    setSending(true);
    try {
      const response = await api.chat(sessionId, message);
      setTurns((prev) => [
        ...prev,
        { role: "concierge", text: response.answer, sources: response.sources, escalated: response.escalated },
      ]);
    } catch (err) {
      setTurns((prev) => [
        ...prev,
        { role: "concierge", text: err instanceof Error ? err.message : String(err) },
      ]);
    } finally {
      setSending(false);
    }
  }

  return (
    <section className="card" aria-label="Concierge chat">
      <h2>Concierge Chat</h2>
      <div className="auth-toggle">
        {authenticated ? (
          <button type="button" onClick={handleLogout}>
            Log out
          </button>
        ) : (
          <div>
            <input
              type="text"
              placeholder="customer_id (e.g. cust-demo-1)"
              value={customerIdInput}
              onChange={(e) => setCustomerIdInput(e.target.value)}
            />
            <button type="button" onClick={handleLogin}>
              Log in
            </button>
            {loginError && <p className="error">{loginError}</p>}
          </div>
        )}
        <span className="auth-status">{authenticated ? "Authenticated" : "Unauthenticated (generic help only)"}</span>
      </div>

      <div className="chat-thread" role="log">
        {turns.map((turn, idx) => (
          <div key={idx} className={`chat-turn chat-turn-${turn.role}`}>
            <p>{turn.text}</p>
            {turn.escalated && <p className="escalated-badge">Escalated to a human agent</p>}
            {turn.sources && turn.sources.length > 0 && (
              <ul className="chat-sources">
                {turn.sources.map((s) => (
                  <li key={s.doc_id}>{s.title}</li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Ask the concierge…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
        <button type="submit" disabled={sending}>
          Send
        </button>
      </form>
    </section>
  );
}
