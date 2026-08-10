import { screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { createApiKeyDailyUsage } from "@/test/mocks/factories";
import { renderWithProviders } from "@/test/utils";

import { ApiDailyUsageCharts, DailyUsageTooltip } from "./api-daily-usage-charts";

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

  it("uses the compact dashboard tooltip and omits zero-value series", () => {
    renderWithProviders(
      <DailyUsageTooltip
        active
        label="2026-07-30"
        metric="cost"
        payload={[
          { dataKey: "zero", name: "Zero user", value: 0, color: "#111111" },
          { dataKey: "small", name: "Small user", value: 1.25, color: "#222222" },
          { dataKey: "large", name: "Large user", value: 9.5, color: "#333333" },
        ]}
      />,
    );

    const tooltip = screen.getByText("2026-07-30 UTC").parentElement;
    expect(tooltip).toHaveClass("rounded-lg", "bg-popover", "shadow-md");
    expect(screen.queryByText("Zero user")).not.toBeInTheDocument();
    expect(screen.getByText("Large user")).toBeInTheDocument();
    expect(screen.getByText("$9.50")).toBeInTheDocument();
    expect(screen.getByText("Large user").parentElement).toHaveTextContent("Large user$9.50");
  });
});
