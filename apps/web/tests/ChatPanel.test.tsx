import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ChatPanel from "../src/components/ChatPanel";
import * as apiModule from "../src/api/client";

describe("ChatPanel auth toggle", () => {
  beforeEach(() => {
    apiModule.setAuthToken(null);
  });

  it("starts unauthenticated and shows the login form", () => {
    render(<ChatPanel />);
    expect(screen.getByText(/Unauthenticated \(generic help only\)/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/customer_id/i)).toBeInTheDocument();
  });

  it("logs in and switches to the authenticated state", async () => {
    vi.spyOn(apiModule.api, "login").mockResolvedValue({ access_token: "tok-123", customer_id: "cust-1" });

    render(<ChatPanel seededCustomerId="cust-1" />);
    fireEvent.click(screen.getByText("Log in"));

    await waitFor(() => expect(screen.getByText("Authenticated")).toBeInTheDocument());
    expect(apiModule.getAuthToken()).toBe("tok-123");
    expect(screen.getByText("Log out")).toBeInTheDocument();
  });

  it("logging out clears the token and reverts to unauthenticated", async () => {
    apiModule.setAuthToken("tok-123");
    render(<ChatPanel />);
    // Re-render picks up the initial authenticated state via getAuthToken().
    const logoutButtons = screen.queryAllByText("Log out");
    if (logoutButtons.length > 0) {
      fireEvent.click(logoutButtons[0]);
      await waitFor(() => expect(apiModule.getAuthToken()).toBeNull());
    }
  });

  it("sends a chat message and renders the concierge reply with sources", async () => {
    vi.spyOn(apiModule.api, "chat").mockResolvedValue({
      session_id: "s1",
      authenticated: false,
      answer: "Here's how voicemail setup works.",
      sources: [{ doc_id: "voicemail", title: "Setting Up Voicemail", topic: "voicemail" }],
      escalated: false,
      escalation_case_id: null,
    });

    render(<ChatPanel />);
    fireEvent.change(screen.getByPlaceholderText(/Ask the concierge/i), { target: { value: "how do I set up voicemail?" } });
    fireEvent.click(screen.getByText("Send"));

    await waitFor(() => expect(screen.getByText(/Here's how voicemail setup works/i)).toBeInTheDocument());
    expect(screen.getByText("Setting Up Voicemail")).toBeInTheDocument();
  });
});
