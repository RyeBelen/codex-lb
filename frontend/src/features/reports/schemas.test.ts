import { describe, expect, it } from "vitest";

import { ReportsResponseSchema } from "./schemas";

const LEGACY_COVERAGE = {
  available: true,
  included: true,
  overlapsSelectedRange: true,
  bucketTimezone: "UTC",
  startDate: "2026-04-01",
  endDate: "2026-06-30",
  aggregateRows: 91,
  requestCount: 12_345,
  unsupportedMetrics: ["medianTtftMs", "medianTps"],
};

describe("ReportsResponseSchema", () => {
  it("parses legacy coverage and nullable aggregate-only metrics", () => {
    const parsed = ReportsResponseSchema.parse({
      summary: {
        totalCostUsd: 12.5,
        totalInputTokens: 300,
        totalOutputTokens: 200,
        totalCachedTokens: 0,
        totalRequests: 25,
        totalErrors: 1,
        activeAccounts: 3,
        avgCostPerDay: 4.17,
        avgRequestsPerDay: 8.33,
      },
      comparison: {
        canCompare: true,
        previous: {
          totalCostUsd: 10,
          totalTokens: 400,
          totalRequests: 20,
        },
      },
      legacyCoverage: LEGACY_COVERAGE,
      daily: [
        {
          date: "2026-04-01",
          historyResolution: "legacy_aggregate",
          requests: 100,
          inputTokens: 300,
          outputTokens: 200,
          cachedInputTokens: 50,
          costUsd: 1.25,
          activeAccounts: 2,
          errorCount: 1,
          medianTtftMs: null,
          medianTps: null,
        },
      ],
      byModel: [
        {
          model: "gpt-5.1",
          costUsd: 12.5,
          requests: 25,
          percentage: 100,
        },
      ],
      byUseragent: [
        {
          useragent: "claude-code",
          costUsd: 12.5,
          requests: 25,
          percentage: 100,
        },
      ],
      byAccount: [],
    });

    expect(parsed.comparison.canCompare).toBe(true);
    expect(parsed.comparison.previous.totalCostUsd).toBe(10);
    expect(parsed.comparison.previous.totalTokens).toBe(400);
    expect(parsed.comparison.previous.totalRequests).toBe(20);
    expect(parsed.byModel[0]?.requests).toBe(25);
    expect(parsed.byUseragent[0]?.useragent).toBe("claude-code");
    expect(parsed.legacyCoverage.overlapsSelectedRange).toBe(true);
    expect(parsed.daily[0]).toMatchObject({
      historyResolution: "legacy_aggregate",
      medianTtftMs: null,
      medianTps: null,
    });
  });

  it("rejects payloads without the comparison block", () => {
    expect(() =>
      ReportsResponseSchema.parse({
        summary: {
          totalCostUsd: 12.5,
          totalInputTokens: 300,
          totalOutputTokens: 200,
          totalCachedTokens: 0,
          totalRequests: 25,
          totalErrors: 1,
          activeAccounts: 3,
          avgCostPerDay: 4.17,
          avgRequestsPerDay: 8.33,
        },
        legacyCoverage: LEGACY_COVERAGE,
        daily: [],
        byModel: [],
        byUseragent: [],
        byAccount: [],
      }),
    ).toThrow(/comparison/i);
  });

  it("rejects comparison blocks without previous totals", () => {
    expect(() =>
      ReportsResponseSchema.parse({
        summary: {
          totalCostUsd: 12.5,
          totalInputTokens: 300,
          totalOutputTokens: 200,
          totalCachedTokens: 0,
          totalRequests: 25,
          totalErrors: 1,
          activeAccounts: 3,
          avgCostPerDay: 4.17,
          avgRequestsPerDay: 8.33,
        },
        comparison: {
          canCompare: false,
        },
        legacyCoverage: LEGACY_COVERAGE,
        daily: [],
        byModel: [],
        byUseragent: [],
        byAccount: [],
      }),
    ).toThrow(/previous/i);
  });

  it("rejects byModel entries without request totals", () => {
    expect(() =>
      ReportsResponseSchema.parse({
        summary: {
          totalCostUsd: 12.5,
          totalInputTokens: 300,
          totalOutputTokens: 200,
          totalCachedTokens: 0,
          totalRequests: 25,
          totalErrors: 1,
          activeAccounts: 3,
          avgCostPerDay: 4.17,
          avgRequestsPerDay: 8.33,
        },
        comparison: {
          canCompare: true,
          previous: {
            totalCostUsd: 10,
            totalTokens: 400,
            totalRequests: 20,
          },
        },
        legacyCoverage: LEGACY_COVERAGE,
        daily: [],
        byModel: [
          {
            model: "gpt-5.1",
            costUsd: 12.5,
            percentage: 100,
          },
        ],
        byUseragent: [],
        byAccount: [],
      }),
    ).toThrow(/requests/i);
  });

  it("rejects payloads without useragent breakdowns", () => {
    expect(() =>
      ReportsResponseSchema.parse({
        summary: {
          totalCostUsd: 12.5,
          totalInputTokens: 300,
          totalOutputTokens: 200,
          totalCachedTokens: 0,
          totalRequests: 25,
          totalErrors: 1,
          activeAccounts: 3,
          avgCostPerDay: 4.17,
          avgRequestsPerDay: 8.33,
        },
        comparison: {
          canCompare: true,
          previous: {
            totalCostUsd: 10,
            totalTokens: 400,
            totalRequests: 20,
          },
        },
        legacyCoverage: LEGACY_COVERAGE,
        daily: [],
        byModel: [
          {
            model: "gpt-5.1",
            costUsd: 12.5,
            requests: 25,
            percentage: 100,
          },
        ],
        byAccount: [],
      }),
    ).toThrow(/byUseragent/i);
  });
});
