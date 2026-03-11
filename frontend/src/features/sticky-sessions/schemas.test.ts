import { describe, expect, it } from "vitest";

import {
  StickySessionEntrySchema,
  StickySessionsListResponseSchema,
  StickySessionsPurgeRequestSchema,
} from "@/features/sticky-sessions/schemas";

describe("StickySessionEntrySchema", () => {
  it("parses sticky session metadata", () => {
    const parsed = StickySessionEntrySchema.parse({
      key: "thread_123",
      accountId: "acc_1",
      kind: "prompt_cache",
      createdAt: "2026-03-10T12:00:00Z",
      updatedAt: "2026-03-10T12:05:00Z",
      expiresAt: "2026-03-10T12:10:00Z",
      isStale: false,
    });

    expect(parsed.kind).toBe("prompt_cache");
    expect(parsed.expiresAt).toBe("2026-03-10T12:10:00Z");
  });
});

describe("StickySessionsListResponseSchema", () => {
  it("defaults entries to an empty array", () => {
    const parsed = StickySessionsListResponseSchema.parse({});
    expect(parsed.entries).toEqual([]);
  });
});

describe("StickySessionsPurgeRequestSchema", () => {
  it("defaults staleOnly to true", () => {
    const parsed = StickySessionsPurgeRequestSchema.parse({});
    expect(parsed.staleOnly).toBe(true);
  });
});
