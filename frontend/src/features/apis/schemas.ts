import { z } from "zod";

const ApiKeyTrendPointSchema = z.object({
  t: z.iso.datetime({ offset: true }),
  v: z.number(),
});

export const ApiKeyTrendsResponseSchema = z.object({
  keyId: z.string(),
  cost: z.array(ApiKeyTrendPointSchema),
  tokens: z.array(ApiKeyTrendPointSchema),
});

const ApiKeyDailyUsagePointSchema = z.object({
  date: z.iso.date(),
  v: z.number(),
});

const ApiKeyDailyUsageSeriesSchema = z.object({
  keyId: z.string(),
  name: z.string(),
  points: z.array(ApiKeyDailyUsagePointSchema),
});

export const ApiKeyDailyUsageResponseSchema = z.object({
  startDate: z.iso.date(),
  endDate: z.iso.date(),
  cost: z.array(ApiKeyDailyUsageSeriesSchema).max(10),
  tokens: z.array(ApiKeyDailyUsageSeriesSchema).max(10),
});

const ApiKeyAccountCostSchema = z.object({
  accountId: z.string().nullable().default(null),
  email: z.string().nullable().default(null),
  costUsd: z.number().default(0),
  isDeleted: z.boolean().default(false),
});

export const ApiKeyUsage7DayResponseSchema = z.object({
  keyId: z.string(),
  totalTokens: z.number().int(),
  totalCostUsd: z.number(),
  totalRequests: z.number().int(),
  cachedInputTokens: z.number().int(),
  accountCosts: z.array(ApiKeyAccountCostSchema).default([]),
});

export type ApiKeyAccountCost = z.infer<typeof ApiKeyAccountCostSchema>;
export type ApiKeyTrendPoint = z.infer<typeof ApiKeyTrendPointSchema>;
export type ApiKeyTrendsResponse = z.infer<typeof ApiKeyTrendsResponseSchema>;
export type ApiKeyDailyUsageSeries = z.infer<typeof ApiKeyDailyUsageSeriesSchema>;
export type ApiKeyDailyUsageResponse = z.infer<typeof ApiKeyDailyUsageResponseSchema>;
export type ApiKeyUsage7DayResponse = z.infer<typeof ApiKeyUsage7DayResponseSchema>;
