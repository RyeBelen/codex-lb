import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";

import { AccountAccess } from "@/features/accounts/components/account-access";
import { createApiKey } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";

function setup(restricted = false, apiKeyIds: string[] = [], readOnly = false, loadError = false) {
  let policy = { accountId: "acc", restricted, apiKeyIds };
  const saved: unknown[] = [];
  server.use(
    http.get("/api/accounts/acc/api-key-access", () => loadError
      ? new HttpResponse(null, { status: 500 }) : HttpResponse.json(policy)),
    http.get("/api/api-keys/", () => HttpResponse.json([
      createApiKey({ id: "one", name: "Personal", keyPrefix: "sk-clb-personal" }),
      createApiKey({ id: "two", name: "Shared clients", keyPrefix: "sk-clb-clients" }),
    ])),
    http.put("/api/accounts/acc/api-key-access", async ({ request }) => {
      const body = await request.json() as typeof policy;
      saved.push(body);
      policy = { ...body, accountId: "acc" };
      return HttpResponse.json(policy);
    }),
  );
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  const view = render(<QueryClientProvider client={client}>
    <AccountAccess accountId="acc" readOnly={readOnly} busy={false} />
  </QueryClientProvider>);
  return { ...view, saved, client };
}

describe("AccountAccess", () => {
  it("saves selected keys and reloads the saved policy", async () => {
    const user = userEvent.setup();
    const { saved, client } = setup();
    await user.click(await screen.findByRole("combobox", { name: "API key access mode" }));
    await user.click(screen.getByRole("option", { name: "Restricted to selected API keys" }));
    await user.click(screen.getByRole("checkbox", { name: /Personal/ }));
    await user.click(screen.getByRole("button", { name: "Save account access" }));
    await waitFor(() => expect(saved).toEqual([{ restricted: true, apiKeyIds: ["one"] }]));
    await client.invalidateQueries({ queryKey: ["accounts", "api-key-access", "acc"] });
    expect(screen.getByRole("checkbox", { name: /Personal/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Shared clients/ })).not.toBeChecked();
    expect(screen.getByRole("button", { name: "Save account access" })).toBeDisabled();
  });

  it("allows an explicit restricted policy with no keys", async () => {
    const user = userEvent.setup();
    const { saved } = setup();
    await user.click(await screen.findByRole("combobox", { name: "API key access mode" }));
    await user.click(screen.getByRole("option", { name: "Restricted to selected API keys" }));
    expect(screen.getByText(/will deny all client inference/)).toBeVisible();
    await user.click(screen.getByRole("button", { name: "Save account access" }));
    await waitFor(() => expect(saved).toEqual([{ restricted: true, apiKeyIds: [] }]));
  });

  it("clears grants when changing back to shared", async () => {
    const user = userEvent.setup();
    const { saved } = setup(true, ["one"]);
    await user.click(await screen.findByRole("combobox", { name: "API key access mode" }));
    await user.click(screen.getByRole("option", { name: "Shared" }));
    await user.click(screen.getByRole("button", { name: "Save account access" }));
    await waitFor(() => expect(saved).toEqual([{ restricted: false, apiKeyIds: [] }]));
  });

  it("retains edits after save failure", async () => {
    const user = userEvent.setup();
    setup(true, ["one"]);
    server.use(http.put("/api/accounts/acc/api-key-access", () => HttpResponse.json(
      { error: { code: "invalid_api_key_ids", message: "Unknown API key IDs" } }, { status: 400 },
    )));
    await user.click(await screen.findByRole("checkbox", { name: /Shared clients/ }));
    await user.click(screen.getByRole("button", { name: "Save account access" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Unknown API key IDs");
    expect(screen.getByRole("checkbox", { name: /Personal/ })).toBeChecked();
    expect(screen.getByRole("checkbox", { name: /Shared clients/ })).toBeChecked();
  });

  it("disables every control for read-only viewers", async () => {
    setup(true, ["one"], true);
    expect(await screen.findByRole("combobox", { name: "API key access mode" })).toBeDisabled();
    for (const checkbox of screen.getAllByRole("checkbox")) expect(checkbox).toBeDisabled();
    expect(screen.getByRole("button", { name: "Save account access" })).toBeDisabled();
  });

  it("does not offer defaults when loading the policy fails", async () => {
    setup(false, [], false, true);
    expect(await screen.findByRole("alert")).toHaveTextContent("Unable to load");
    expect(screen.queryByRole("button", { name: "Save account access" })).not.toBeInTheDocument();
  });
});
