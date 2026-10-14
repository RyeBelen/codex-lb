import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HttpResponse, http } from "msw";
import { describe, expect, it, vi } from "vitest";

import { ModelSourceCreateDialog } from "@/features/model-sources/components/model-source-create-dialog";
import { createApiKey } from "@/test/mocks/factories";
import { server } from "@/test/mocks/server";
import { renderWithProviders } from "@/test/utils";

describe("ModelSourceCreateDialog", () => {
  it("creates an automatic source when model IDs are blank", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    renderWithProviders(
      <ModelSourceCreateDialog
        open
        busy={false}
        onOpenChange={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    await user.type(screen.getByLabelText("Name"), "Automatic source");
    await user.type(screen.getByLabelText("Base URL"), "https://auto.example/v1");
    await user.type(screen.getByLabelText("Models"), ",  ,");
    expect(screen.getByText(/startup and every 5 minutes/)).toBeInTheDocument();
    expect(screen.getByRole("checkbox", { name: "Streaming" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: "Responses" })).toBeEnabled();

    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].models).toEqual([]);
  });

  it("submits selected API keys from a scrollable dialog", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    server.use(
      http.get("/api/api-keys/", () =>
        HttpResponse.json([
          createApiKey({ id: "key_one", name: "Personal", keyPrefix: "sk-safe-one" }),
        ]),
      ),
    );

    renderWithProviders(
      <ModelSourceCreateDialog
        open
        busy={false}
        onOpenChange={vi.fn()}
        onSubmit={onSubmit}
      />,
    );

    expect(screen.getByRole("dialog")).toHaveClass(
      "max-h-[calc(100dvh-2rem)]",
      "overflow-y-auto",
    );
    await user.type(screen.getByLabelText("Name"), "Local source");
    await user.type(screen.getByLabelText("Base URL"), "https://local.example/v1");
    await user.type(screen.getByLabelText("Models"), "local-model");
    await user.click(await screen.findByRole("checkbox", { name: /Personal sk-safe-one/ }));
    await user.click(screen.getByRole("button", { name: "Create" }));

    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(onSubmit.mock.calls[0][0].allowedApiKeyIds).toEqual(["key_one"]);
  });
});
