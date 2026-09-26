import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { getAccountAllowedModels, setAccountAllowedModels } from "@/features/accounts/api";
import type { AccountAllowedModels as AllowedModelsPolicy } from "@/features/accounts/schemas";

const queryKey = (accountId: string) => ["accounts", "allowed-models", accountId];

export function AccountAllowedModels({ accountId, readOnly, busy }: {
  accountId: string;
  readOnly: boolean;
  busy: boolean;
}) {
  const policy = useQuery({
    queryKey: queryKey(accountId),
    queryFn: () => getAccountAllowedModels(accountId),
  });

  return (
    <section aria-label="Account allowed models" className="min-w-0 rounded-lg border bg-muted/30 p-4">
      <h3 className="text-sm font-semibold">Allowed models</h3>
      <p className="mt-1 text-xs text-muted-foreground">
        Select models this account may serve. No selection allows all supported models.
      </p>
      {policy.isError ? (
        <p role="alert" className="mt-3 text-sm text-destructive">Unable to load allowed models.</p>
      ) : policy.data ? (
        <AccountAllowedModelsForm
          key={JSON.stringify(policy.data)}
          policy={policy.data}
          disabled={readOnly || busy}
        />
      ) : <p role="status" className="mt-3 text-sm text-muted-foreground">Loading allowed models...</p>}
    </section>
  );
}

function AccountAllowedModelsForm({ policy, disabled }: {
  policy: AllowedModelsPolicy;
  disabled: boolean;
}) {
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState(policy.allowedModels);
  const mutation = useMutation({
    mutationFn: () => setAccountAllowedModels(policy.accountId, selected),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey(policy.accountId), data);
      toast.success("Allowed models saved");
    },
  });
  const locked = disabled || mutation.isPending;
  const changed = JSON.stringify([...selected].sort()) !== JSON.stringify([...policy.allowedModels].sort());
  const missingIds = selected.filter((id) => !policy.availableModels.some((model) => model.id === id));

  return (
    <div className="mt-3 space-y-3">
      {!policy.catalogAvailable ? (
        <p role="status" className="text-sm text-muted-foreground">
          This account&apos;s model catalog is unavailable. Known models are listed when available; this account&apos;s support is unverified until its catalog refreshes.
        </p>
      ) : null}
      <fieldset disabled={locked} className="space-y-2">
        <legend className="sr-only">Allowed models</legend>
        <div className="max-h-56 space-y-2 overflow-y-auto">
          {policy.availableModels.map((model) => (
            <label key={model.id} className="flex items-center gap-2 text-sm">
              <Checkbox checked={selected.includes(model.id)} disabled={locked}
                onCheckedChange={(checked) => setSelected((current) => checked
                  ? [...current, model.id] : current.filter((id) => id !== model.id))} />
              <span className="min-w-0 break-all">
                {model.name} {model.name !== model.id ? <span className="text-muted-foreground">{model.id}</span> : null}
              </span>
            </label>
          ))}
          {missingIds.map((id) => (
            <label key={id} className="flex items-center gap-2 text-sm">
              <Checkbox checked disabled={locked}
                onCheckedChange={() => setSelected((current) => current.filter((value) => value !== id))} />
              <span>{policy.catalogAvailable ? "Unavailable model" : "Saved model"} ({id})</span>
            </label>
          ))}
        </div>
        {policy.availableModels.length === 0 && missingIds.length === 0 ? (
          <p className="text-sm text-muted-foreground">This account has no resolved supported models.</p>
        ) : null}
        {selected.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            No models selected. This account can serve every model it supports.
          </p>
        ) : null}
      </fieldset>
      {mutation.isError ? <p role="alert" className="text-sm text-destructive">{mutation.error.message}</p> : null}
      <Button size="sm" disabled={locked || !changed} onClick={() => mutation.mutate()}>
        {mutation.isPending ? "Saving..." : "Save allowed models"}
      </Button>
    </div>
  );
}
