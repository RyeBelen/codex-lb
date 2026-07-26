import { Users } from "lucide-react";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { EmptyState } from "@/components/empty-state";
import {
  buildDashboardAccountStatusOptions,
  DEFAULT_DASHBOARD_ACCOUNT_STATUSES,
} from "@/features/dashboard/account-status-filter";
import { AccountCard, type AccountCardProps } from "@/features/dashboard/components/account-card";
import { MultiSelectFilter } from "@/features/dashboard/components/filters/multi-select-filter";
import type { AccountSummary } from "@/features/dashboard/schemas";

const ACCOUNT_CARD_VISIBLE_ROWS = 2;
// Account cards can grow when the optional email row is rendered.
const ACCOUNT_CARD_ROW_HEIGHT_REM = 11.5;
const ACCOUNT_CARD_ROW_GAP_REM = 1;

export type AccountCardsProps = {
  accounts: AccountSummary[];
  readOnly?: boolean;
  onAction?: AccountCardProps["onAction"];
};

export function AccountCards({ accounts, readOnly = false, onAction }: AccountCardsProps) {
  const { t } = useTranslation();
  const [statusFilters, setStatusFilters] = useState<string[]>([
    ...DEFAULT_DASHBOARD_ACCOUNT_STATUSES,
  ]);
  const statusOptions = useMemo(
    () => buildDashboardAccountStatusOptions(accounts.map((account) => account.status), t),
    [accounts, t],
  );
  const visibleAccounts = useMemo(
    () => accounts.filter((account) => statusFilters.includes(account.status)),
    [accounts, statusFilters],
  );

  if (accounts.length === 0) {
    return (
      <EmptyState
        icon={Users}
        title={t("dashboard.accounts.emptyTitle")}
        description={t("dashboard.accounts.emptyDescription")}
      />
    );
  }

  return (
    <div className="space-y-3">
      <MultiSelectFilter
        label={t("dashboard.filters.statuses")}
        values={statusFilters}
        options={statusOptions}
        onChange={setStatusFilters}
      />
      <div
        data-testid="dashboard-account-cards"
        className="grid gap-4 overflow-y-auto pr-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden sm:grid-cols-2 lg:grid-cols-3"
        style={{
          maxHeight: `calc(${ACCOUNT_CARD_VISIBLE_ROWS} * ${ACCOUNT_CARD_ROW_HEIGHT_REM}rem + ${(ACCOUNT_CARD_VISIBLE_ROWS - 1) * ACCOUNT_CARD_ROW_GAP_REM}rem)`,
        }}
      >
        {visibleAccounts.map((account, index) => (
          <div key={account.accountId} className="animate-fade-in-up" style={{ animationDelay: `${index * 75}ms` }}>
            <AccountCard
              account={account}
              showAccountId={account.isEmailDuplicate === true}
              readOnly={readOnly}
              onAction={onAction}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
