import { Switch } from "@/components/ui/switch";

export function ApiKeyAstraToggle({
  enabled,
  disabled,
  onChange,
}: {
  enabled: boolean;
  disabled?: boolean;
  onChange: (enabled: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border p-2">
      <div>
        <p className="text-sm font-medium">Allow GPT-6 Astra</p>
        <p className="text-xs text-muted-foreground">
          Only keys with this enabled can use Astra. Other model restrictions still apply.
        </p>
      </div>
      <Switch
        aria-label="Allow GPT-6 Astra"
        checked={enabled}
        disabled={disabled}
        onCheckedChange={onChange}
      />
    </div>
  );
}
