import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { Checkbox } from "@/components/ui/checkbox";
import { listApiKeys } from "@/features/api-keys/api";

type ModelSourceApiKeyWhitelistProps = {
  selectedIds: string[];
  onChange: (selectedIds: string[]) => void;
};

export function ModelSourceApiKeyWhitelist({
  selectedIds,
  onChange,
}: ModelSourceApiKeyWhitelistProps) {
  const { t } = useTranslation();
  const apiKeys = useQuery({ queryKey: ["api-keys", "list"], queryFn: listApiKeys });
  const availableIds = new Set(apiKeys.data?.map((key) => key.id));
  const unavailableIds = apiKeys.data
    ? selectedIds.filter((id) => !availableIds.has(id))
    : apiKeys.isError
      ? selectedIds
      : [];

  const setChecked = (id: string, checked: boolean) => {
    onChange(
      checked
        ? [...new Set([...selectedIds, id])]
        : selectedIds.filter((selectedId) => selectedId !== id),
    );
  };

  return (
    <fieldset className="space-y-2 rounded-md border p-3">
      <legend className="px-1 text-sm font-medium">
        {t("modelSources.fields.allowedApiKeys")}
      </legend>
      <p className="text-xs text-muted-foreground">
        {t("modelSources.fields.allowedApiKeysDescription")}
      </p>

      {apiKeys.isPending ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("modelSources.fields.apiKeysLoading")}
        </p>
      ) : null}
      {apiKeys.isError ? (
        <p role="alert" className="text-sm text-destructive">
          {t("modelSources.fields.apiKeysLoadError")}
        </p>
      ) : null}

      {apiKeys.data || unavailableIds.length > 0 ? (
        <div className="max-h-48 space-y-2 overflow-y-auto overscroll-contain">
          {apiKeys.data?.map((key) => (
            <label key={key.id} className="flex items-center gap-2 text-sm">
              <Checkbox
                checked={selectedIds.includes(key.id)}
                onCheckedChange={(checked) => setChecked(key.id, checked === true)}
              />
              <span className="min-w-0 break-all">
                {key.name}{" "}
                <span className="text-muted-foreground">{key.keyPrefix}</span>
              </span>
            </label>
          ))}
          {unavailableIds.map((id) => (
            <label key={id} className="flex items-center gap-2 text-sm">
              <Checkbox checked onCheckedChange={() => setChecked(id, false)} />
              <span className="min-w-0 break-all">
                {t("modelSources.fields.unavailableApiKey", { id })}
              </span>
            </label>
          ))}
          {apiKeys.data?.length === 0 && unavailableIds.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              {t("modelSources.fields.noApiKeys")}
            </p>
          ) : null}
        </div>
      ) : null}
    </fieldset>
  );
}
