import { get } from "@/lib/api-client";

import { API_KEYS_BASE_PATH } from "@/features/api-keys/api";
import {
  ApiKeyDailyUsageResponseSchema,
  ApiKeyTrendsResponseSchema,
  ApiKeyUsage7DayResponseSchema,
} from "@/features/apis/schemas";

export function getApiKeyDailyUsage() {
  return get(`${API_KEYS_BASE_PATH}/usage-daily`, ApiKeyDailyUsageResponseSchema);
}

export function getApiKeyTrends(keyId: string) {
  return get(
    `${API_KEYS_BASE_PATH}/${encodeURIComponent(keyId)}/trends`,
    ApiKeyTrendsResponseSchema,
  );
}

export function getApiKeyUsage7Day(keyId: string) {
  return get(
    `${API_KEYS_BASE_PATH}/${encodeURIComponent(keyId)}/usage-7d`,
    ApiKeyUsage7DayResponseSchema,
  );
}
