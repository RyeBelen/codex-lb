import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { getAccountAccess, setAccountAccess } from "@/features/accounts/api";
import type { AccountAccess as AccessPolicy } from "@/features/accounts/schemas";
import { listApiKeys } from "@/features/api-keys/api";
import type { ApiKey } from "@/features/api-keys/schemas";

export function AccountAccess({ accountId, readOnly, busy }: {
  accountId: string;
  readOnly: boolean;
  busy: boolean;
}) {
  const policy = useQuery({
    queryKey: ["accounts", "api-key-access", accountId],
    queryFn: () => getAccountAccess(accountId),
  });
  const keys = useQuery({ queryKey: ["api-keys", "list"], queryFn: listApiKeys });

  return (
    <section aria-label="Account API key access" className="min-w-0 rounded-lg border bg-muted/30 p-4">
      <h3 className="text-sm font-semibold">API key access</h3>
      <p className="mt-1 text-xs text-muted-foreground">Reserve this account for selected API keys.</p>
      {policy.isError || keys.isError ? (
        <p role="alert" className="mt-3 text-sm text-destructive">Unable to load account access settings.</p>
      ) : policy.data && keys.data ? (
        <AccountAccessForm
          key={JSON.stringify(policy.data)}
          policy={policy.data}
          apiKeys={keys.data}
          disabled={readOnly || busy}
        />
      ) : <p role="status" className="mt-3 text-sm text-muted-foreground">Loading account access...</p>}
    </section>
  );
}

function AccountAccessForm({ policy, apiKeys, disabled }: {
  policy: AccessPolicy;
  apiKeys: ApiKey[];
  disabled: boolean;
}) {
  const queryClient = useQueryClient();
  const [restricted, setRestricted] = useState(policy.restricted);
  const [selected, setSelected] = useState(policy.apiKeyIds);
  const mutation = useMutation({
    mutationFn: () => setAccountAccess(policy.accountId, restricted, restricted ? selected : []),
    onSuccess: (data) => {
      queryClient.setQueryData(["accounts", "api-key-access", policy.accountId], data);
      void queryClient.invalidateQueries({ queryKey: ["api-keys"] });
      toast.success("Account API key access saved");
    },
  });
  const locked = disabled || mutation.isPending;
  const effectiveSelected = restricted ? selected : [];
  const changed = restricted !== policy.restricted ||
    JSON.stringify([...effectiveSelected].sort()) !== JSON.stringify([...policy.apiKeyIds].sort());
  const missingIds = selected.filter((id) => !apiKeys.some((key) => key.id === id));

  return (
    <div className="mt-3 space-y-3">
      <Select value={restricted ? "restricted" : "shared"} disabled={locked}
        onValueChange={(value) => setRestricted(value === "restricted")}>
        <SelectTrigger aria-label="API key access mode"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="shared">Shared</SelectItem>
          <SelectItem value="restricted">Restricted to selected API keys</SelectItem>
        </SelectContent>
      </Select>
      {restricted ? (
        <fieldset disabled={locked} className="space-y-2">
          <legend className="mb-2 text-sm font-medium">Allowed API keys</legend>
          <div className="max-h-56 space-y-2 overflow-y-auto">
            {apiKeys.map((key) => (
              <label key={key.id} className="flex items-center gap-2 text-sm">
                <Checkbox checked={selected.includes(key.id)} disabled={locked}
                  onCheckedChange={(checked) => setSelected((current) => checked
                    ? [...current, key.id] : current.filter((id) => id !== key.id))} />
                <span className="min-w-0 break-all">{key.name} <span className="text-muted-foreground">{key.keyPrefix}</span></span>
              </label>
            ))}
            {missingIds.map((id) => (
              <label key={id} className="flex items-center gap-2 text-sm">
                <Checkbox checked disabled={locked}
                  onCheckedChange={() => setSelected((current) => current.filter((value) => value !== id))} />
                <span>Unavailable key ({id})</span>
              </label>
            ))}
          </div>
          {selected.length === 0 ? (
            <p className="text-sm text-muted-foreground">No API keys selected. This account will deny all client inference.</p>
          ) : null}
          <p className="text-xs text-muted-foreground">Each key's Assigned accounts setting still applies.</p>
        </fieldset>
      ) : <p className="text-xs text-muted-foreground">API keys can use this account when their Assigned accounts setting permits it.</p>}
      {mutation.isError ? <p role="alert" className="text-sm text-destructive">{mutation.error.message}</p> : null}
      <Button size="sm" disabled={locked || !changed} onClick={() => mutation.mutate()}>
        {mutation.isPending ? "Saving..." : "Save account access"}
      </Button>
    </div>
  );
}
