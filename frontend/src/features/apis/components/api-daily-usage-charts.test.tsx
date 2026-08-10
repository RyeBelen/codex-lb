import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createApiKeyDailyUsage } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

import { ApiDailyUsageCharts } from "./api-daily-usage-charts";

function createSeries(index: number) {
  return {
    keyId: `key-${index}`,
    name: `Daily user ${index}`,
    points: [{ date: "2026-01-01", v: index + 1 }],
  };
}

describe("ApiDailyUsageCharts", () => {
  it("renders separate named cost and token charts with at most ten lines", () => {
    renderWithProviders(
      <ApiDailyUsageCharts
        data={createApiKeyDailyUsage({
          cost: Array.from({ length: 10 }, (_, index) => createSeries(index)),
          tokens: Array.from({ length: 10 }, (_, index) => createSeries(index + 10)),
        })}
      />,
    );

    expect(screen.getByText("Daily Cost by API Key")).toBeInTheDocument();
    expect(screen.getByText("Daily Tokens by API Key")).toBeInTheDocument();
    expect(screen.getAllByTestId("api-daily-cost-series")).toHaveLength(10);
    expect(screen.getAllByTestId("api-daily-tokens-series")).toHaveLength(10);
    expect(within(screen.getByTestId("api-daily-cost-legend")).getByText("Daily user 0")).toBeInTheDocument();
    expect(within(screen.getByTestId("api-daily-tokens-legend")).getByText("Daily user 19")).toBeInTheDocument();
  });

  it("keeps both daily graph cards visible when the window has no usage", () => {
    renderWithProviders(<ApiDailyUsageCharts data={createApiKeyDailyUsage({ cost: [], tokens: [] })} />);

    expect(screen.getAllByText("No usage recorded in this window.")).toHaveLength(2);
    expect(screen.getByTestId("api-daily-cost-panel")).toBeInTheDocument();
    expect(screen.getByTestId("api-daily-tokens-panel")).toBeInTheDocument();
  });
});
