import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import JourneyTimeline from "../src/components/JourneyTimeline";
import * as apiModule from "../src/api/client";

describe("JourneyTimeline", () => {
  it("renders account and line activities once loaded", async () => {
    vi.spyOn(apiModule.api, "getJourney").mockResolvedValue({
      journey_id: "j1",
      account_id: "a1",
      status: "ACTIVE",
      started_at: "2026-08-24T00:00:00Z",
      expires_at: "2026-09-23T00:00:00Z",
      current_day: 2,
      account_activities: [{ activity_code: "ACCOUNT_SECURITY", status: "NOT_STARTED", requirement_class: "REQUIRED" }],
      lines: [
        {
          line_id: "line-1",
          plan_type: "POSTPAID",
          status: "IN_PROGRESS",
          activities: [{ activity_code: "SIM_ESIM_ACTIVATION", status: "COMPLETED", requirement_class: "REQUIRED" }],
        },
      ],
    });

    render(<JourneyTimeline journeyId="j1" />);

    await waitFor(() => expect(screen.getByText(/Account Journey/i)).toBeInTheDocument());
    expect(screen.getByText(/Day 2 of 30/i)).toBeInTheDocument();
    expect(screen.getByText(/SIM ESIM ACTIVATION/i)).toBeInTheDocument();
  });

  it("shows an error message when the fetch fails", async () => {
    vi.spyOn(apiModule.api, "getJourney").mockRejectedValue(new Error("boom"));

    render(<JourneyTimeline journeyId="j1" />);

    await waitFor(() => expect(screen.getByText("boom")).toBeInTheDocument());
  });
});
