import { describe, expect, it } from "vitest";

import { ApiKeyDailyUsageResponseSchema } from "@/features/apis/schemas";

function createSeries(index: number) {
  return {
    keyId: `key-${index}`,
    name: `User ${index}`,
    points: [{ date: "2026-08-01", v: index }],
  };
}

describe("ApiKeyDailyUsageResponseSchema", () => {
  it("parses bounded named daily series", () => {
    const parsed = ApiKeyDailyUsageResponseSchema.parse({
      startDate: "2026-08-01",
      endDate: "2026-08-30",
      cost: [createSeries(1)],
      tokens: [createSeries(2)],
    });

    expect(parsed.cost[0].name).toBe("User 1");
    expect(parsed.tokens[0].points[0]).toEqual({ date: "2026-08-01", v: 2 });
  });

  it("rejects more than ten series for either metric", () => {
    expect(() =>
      ApiKeyDailyUsageResponseSchema.parse({
        startDate: "2026-08-01",
        endDate: "2026-08-30",
        cost: Array.from({ length: 11 }, (_, index) => createSeries(index)),
        tokens: [],
      }),
    ).toThrow();
  });
});
