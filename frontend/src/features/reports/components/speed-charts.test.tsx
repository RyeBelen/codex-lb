import type { ReactNode } from "react";
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { DailyReportRow } from "../schemas";
import { TimeToFirstTokenChart } from "./time-to-first-token-chart";
import { TokensPerSecondChart } from "./tokens-per-second-chart";

let capturedData: unknown;

vi.mock("@/components/lazy-recharts", () => ({
  ResponsiveContainer: ({ children }: { children: ReactNode }) => (
    <div>{children}</div>
  ),
  AreaChart: ({ data }: { data: unknown }) => {
    capturedData = data;
    return <div data-testid="speed-area-chart" />;
  },
  Area: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
}));

const SPEED_ROWS: DailyReportRow[] = [
  {
    date: "2026-04-01",
    historyResolution: "legacy_aggregate",
    requests: 25,
    inputTokens: 100,
    outputTokens: 50,
    cachedInputTokens: 20,
    costUsd: 1,
    activeAccounts: 2,
    errorCount: 0,
    medianTtftMs: null,
    medianTps: null,
  },
  {
    date: "2026-04-02",
    historyResolution: "exact",
    requests: 10,
    inputTokens: 40,
    outputTokens: 20,
    cachedInputTokens: 5,
    costUsd: 0.5,
    activeAccounts: 1,
    errorCount: 0,
    medianTtftMs: 1_500,
    medianTps: 18.5,
  },
];

describe("report speed charts", () => {
  beforeEach(() => {
    capturedData = undefined;
  });

  it("renders aggregate-only TTFT as a chart gap", () => {
    render(
      <TimeToFirstTokenChart
        startDate="2026-04-01"
        endDate="2026-04-02"
        data={SPEED_ROWS}
      />,
    );

    expect(capturedData).toEqual([
      { date: "04-01", ttft: null },
      { date: "04-02", ttft: 1_500 },
    ]);
  });

  it("renders aggregate-only throughput as a chart gap", () => {
    render(
      <TokensPerSecondChart
        startDate="2026-04-01"
        endDate="2026-04-02"
        data={SPEED_ROWS}
      />,
    );

    expect(capturedData).toEqual([
      { date: "04-01", tps: null },
      { date: "04-02", tps: 18.5 },
    ]);
  });
});
