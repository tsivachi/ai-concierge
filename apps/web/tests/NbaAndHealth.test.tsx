import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HealthBadge from "../src/components/HealthBadge";
import NBACard from "../src/components/NBACard";
import * as apiModule from "../src/api/client";

describe("HealthBadge", () => {
  it("renders account and line bands with reason codes", async () => {
    vi.spyOn(apiModule.api, "getHealth").mockResolvedValue({
      account: { scope: "ACCOUNT", line_id: null, score: 55, band: "YELLOW", reason_codes: [] },
      lines: [
        {
          scope: "LINE",
          line_id: "line-1",
          score: 55,
          band: "YELLOW",
          reason_codes: [{ code: "ACTIVATION_FAILURE", label: "Activation failure", deduction: -25 }],
        },
      ],
    });

    render(<HealthBadge journeyId="j1" />);

    await waitFor(() => expect(screen.getByText(/Account: 55/i)).toBeInTheDocument());
    expect(screen.getAllByText("YELLOW").length).toBeGreaterThan(0);
    expect(screen.getByText(/Activation failure/i)).toBeInTheDocument();
  });
});

describe("NBACard", () => {
  it("renders the top recommendation per line", async () => {
    vi.spyOn(apiModule.api, "getRecommendation").mockResolvedValue([
      {
        line_id: "line-1",
        action_code: "ACTIVATION_FAILURE",
        priority: 100,
        tie_break_rank: 0,
        reason_codes: [{ code: "ACTIVATION_FAILURE", label: "Device activation failed", deduction: null }],
        message: "Let's get your activation resolved.",
        computed_at: "2026-08-24T00:00:00Z",
      },
    ]);

    render(<NBACard journeyId="j1" />);

    await waitFor(() => expect(screen.getByText(/priority 100/i)).toBeInTheDocument());
    expect(screen.getByText(/Let's get your activation resolved/i)).toBeInTheDocument();
  });

  it("shows a friendly empty state when nothing is open", async () => {
    vi.spyOn(apiModule.api, "getRecommendation").mockResolvedValue([]);

    render(<NBACard journeyId="j1" />);

    await waitFor(() => expect(screen.getByText(/nice work/i)).toBeInTheDocument());
  });
});
