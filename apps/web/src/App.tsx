import { useState } from "react";
import ChatPage from "./pages/ChatPage";
import DashboardPage from "./pages/DashboardPage";
import JourneyPage from "./pages/JourneyPage";

type Tab = "journey" | "chat" | "dashboard";

const TABS: { id: Tab; label: string }[] = [
  { id: "journey", label: "Journey" },
  { id: "chat", label: "Concierge Chat" },
  { id: "dashboard", label: "Dashboard" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("journey");

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>30-Day Personalized AI Concierge</h1>
        <nav aria-label="Primary">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={t.id === tab ? "nav-active" : ""}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main>
        {tab === "journey" && <JourneyPage />}
        {tab === "chat" && <ChatPage />}
        {tab === "dashboard" && <DashboardPage />}
      </main>
    </div>
  );
}
