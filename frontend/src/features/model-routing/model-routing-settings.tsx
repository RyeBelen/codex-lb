import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useId, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { AccountSummary } from "@/features/accounts/schemas";
import { listModels } from "@/features/api-keys/api";
import { listModelRoutingPolicies, saveModelRoutingPolicy, type ModelRoutingPolicy } from "@/features/model-routing/api";

const QUERY_KEY = ["model-account-routing"];

export function ModelRoutingSettings({ accounts, accountsReady, disabled }: {
  accounts: AccountSummary[];
  accountsReady: boolean;
  disabled: boolean;
}) {
  const policies = useQuery({ queryKey: QUERY_KEY, queryFn: listModelRoutingPolicies });
  const models = useQuery({ queryKey: ["models"], queryFn: listModels });
  const [editing, setEditing] = useState<ModelRoutingPolicy | null>(null);
  const rules = policies.data?.rules ?? [];

  return (
    <section id="model-account-routing" aria-label="Model account routing" className="scroll-mt-16 space-y-3 rounded-xl border bg-card p-5">
      <h3 className="text-sm font-semibold">Model account routing</h3>
      <p className="text-sm text-muted-foreground">
        Reserve a model for selected accounts. Models without a rule use the normal account pool.
      </p>
      {policies.isError ? (
        <p role="alert" className="text-sm text-destructive">Unable to load model routing rules.</p>
      ) : policies.isPending ? (
        <p role="status">Loading model routing rules...</p>
      ) : (
        <>
          {rules.length === 0 ? <p className="text-sm text-muted-foreground">No model restrictions configured.</p> : (
            <ul className="space-y-2">
              {rules.map((rule) => (
                <li key={rule.model} className="flex flex-wrap items-center justify-between gap-2 rounded-lg border p-3 text-sm">
                  <div><span className="font-medium">{rule.model}</span><p className="text-muted-foreground">{rule.accountIds.length} selected accounts</p></div>
                  <Button variant="outline" size="sm" disabled={!accountsReady || editing !== null} onClick={() => setEditing(rule)}>
                    {disabled ? "View" : "Edit"} {rule.model}
                  </Button>
                </li>
              ))}
            </ul>
          )}
          {!accountsReady ? <p role="status" className="text-sm text-muted-foreground">Account selection is unavailable until accounts load.</p> : null}
          {editing ? (
            <ModelRoutingForm
              key={JSON.stringify(editing)}
              policy={editing}
              accounts={accounts}
              existingModels={rules.map((rule) => rule.model)}
              modelOptions={models.data?.models.filter((model) => !model.sourceOnly).map((model) => model.id) ?? []}
              disabled={disabled || !accountsReady}
              onClose={() => setEditing(null)}
            />
          ) : (
            <Button size="sm" disabled={disabled || !accountsReady} onClick={() => setEditing({ model: "", restricted: true, accountIds: [] })}>
              Add model rule
            </Button>
          )}
        </>
      )}
    </section>
  );
}

function ModelRoutingForm({ policy, accounts, existingModels, modelOptions, disabled, onClose }: {
  policy: ModelRoutingPolicy;
  accounts: AccountSummary[];
  existingModels: string[];
  modelOptions: string[];
  disabled: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const optionsId = useId();
  const [model, setModel] = useState(policy.model);
  const [restricted, setRestricted] = useState(policy.restricted);
  const [selected, setSelected] = useState(policy.accountIds);
  const mutation = useMutation({
    mutationFn: saveModelRoutingPolicy,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: QUERY_KEY });
      toast.success("Model routing rule saved");
      onClose();
    },
  });
  const normalizedModel = model.trim().toLowerCase();
  const duplicate = !policy.model && existingModels.includes(normalizedModel);
  const locked = disabled || mutation.isPending;
  const effectiveSelected = restricted ? selected : [];
  const changed = !policy.model || restricted !== policy.restricted ||
    JSON.stringify([...effectiveSelected].sort()) !== JSON.stringify([...policy.accountIds].sort());
  const validModel = /^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$/.test(normalizedModel) && normalizedModel.length <= 128;

  return (
    <form className="space-y-3 rounded-lg border bg-muted/30 p-4" onSubmit={(event) => {
      event.preventDefault();
      if (!locked && changed && validModel && !duplicate) {
        mutation.mutate({ model: normalizedModel, restricted, accountIds: effectiveSelected });
      }
    }}>
      <label className="block space-y-1 text-sm">
        <span>Model ID</span>
        <Input value={model} list={optionsId} maxLength={128} placeholder="gpt-6-astra" disabled={locked || Boolean(policy.model)} onChange={(event) => setModel(event.target.value)} />
      </label>
      <datalist id={optionsId}>{modelOptions.map((id) => <option key={id} value={id} />)}</datalist>
      {duplicate ? <p role="alert">This model already has a rule. Edit its existing rule.</p> : null}
      <Select value={restricted ? "restricted" : "unrestricted"} disabled={locked} onValueChange={(value) => setRestricted(value === "restricted")}>
        <SelectTrigger aria-label="Model routing mode"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="restricted">Only selected accounts</SelectItem>
          <SelectItem value="unrestricted">All eligible accounts</SelectItem>
        </SelectContent>
      </Select>
      {restricted ? (
        <fieldset disabled={locked} className="space-y-3">
          <legend className="text-sm font-medium">Allowed accounts</legend>
          <div className="flex flex-wrap gap-2">
            <Button type="button" size="sm" variant="outline" disabled={locked} onClick={() => setSelected(accounts.filter((account) => account.planType === "pro").map((account) => account.accountId))}>Select Pro accounts</Button>
            <Button type="button" size="sm" variant="outline" disabled={locked} onClick={() => setSelected([])}>Clear selection</Button>
          </div>
          <div className="max-h-64 space-y-2 overflow-y-auto">
            {accounts.map((account) => (
              <label key={account.accountId} className="flex items-center gap-2 text-sm">
                <Checkbox disabled={locked} checked={selected.includes(account.accountId)} onCheckedChange={(checked) => setSelected((current) => checked ? [...current, account.accountId] : current.filter((id) => id !== account.accountId))} />
                <span className="min-w-0 break-all">{account.displayName} <span className="text-muted-foreground">{account.planType}</span></span>
              </label>
            ))}
            {selected.filter((id) => !accounts.some((account) => account.accountId === id)).map((id) => (
              <label key={id} className="flex items-center gap-2 text-sm">
                <Checkbox checked disabled={locked} onCheckedChange={() => setSelected((current) => current.filter((value) => value !== id))} />
                <span>Unavailable account ({id})</span>
              </label>
            ))}
          </div>
          {selected.length === 0 ? <p role="status" className="text-sm">No accounts selected. This model will be blocked on the account pool.</p> : null}
          <p className="text-xs text-muted-foreground">There is no fallback to other accounts. Existing key permissions, model support, and usage limits still apply. Newly added accounts need explicit selection.</p>
        </fieldset>
      ) : <p className="text-sm text-muted-foreground">Saving removes this model's account restriction.</p>}
      {mutation.isError ? <p role="alert" className="text-sm text-destructive">{mutation.error.message}</p> : null}
      <div className="flex gap-2">
        <Button type="submit" size="sm" disabled={locked || !changed || !validModel || duplicate}>{mutation.isPending ? "Saving..." : "Save model rule"}</Button>
        <Button type="button" size="sm" variant="outline" disabled={mutation.isPending} onClick={onClose}>Cancel</Button>
      </div>
    </form>
  );
}
