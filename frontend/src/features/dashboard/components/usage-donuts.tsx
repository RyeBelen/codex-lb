import { useMemo } from "react";

import { DonutChart } from "@/components/donut-chart";
import type { RemainingItem, SafeLineView } from "@/features/dashboard/utils";
import { formatWindowLabel } from "@/utils/formatters";

export type UsageDonutsProps = {
	primaryItems: RemainingItem[];
	secondaryItems: RemainingItem[];
	primaryTotal: number;
	secondaryTotal: number;
	primaryWindowMinutes: number | null;
	secondaryWindowMinutes: number | null;
	safeLine?: SafeLineView | null;
};

export function UsageDonuts({
	primaryItems,
	secondaryItems,
	primaryTotal,
	secondaryTotal,
	primaryWindowMinutes,
	secondaryWindowMinutes,
	safeLine,
}: UsageDonutsProps) {
	const primaryChartItems = useMemo(
		() =>
			primaryItems.map((item) => ({
				label: item.label,
				value: item.value,
				color: item.color,
			})),
		[primaryItems],
	);
	const secondaryChartItems = useMemo(
		() =>
			secondaryItems.map((item) => ({
				label: item.label,
				value: item.value,
				color: item.color,
			})),
		[secondaryItems],
	);

	// Weekly-only plans remap usage to secondary — route safeLine to the active donut.
	// TODO: In mixed-plan dashboards (Plus + Free), the aggregate depletion is always
	// computed from primary usage; secondary-only depletion would require backend changes.
	const isWeeklyOnly = primaryItems.length === 0 || primaryTotal === 0;

	return (
		<div className="grid gap-4 lg:grid-cols-2">
			<DonutChart
				title="Primary Remaining"
				subtitle={`Window ${formatWindowLabel("primary", primaryWindowMinutes)}`}
				items={primaryChartItems}
				total={primaryTotal}
				safeLine={isWeeklyOnly ? undefined : safeLine}
			/>
			<DonutChart
				title="Secondary Remaining"
				subtitle={`Window ${formatWindowLabel("secondary", secondaryWindowMinutes)}`}
				items={secondaryChartItems}
				total={secondaryTotal}
				safeLine={isWeeklyOnly ? safeLine : undefined}
			/>
		</div>
	);
}
