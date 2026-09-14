import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import type { ModelRoutingPolicy } from "@/features/model-routing/api";
import { ModelRoutingSettings } from "@/features/model-routing/model-routing-settings";
import { createAccountSummary } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";

function setup(initial: ModelRoutingPolicy[] = [], disabled = false, accountsReady = true, loadError = false) {
  let rules = initial;
  const saved: ModelRoutingPolicy[] = [];
  server.use(
    http.get("/api/model-account-routing", () => loadError ? new HttpResponse(null, { status: 500 }) : HttpResponse.json({ rules })),
    http.put("/api/model-account-routing", async ({ request }) => {
      const body = await request.json() as ModelRoutingPolicy;
      saved.push(body);
      rules = rules.filter((rule) => rule.model !== body.model);
      if (body.restricted) rules.push(body);
      return HttpResponse.json(body);
    }),
  );
  const accounts = [
    createAccountSummary({ accountId: "pro1", displayName: "First Pro", planType: "pro" }),
    createAccountSummary({ accountId: "pro2", displayName: "Second Pro", planType: "pro" }),
    createAccountSummary({ accountId: "plus", displayName: "Plus account", planType: "plus" }),
  ];
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(<QueryClientProvider client={client}><ModelRoutingSettings accounts={accounts} accountsReady={accountsReady} disabled={disabled} /></QueryClientProvider>);
  return { saved };
}

describe("ModelRoutingSettings", () => {
  it("selects current Pro accounts and allows individual edits before saving", async () => {
    const user = userEvent.setup();
    const { saved } = setup();
    await user.click(await screen.findByRole("button", { name: "Add model rule" }));
    expect(screen.getByText(/Those accounts serve only their assigned models/)).toHaveTextContent("The model can also use other eligible accounts.");
    expect(screen.getByText(/Selected accounts only serve this model/)).toHaveTextContent("This model can also use unreserved accounts.");
    await user.type(screen.getByRole("combobox", { name: "Model ID" }), "GPT-6-astra");
    await user.click(screen.getByRole("button", { name: "Select Pro accounts" }));
    expect(screen.getByRole("checkbox", { name: /First Pro/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Second Pro/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Plus account/ })).not.toBeChecked();
    await user.click(screen.getByRole("checkbox", { name: /Second Pro/ }));
    await user.click(screen.getByRole("button", { name: "Save model rule" }));
    await user.click(await screen.findByRole("button", { name: "Edit gpt-6-astra" }));
    expect(saved).toEqual([{ model: "gpt-6-astra", restricted: true, accountIds: ["pro1"] }]);
    expect(screen.getByRole("checkbox", { name: /First Pro/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Second Pro/ })).not.toBeChecked();
  });

  it("explains empty reservations and can remove a reservation", async () => {
    const user = userEvent.setup();
    const { saved } = setup([{ model: "gpt-6-astra", restricted: true, accountIds: ["pro1"] }]);
    await user.click(await screen.findByRole("button", { name: "Edit gpt-6-astra" }));
    await user.click(screen.getByRole("button", { name: "Clear selection" }));
    expect(screen.getByText(/This rule reserves no accounts and does not block the model/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Save model rule" }));
    await user.click(await screen.findByRole("button", { name: "Edit gpt-6-astra" }));
    await user.click(screen.getByRole("combobox", { name: "Model routing mode" }));
    await user.click(screen.getByRole("option", { name: "Remove reservation" }));
    await user.click(screen.getByRole("button", { name: "Save model rule" }));
    await waitFor(() => expect(saved).toEqual([
      { model: "gpt-6-astra", restricted: true, accountIds: [] },
      { model: "gpt-6-astra", restricted: false, accountIds: [] },
    ]));
    expect(await screen.findByText("No account reservations configured.")).toBeVisible();
  });

  it("retains selection after a save error", async () => {
    const user = userEvent.setup();
    setup([{ model: "gpt-6-astra", restricted: true, accountIds: [] }]);
    server.use(http.put("/api/model-account-routing", () => HttpResponse.json({ error: { code: "invalid_routing_account", message: "Unknown account" } }, { status: 400 })));
    await user.click(await screen.findByRole("button", { name: "Edit gpt-6-astra" }));
    await user.click(screen.getByRole("checkbox", { name: /First Pro/ }));
    await user.click(screen.getByRole("button", { name: "Save model rule" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown account");
    expect(screen.getByRole("checkbox", { name: /First Pro/ })).toBeChecked();
  });

  it("allows read-only inspection but disables mutation controls", async () => {
    const user = userEvent.setup();
    setup([{ model: "gpt-6-astra", restricted: true, accountIds: [] }], true);
    expect(await screen.findByRole("button", { name: "Add model rule" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "View gpt-6-astra" }));
    for (const box of screen.getAllByRole("checkbox")) expect(box).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save model rule" })).toBeDisabled();
  });

  it("prevents editing without account data", async () => {
    setup([], false, false);
    expect(await screen.findByRole("button", { name: "Add model rule" })).toBeDisabled();
  });

  it("does not present an unrestricted default after load failure", async () => {
    setup([], false, true, true);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load");
    expect(screen.queryByRole("button", { name: "Add model rule" })).not.toBeInTheDocument();
  });
});
