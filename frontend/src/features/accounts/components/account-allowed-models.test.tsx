import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { AccountAllowedModels } from "@/features/accounts/components/account-allowed-models";
import type { AccountAllowedModels as AllowedModelsPolicy } from "@/features/accounts/schemas";
import { server } from "@/test/mocks/server";

const basePolicy: AllowedModelsPolicy = {
  accountId: "acc",
  allowedModels: [],
  availableModels: [
    { id: "gpt-6-astra", name: "GPT-6 Astra" },
    { id: "gpt-6-sol", name: "GPT-6 Sol" },
  ],
  catalogAvailable: true,
};

function setup(overrides: Partial<AllowedModelsPolicy> = {}, readOnly = false, loadError = false) {
  let policy = { ...basePolicy, ...overrides };
  const saved: unknown[] = [];
  server.use(
    http.get("/api/accounts/acc/allowed-models", () => loadError
      ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(policy)),
    http.put("/api/accounts/acc/allowed-models", async ({ request }) => {
      const body = await request.json() as { allowedModels: string[] };
      saved.push(body);
      policy = { ...policy, allowedModels: body.allowedModels };
      return HttpResponse.json(policy);
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(<QueryClientProvider client={client}>
    <AccountAllowedModels accountId="acc" readOnly={readOnly} busy={false} />
  </QueryClientProvider>);
  return { ...view, saved, client };
}

describe("AccountAllowedModels", () => {
  it("saves checked models and explains that an empty selection allows all", async () => {
    const user = userEvent.setup();
    const { saved } = setup();
    expect(await screen.findByText(/No models selected.*every model it supports/)).toBeVisible();
    await user.click(screen.getByRole("checkbox", { name: /GPT-6 Sol/ }));
    await user.click(screen.getByRole("button", { name: "Save allowed models" }));
    await waitFor(() => expect(saved).toEqual([{ allowedModels: ["gpt-6-sol"] }]));
    expect(screen.getByRole("button", { name: "Save allowed models" })).toBeDisabled();
  });

  it("keeps an unavailable selected model visible and removable", async () => {
    const user = userEvent.setup();
    const { saved } = setup({ allowedModels: ["retired-model"] });
    const stale = await screen.findByRole("checkbox", { name: /Unavailable model \(retired-model\)/ });
    expect(stale).toBeChecked();
    await user.click(stale);
    await user.click(screen.getByRole("button", { name: "Save allowed models" }));
    await waitFor(() => expect(saved).toEqual([{ allowedModels: [] }]));
  });

  it("edits known models and saved selections while account support is unverified", async () => {
    const user = userEvent.setup();
    const unavailable = setup({ catalogAvailable: false, allowedModels: ["retired-model"] });
    expect(await screen.findByText(/model catalog is unavailable/)).toBeVisible();
    expect(screen.getByText(/support is unverified/)).toBeVisible();
    await user.click(screen.getByRole("checkbox", { name: /Saved model \(retired-model\)/ }));
    await user.click(screen.getByRole("checkbox", { name: /GPT-6 Sol/ }));
    await user.click(screen.getByRole("button", { name: "Save allowed models" }));
    await waitFor(() => expect(unavailable.saved).toEqual([{ allowedModels: ["gpt-6-sol"] }]));
    unavailable.unmount();

    const noKnownModels = setup({ catalogAvailable: false, availableModels: [], allowedModels: ["retired-model"] });
    const stale = await screen.findByRole("checkbox", { name: /Saved model \(retired-model\)/ });
    await user.click(stale);
    await user.click(screen.getByRole("button", { name: "Save allowed models" }));
    await waitFor(() => expect(noKnownModels.saved).toEqual([{ allowedModels: [] }]));
    noKnownModels.unmount();

    setup({}, false, true);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load allowed models");
  });

  it("disables controls for read-only viewers and retains edits after a save failure", async () => {
    const readOnly = setup({ catalogAvailable: false }, true);
    expect(await screen.findByRole("checkbox", { name: /GPT-6 Astra/ })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save allowed models" })).toBeDisabled();
    readOnly.unmount();

    const user = userEvent.setup();
    setup();
    server.use(http.put("/api/accounts/acc/allowed-models", () => HttpResponse.json(
      { error: { code: "routing_policy_conflict", message: "Reload and try again" } }, { status: 409 },
    )));
    const sol = await screen.findByRole("checkbox", { name: /GPT-6 Sol/ });
    await user.click(sol);
    await user.click(screen.getByRole("button", { name: "Save allowed models" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Reload and try again");
    expect(sol).toBeChecked();
  });
});
