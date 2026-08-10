import { useMemo } from "react";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "@/components/lazy-recharts";
import type { ApiKeyDailyUsageResponse, ApiKeyDailyUsageSeries } from "@/features/apis/schemas";
import { useReducedMotion } from "@/hooks/use-reduced-motion";
import { useThemeStore } from "@/hooks/use-theme";
import { buildDonutPalette } from "@/utils/colors";
import { formatCompactNumber, formatCurrency } from "@/utils/formatters";

type DailyChartMetric = "cost" | "tokens";
type DailyChartRow = Record<string, string | number> & { date: string };

function buildChartRows(series: ApiKeyDailyUsageSeries[]): DailyChartRow[] {
  if (series.length === 0) return [];
  return series[0].points.map((point, index) => {
    const row: DailyChartRow = { date: point.date };
    for (const item of series) {
      row[item.keyId] = item.points[index]?.v ?? 0;
    }
    return row;
  });
}

function formatDateTick(value: string): string {
  return value.slice(5);
}

function formatMetricValue(metric: DailyChartMetric, value: number): string {
  return metric === "cost" ? formatCurrency(value) : formatCompactNumber(value);
}

type DailyUsagePanelProps = {
  metric: DailyChartMetric;
  title: string;
  subtitle: string;
  series: ApiKeyDailyUsageSeries[];
};

function DailyUsagePanel({ metric, title, subtitle, series }: DailyUsagePanelProps) {
  const visibleSeries = series.slice(0, 10);
  const isDark = useThemeStore((state) => state.theme === "dark");
  const reducedMotion = useReducedMotion();
  const colors = useMemo(() => buildDonutPalette(visibleSeries.length, isDark), [isDark, visibleSeries.length]);
  const chartRows = useMemo(() => buildChartRows(visibleSeries), [visibleSeries]);

  return (
    <div className="rounded-xl border bg-card p-4" data-testid={`api-daily-${metric}-panel`}>
      <div>
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
      </div>

      {visibleSeries.length === 0 ? (
        <div className="mt-4 flex h-[18rem] items-center justify-center rounded-lg border border-dashed bg-muted/10 px-4 text-sm text-muted-foreground">
          No usage recorded in this window.
        </div>
      ) : (
        <>
          <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1.5" data-testid={`api-daily-${metric}-legend`}>
            {visibleSeries.map((item, index) => (
              <div
                key={item.keyId}
                className="flex min-w-0 items-center gap-1.5 text-[11px] text-muted-foreground"
                data-testid={`api-daily-${metric}-series`}
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ backgroundColor: colors[index] }}
                  aria-hidden
                />
                <span className="max-w-40 truncate" title={item.name}>
                  {item.name}
                </span>
              </div>
            ))}
          </div>

          <div className="mt-3 h-[18rem]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartRows} margin={{ top: 5, right: 10, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="currentColor" opacity={0.06} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDateTick}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                  minTickGap={28}
                />
                <YAxis
                  tickFormatter={(value: number) => formatMetricValue(metric, value)}
                  tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                  tickLine={false}
                  axisLine={false}
                  width={52}
                />
                <Tooltip
                  labelFormatter={(label: string) => `${label} UTC`}
                  formatter={(value: number, name: string) => [formatMetricValue(metric, value), name]}
                  contentStyle={{
                    borderRadius: "0.5rem",
                    borderColor: "hsl(var(--border))",
                    backgroundColor: "hsl(var(--popover))",
                    color: "hsl(var(--popover-foreground))",
                    fontSize: "0.75rem",
                  }}
                />
                {visibleSeries.map((item, index) => (
                  <Line
                    key={item.keyId}
                    type="monotone"
                    dataKey={item.keyId}
                    name={item.name}
                    stroke={colors[index]}
                    strokeWidth={1.75}
                    dot={false}
                    activeDot={{ r: 3, strokeWidth: 1.5, fill: "hsl(var(--popover))" }}
                    isAnimationActive={!reducedMotion}
                    animationDuration={450}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}

export type ApiDailyUsageChartsProps = {
  data: ApiKeyDailyUsageResponse;
};

export function ApiDailyUsageCharts({ data }: ApiDailyUsageChartsProps) {
  const windowLabel = `${data.startDate} to ${data.endDate} UTC`;
  return (
    <div className="grid gap-4 xl:grid-cols-2" data-testid="api-daily-usage-charts">
      <DailyUsagePanel
        metric="cost"
        title="Daily Cost by API Key"
        subtitle={`Top 10 by cost · ${windowLabel}`}
        series={data.cost}
      />
      <DailyUsagePanel
        metric="tokens"
        title="Daily Tokens by API Key"
        subtitle={`Top 10 by tokens · ${windowLabel}`}
        series={data.tokens}
      />
    </div>
  );
}
