import type { TFunction } from "i18next";

import type { MultiSelectOption } from "@/features/dashboard/components/filters/multi-select-filter";
import { formatSlug } from "@/utils/formatters";

export const DEFAULT_DASHBOARD_ACCOUNT_STATUSES = [
  "active",
  "paused",
  "rate_limited",
  "quota_exceeded",
] as const;

const STATUS_TRANSLATION_KEYS: Record<string, string> = {
  active: "common.status.active",
  paused: "common.status.paused",
  rate_limited: "common.status.limited",
  quota_exceeded: "common.status.exceeded",
  reauth_required: "common.status.reauth",
  deactivated: "common.status.deactivated",
};

export function buildDashboardAccountStatusOptions(
  statuses: Iterable<string>,
  t: TFunction,
): MultiSelectOption[] {
  const values = new Set<string>(DEFAULT_DASHBOARD_ACCOUNT_STATUSES);
  for (const status of statuses) {
    values.add(status);
  }
  return [...values].sort().map((status) => {
    const translationKey = STATUS_TRANSLATION_KEYS[status];
    return {
      value: status,
      label: translationKey ? t(translationKey) : formatSlug(status),
    };
  });
}
