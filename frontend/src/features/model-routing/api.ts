import { z } from "zod";

import { get, put } from "@/lib/api-client";

export const ModelRoutingPolicySchema = z.object({
  model: z.string().trim().min(1).max(128),
  restricted: z.boolean(),
  accountIds: z.array(z.string()),
});
export const ModelRoutingPoliciesSchema = z.object({ rules: z.array(ModelRoutingPolicySchema) });
export type ModelRoutingPolicy = z.infer<typeof ModelRoutingPolicySchema>;

export function listModelRoutingPolicies() {
  return get("/api/model-account-routing", ModelRoutingPoliciesSchema);
}

export function saveModelRoutingPolicy(policy: ModelRoutingPolicy) {
  return put("/api/model-account-routing", ModelRoutingPolicySchema, {
    body: ModelRoutingPolicySchema.parse(policy),
  });
}
