import { useWatch, type Control } from "react-hook-form";
import { useTranslation } from "react-i18next";

import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ModelSourceApiKeyWhitelist } from "@/features/model-sources/components/model-source-api-key-whitelist";
import type {
  ModelSourceDraft,
  ModelSourceFormValues,
} from "@/features/model-sources/components/model-source-form";
import { parseReasoningEffortsInput } from "@/features/model-sources/components/model-source-form";
import type { ModelSourceModel } from "@/features/model-sources/schemas";

type ModelSourceFormFieldsProps = {
  control: Control<ModelSourceFormValues>;
  draft: ModelSourceDraft;
  updateDraft: (patch: Partial<ModelSourceDraft>) => void;
  apiKeyLabel: string;
  apiKeyPlaceholder?: string;
  discoveredModels?: ModelSourceModel[];
};

const CAPABILITY_TOGGLES = [
  ["supportsChatCompletions", "modelSources.capabilities.chatCompletions", false] as const,
  ["supportsResponses", "modelSources.capabilities.responses", false] as const,
  ["supportsAudioTranscriptions", "modelSources.capabilities.audioTranscriptions", false] as const,
  ["supportsEmbeddings", "modelSources.capabilities.embeddings", false] as const,
  ["supportsStreaming", "modelSources.capabilities.streaming", true] as const,
  ["supportsTools", "modelSources.capabilities.tools", true] as const,
  ["supportsVision", "modelSources.capabilities.vision", true] as const,
  ["supportsReasoning", "modelSources.capabilities.reasoning", true] as const,
];

const DEFAULT_REASONING_EFFORTS = ["low", "medium", "high"];

export function ModelSourceFormFields({
  control,
  draft,
  updateDraft,
  apiKeyLabel,
  apiKeyPlaceholder,
  discoveredModels,
}: ModelSourceFormFieldsProps) {
  const { t } = useTranslation();
  const models = useWatch({ control, name: "models" });
  const automatic = !models.split(/[\n,]/).some((model) => model.trim().length > 0);
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        <FormField
          control={control}
          name="name"
          render={({ field }) => (
            <FormItem>
	              <FormLabel>{t("apiKeys.table.name")}</FormLabel>
              <FormControl>
                <Input {...field} autoComplete="off" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={control}
          name="baseUrl"
          render={({ field }) => (
            <FormItem>
	              <FormLabel>{t("modelSources.fields.baseUrl")}</FormLabel>
              <FormControl>
                <Input {...field} placeholder="https://api.example.com/v1" autoComplete="off" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
      </div>

      <FormField
        control={control}
        name="apiKey"
        render={({ field }) => (
          <FormItem>
            <FormLabel>{apiKeyLabel}</FormLabel>
            <FormControl>
              <Input {...field} type="password" autoComplete="new-password" placeholder={apiKeyPlaceholder} />
            </FormControl>
            <FormMessage />
          </FormItem>
        )}
      />

      <ModelSourceApiKeyWhitelist
        selectedIds={draft.allowedApiKeyIds}
        onChange={(allowedApiKeyIds) => updateDraft({ allowedApiKeyIds })}
      />

      <FormField
        control={control}
        name="models"
        render={({ field }) => (
          <FormItem>
	            <FormLabel>{t("apiKeys.table.models")}</FormLabel>
            <FormControl>
              <Input {...field} placeholder="deepseek-v4-flash, local-coder" autoComplete="off" />
            </FormControl>
            <p className="text-xs text-muted-foreground">
              {t("modelSources.fields.modelsDescription")}
            </p>
            <FormMessage />
          </FormItem>
        )}
      />

      {automatic && discoveredModels ? (
        <div className="space-y-2 rounded-md border bg-muted/30 p-3">
          <div className="text-sm font-medium">{t("modelSources.fields.discoveredModels")}</div>
          <p className="text-xs text-muted-foreground">
            {t("modelSources.fields.discoveredModelsDescription")}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {discoveredModels.length > 0 ? (
              discoveredModels.map((model) => (
                <Badge key={model.id} variant={model.isEnabled ? "outline" : "secondary"}>
                  {model.displayName || model.model}
                </Badge>
              ))
            ) : (
              <span className="text-xs text-muted-foreground">
                {t("modelSources.fields.noDiscoveredModels")}
              </span>
            )}
          </div>
        </div>
      ) : null}

      {automatic ? (
        <p className="text-xs text-muted-foreground">
          {t("modelSources.fields.automaticMetadataDescription")}
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-1">
	          <label className="text-sm font-medium">{t("modelSources.fields.contextWindow")}</label>
          <Input
            value={draft.contextWindow}
            onChange={(event) => updateDraft({ contextWindow: event.target.value })}
            placeholder="e.g. 32768"
            inputMode="numeric"
            disabled={automatic}
          />
        </div>
        <div className="space-y-1">
	          <label className="text-sm font-medium">{t("modelSources.fields.maxOutputTokens")}</label>
          <Input
            value={draft.maxOutputTokens}
            onChange={(event) => updateDraft({ maxOutputTokens: event.target.value })}
            placeholder="e.g. 4096"
            inputMode="numeric"
            disabled={automatic}
          />
        </div>
      </div>

      <div className="space-y-2">
	        <div className="text-sm font-medium">{t("modelSources.fields.pricing")}</div>
	        <p className="text-xs text-muted-foreground">
	          {t("modelSources.fields.pricingDescription")}
	        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1">
	            <label className="text-xs text-muted-foreground">{t("common.units.input")}</label>
            <Input
              value={draft.inputPer1M}
              onChange={(event) => updateDraft({ inputPer1M: event.target.value })}
              placeholder="0.00"
              inputMode="decimal"
              disabled={automatic}
            />
          </div>
          <div className="space-y-1">
	            <label className="text-xs text-muted-foreground">{t("common.units.cached")}</label>
            <Input
              value={draft.cachedInputPer1M}
              onChange={(event) => updateDraft({ cachedInputPer1M: event.target.value })}
              placeholder="0.00"
              inputMode="decimal"
              disabled={automatic}
            />
          </div>
          <div className="space-y-1">
	            <label className="text-xs text-muted-foreground">{t("common.units.output")}</label>
            <Input
              value={draft.outputPer1M}
              onChange={(event) => updateDraft({ outputPer1M: event.target.value })}
              placeholder="0.00"
              inputMode="decimal"
              disabled={automatic}
            />
          </div>
        </div>
      </div>

      <div className="space-y-2">
	        <div className="text-sm font-medium">{t("modelSources.fields.audioPricing")}</div>
	        <p className="text-xs text-muted-foreground">
	          {t("modelSources.fields.audioPricingDescription")}
	        </p>
        <div className="grid gap-3 sm:grid-cols-3">
          <div className="space-y-1">
	            <label className="text-xs text-muted-foreground">{t("modelSources.fields.perMinute")}</label>
            <Input
              value={draft.audioPerMinute}
              onChange={(event) => updateDraft({ audioPerMinute: event.target.value })}
              placeholder="0.00"
              inputMode="decimal"
              disabled={automatic}
            />
          </div>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
	        {CAPABILITY_TOGGLES.map(([key, labelKey, providerOwned]) => (
          <label key={key} className="flex items-center gap-2 rounded-md border p-2 text-sm">
            <Checkbox
              checked={draft[key]}
              disabled={automatic && providerOwned}
              onCheckedChange={(checked) =>
                updateDraft({
                  [key]: checked === true,
                  ...(key === "supportsReasoning" && checked === true
                    ? {
                        reasoningEffortsInput:
                          draft.reasoningEffortsInput || DEFAULT_REASONING_EFFORTS.join(", "),
                        reasoningEfforts:
                          draft.reasoningEfforts.length > 0
                            ? draft.reasoningEfforts
                            : DEFAULT_REASONING_EFFORTS,
                        defaultReasoningEffort: draft.defaultReasoningEffort || "medium",
                      }
                    : {}),
                })
              }
            />
	            {t(labelKey)}
          </label>
        ))}
      </div>

      {draft.supportsReasoning ? (
        <div className="space-y-3 rounded-md border p-3">
          <div>
            <div className="text-sm font-medium">{t("modelSources.fields.reasoningEfforts")}</div>
            <p className="text-xs text-muted-foreground">
              {t("modelSources.fields.reasoningEffortsDescription")}
            </p>
          </div>

          <div className="space-y-1">
            <label className="text-xs text-muted-foreground" htmlFor="model-source-reasoning-efforts">
              {t("modelSources.fields.reasoningEfforts")}
            </label>
            <Input
              id="model-source-reasoning-efforts"
              aria-label={t("modelSources.fields.reasoningEfforts")}
              value={draft.reasoningEffortsInput}
              onChange={(event) => {
                const reasoningEffortsInput = event.target.value;
                const reasoningEfforts = parseReasoningEffortsInput(reasoningEffortsInput);
                updateDraft({
                  reasoningEffortsInput,
                  reasoningEfforts,
                  defaultReasoningEffort: reasoningEfforts.includes(draft.defaultReasoningEffort)
                    ? draft.defaultReasoningEffort
                    : (reasoningEfforts[0] ?? ""),
                });
              }}
              placeholder={t("modelSources.fields.reasoningEffortsPlaceholder")}
              autoComplete="off"
              disabled={automatic}
            />
          </div>

          <div className="space-y-1">
            <label
              className="text-xs text-muted-foreground"
              htmlFor="model-source-default-reasoning-effort"
            >
              {t("modelSources.fields.defaultReasoningEffort")}
            </label>
            <Select
              value={draft.defaultReasoningEffort}
              onValueChange={(value) => updateDraft({ defaultReasoningEffort: value })}
              disabled={automatic || draft.reasoningEfforts.length === 0}
            >
              <SelectTrigger
                id="model-source-default-reasoning-effort"
                aria-label={t("modelSources.fields.defaultReasoningEffort")}
                className="w-full"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {draft.reasoningEfforts.map((effort) => (
                  <SelectItem key={effort} value={effort}>
                    {effort}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
      ) : null}
    </>
  );
}
