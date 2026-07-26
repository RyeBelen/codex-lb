import { lazy, Suspense, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { DonutChartProps } from "@/components/donut-chart";
import {
	buildDashboardAccountStatusOptions,
	DEFAULT_DASHBOARD_ACCOUNT_STATUSES,
} from "@/features/dashboard/account-status-filter";
import { MultiSelectFilter } from "@/features/dashboard/components/filters/multi-select-filter";
import { sumRemaining, type RemainingItem, type SafeLineView } from "@/features/dashboard/utils";

function estimateCapacity(items: RemainingItem[]): number {
	return items.reduce((sum, item) => {
		if (item.remainingPercent == null || item.remainingPercent <= 0) {
			return sum + Math.max(0, item.value);
		}
		return sum + Math.max(0, item.value / (item.remainingPercent / 100));
	}, 0);
}

const DonutChart = lazy(() =>
  import("@/components/donut-chart").then((module) => ({
    default: (props: DonutChartProps) => <module.DonutChart {...props} />,
  })),
);

export type UsageDonutsProps = {
	primaryItems: RemainingItem[];
	secondaryItems: RemainingItem[];
	primaryTotal: number;
	secondaryTotal: number;
	primaryCenterValue?: number;
	secondaryCenterValue?: number;
	safeLinePrimary?: SafeLineView | null;
	safeLineSecondary?: SafeLineView | null;
};

export function UsageDonuts({
	primaryItems,
	secondaryItems,
	primaryTotal,
	secondaryTotal,
	primaryCenterValue,
	secondaryCenterValue,
	safeLinePrimary,
	safeLineSecondary,
}: UsageDonutsProps) {
	const { t } = useTranslation();
	const [statusFilters, setStatusFilters] = useState<string[]>([
		...DEFAULT_DASHBOARD_ACCOUNT_STATUSES,
	]);
	const statusOptions = useMemo(
		() =>
			buildDashboardAccountStatusOptions(
				[
					...primaryItems.map((item) => item.status),
					...secondaryItems.map((item) => item.status),
				],
				t,
			),
		[primaryItems, secondaryItems, t],
	);
	const filteredPrimaryItems = useMemo(
		() => primaryItems.filter((item) => statusFilters.includes(item.status)),
		[primaryItems, statusFilters],
	);
	const filteredSecondaryItems = useMemo(
		() => secondaryItems.filter((item) => statusFilters.includes(item.status)),
		[secondaryItems, statusFilters],
	);
	const primaryChartItems = useMemo(
		() =>
			filteredPrimaryItems.map((item) => ({
				id: item.accountId,
				label: item.label,
				labelSuffix: item.labelSuffix,
				isEmail: item.isEmail,
				value: item.value,
				color: item.color,
			})),
		[filteredPrimaryItems],
	);
	const secondaryChartItems = useMemo(
		() =>
			filteredSecondaryItems.map((item) => ({
				id: item.accountId,
				label: item.label,
				labelSuffix: item.labelSuffix,
				isEmail: item.isEmail,
				value: item.value,
				color: item.color,
			})),
		[filteredSecondaryItems],
	);
	const showingAllPrimary = filteredPrimaryItems.length === primaryItems.length;
	const showingAllSecondary = filteredSecondaryItems.length === secondaryItems.length;
	const visiblePrimaryTotal = showingAllPrimary
		? primaryTotal
		: estimateCapacity(filteredPrimaryItems);
	const visibleSecondaryTotal = showingAllSecondary
		? secondaryTotal
		: estimateCapacity(filteredSecondaryItems);
	const visiblePrimaryCenterValue = showingAllPrimary
		? primaryCenterValue
		: sumRemaining(filteredPrimaryItems);
	const visibleSecondaryCenterValue = showingAllSecondary
		? secondaryCenterValue
		: sumRemaining(filteredSecondaryItems);

	return (
		<div className="space-y-3">
			<MultiSelectFilter
				label={t("dashboard.filters.statuses")}
				values={statusFilters}
				options={statusOptions}
				onChange={setStatusFilters}
			/>
			<Suspense fallback={<div className="grid gap-4 lg:grid-cols-2" />}>
			<div className="grid gap-4 lg:grid-cols-2">
			<DonutChart
				title={t("dashboard.usage.fiveHourCredits")}
				items={primaryChartItems}
				total={visiblePrimaryTotal}
				centerValue={visiblePrimaryCenterValue}
				safeLine={safeLinePrimary}
				centerLayout="credits"
			/>
			<DonutChart
				title={t("dashboard.usage.weeklyCredits")}
				items={secondaryChartItems}
				total={visibleSecondaryTotal}
				centerValue={visibleSecondaryCenterValue}
				safeLine={safeLineSecondary}
				centerLayout="credits"
			/>
			</div>
			</Suspense>
		</div>
	);
}
