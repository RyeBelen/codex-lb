import { useState } from "react";
import { CheckCircle2, Loader2, Trash2, XCircle } from "lucide-react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import type { UpstreamProxyEndpoint, UpstreamProxyEndpointCreateRequest, UpstreamProxyEndpointTestResponse } from "@/features/settings/schemas";

const SCHEME_OPTIONS = ["http", "https", "socks5", "socks5h"] as const;

type FormValues = {
  name: string;
  scheme: (typeof SCHEME_OPTIONS)[number];
  host: string;
  port: string;
  username: string;
  password: string;
  isActive: boolean;
};

export type ProxyEndpointCreateDialogProps = {
  open: boolean;
  busy: boolean;
  endpoint?: UpstreamProxyEndpoint | null;
  testResult: UpstreamProxyEndpointTestResponse | null;
  testing: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmit: (payload: UpstreamProxyEndpointCreateRequest) => Promise<unknown>;
  onTest: () => Promise<unknown>;
  onDelete: () => Promise<unknown>;
};

type ProxyEndpointCreateFormProps = {
  busy: boolean;
  endpoint?: UpstreamProxyEndpoint | null;
  onClose: () => void;
  onSubmit: (payload: UpstreamProxyEndpointCreateRequest) => Promise<unknown>;
};

function ProxyEndpointCreateForm({ busy, endpoint, onClose, onSubmit }: ProxyEndpointCreateFormProps) {
  const { t } = useTranslation();
  const formSchema = z.object({
    name: z.string().trim().min(1, t("upstreamProxy.validation.nameRequired")),
    scheme: z.enum(SCHEME_OPTIONS),
    host: z.string().trim().min(1, t("upstreamProxy.validation.hostRequired")),
    port: z.string().refine((value) => {
      const parsed = Number(value);
      return Number.isInteger(parsed) && parsed >= 1 && parsed <= 65535;
    }, t("upstreamProxy.validation.portInvalid")),
    username: z.string(),
    password: z.string(),
    isActive: z.boolean(),
  });
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: endpoint?.name ?? "",
      scheme: endpoint?.scheme ?? "http",
      host: endpoint?.host ?? "",
      port: String(endpoint?.port ?? 8080),
      username: endpoint?.username ?? "",
      password: "",
      isActive: endpoint?.isActive ?? true,
    },
  });

  const handleSubmit = async (values: FormValues) => {
    const username = values.username.trim();
    const payload: UpstreamProxyEndpointCreateRequest = {
      name: values.name.trim(),
      scheme: values.scheme,
      host: values.host.trim(),
      port: Number(values.port),
      username: username ? username : null,
      password: values.password ? values.password : null,
      isActive: values.isActive,
    };

    try {
      await onSubmit(payload);
    } catch {
      return;
    }

    onClose();
  };

  return (
    <Form {...form}>
      <form className="space-y-4" onSubmit={form.handleSubmit(handleSubmit)}>
        <FormField
          control={form.control}
          name="name"
          render={({ field }) => (
            <FormItem>
	              <FormLabel>{t("apiKeys.table.name")}</FormLabel>
	              <FormControl>
	                <Input {...field} autoComplete="off" placeholder={t("upstreamProxy.endpointDialog.placeholders.name")} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-[8rem_minmax(0,1fr)]">
          <FormField
            control={form.control}
            name="scheme"
            render={({ field }) => (
              <FormItem>
	                <FormLabel>{t("upstreamProxy.endpointDialog.scheme")}</FormLabel>
                <Select value={field.value} onValueChange={field.onChange}>
                  <FormControl>
                    <SelectTrigger className="w-full">
                      <SelectValue />
                    </SelectTrigger>
                  </FormControl>
                  <SelectContent>
                    {SCHEME_OPTIONS.map((scheme) => (
                      <SelectItem key={scheme} value={scheme}>
                        {scheme}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="host"
            render={({ field }) => (
              <FormItem>
	                <FormLabel>{t("upstreamProxy.endpointDialog.host")}</FormLabel>
                <FormControl>
                  <Input {...field} autoComplete="off" placeholder="proxy.example.com" />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <FormField
          control={form.control}
          name="isActive"
          render={({ field }) => (
            <FormItem className="flex items-center justify-between rounded-lg border px-3 py-2">
              <FormLabel className="mb-0">{t("common.states.active")}</FormLabel>
              <FormControl>
                <Switch checked={field.value} onCheckedChange={field.onChange} />
              </FormControl>
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="port"
          render={({ field }) => (
            <FormItem>
	              <FormLabel>{t("upstreamProxy.endpointDialog.port")}</FormLabel>
              <FormControl>
                <Input {...field} inputMode="numeric" autoComplete="off" placeholder="8080" />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <div className="grid gap-4 sm:grid-cols-2">
          <FormField
            control={form.control}
            name="username"
            render={({ field }) => (
              <FormItem>
	                <FormLabel>{t("upstreamProxy.endpointDialog.username")}</FormLabel>
	                <FormControl>
	                  <Input {...field} autoComplete="off" placeholder={t("upstreamProxy.optional")} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />

          <FormField
            control={form.control}
            name="password"
            render={({ field }) => (
              <FormItem>
	                <FormLabel>{t("auth.login.passwordLabel")}</FormLabel>
                <FormControl>
	                  <Input {...field} type="password" autoComplete="new-password" placeholder={t("upstreamProxy.optional")} />
                </FormControl>
                {endpoint ? <FormDescription>{t("upstreamProxy.endpointDialog.passwordUnchanged")}</FormDescription> : null}
                <FormMessage />
              </FormItem>
            )}
          />
        </div>

        <DialogFooter className="mt-2">
          <Button type="submit" disabled={busy || form.formState.isSubmitting}>
            {endpoint ? t("common.actions.save") : t("upstreamProxy.actions.createEndpoint")}
          </Button>
        </DialogFooter>
      </form>
    </Form>
  );
}

export function ProxyEndpointCreateDialog({ open, busy, endpoint, testResult, testing, onOpenChange, onSubmit, onTest, onDelete }: ProxyEndpointCreateDialogProps) {
  const { t } = useTranslation();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const handleOpenChange = (nextOpen: boolean) => {
    if (!nextOpen) setConfirmDelete(false);
    onOpenChange(nextOpen);
  };
  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      {open ? (
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-md">
          <DialogHeader>
            <DialogTitle>
              {endpoint ? t("upstreamProxy.endpointDialog.editTitle") : t("upstreamProxy.endpointDialog.title")}
            </DialogTitle>
	            <DialogDescription>
	              {t("upstreamProxy.endpointDialog.description")}
	            </DialogDescription>
          </DialogHeader>
          <ProxyEndpointCreateForm
            busy={busy}
            endpoint={endpoint}
            onClose={() => handleOpenChange(false)}
            onSubmit={onSubmit}
          />
          {endpoint ? (
            <>
              <div className="flex items-center justify-between gap-2 border-t pt-3">
                <Button type="button" variant="outline" disabled={busy || testing} onClick={() => void onTest()}>
                  {testing ? <Loader2 className="mr-1 h-4 w-4 animate-spin" aria-hidden="true" /> : null}
                  {t("upstreamProxy.actions.test")}
                </Button>
                <Button type="button" variant="destructive" disabled={busy} onClick={() => setConfirmDelete(true)}>
                  <Trash2 className="mr-1 h-4 w-4" aria-hidden="true" />
                  {t("common.actions.delete")}
                </Button>
              </div>
              {testResult ? (
                <div className={testResult.ok ? "flex items-center gap-1 text-sm text-emerald-600" : "flex items-center gap-1 text-sm text-destructive"}>
                  {testResult.ok ? <CheckCircle2 className="h-4 w-4" aria-hidden="true" /> : <XCircle className="h-4 w-4" aria-hidden="true" />}
                  <span>
                    {testResult.ok ? t("upstreamProxy.endpoints.connectionOk") : t("upstreamProxy.endpoints.connectionFailed")}
                    {testResult.statusCode ? ` · HTTP ${testResult.statusCode}` : ""}
                    {testResult.elapsedMs !== null && testResult.elapsedMs !== undefined ? ` · ${testResult.elapsedMs}ms` : ""}
                    {!testResult.ok && testResult.error ? ` · ${testResult.error}` : ""}
                  </span>
                </div>
              ) : null}
              <ConfirmDialog
                open={confirmDelete}
                onOpenChange={setConfirmDelete}
                title={t("upstreamProxy.deleteDialog.title")}
                description={t("upstreamProxy.deleteDialog.description", { name: endpoint.name })}
                confirmLabel={t("common.actions.delete")}
                confirmDisabled={busy}
                keepOpenOnConfirm
                onConfirm={() => {
                  void onDelete().then(() => {
                    setConfirmDelete(false);
                    handleOpenChange(false);
                  }).catch(() => {});
                }}
              />
            </>
          ) : null}
        </DialogContent>
      ) : null}
    </Dialog>
  );
}
