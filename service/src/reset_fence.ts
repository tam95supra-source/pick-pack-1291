import { currentAuthority } from "./core";
import { apiError } from "./util";

type LegacyQueued = {
  authority_epoch?: unknown;
  service_generation?: unknown;
  payload?: Record<string, unknown>;
};

function fenceValues(event: LegacyQueued): { epoch: number; generation: string } {
  const payload = event.payload && typeof event.payload === "object" ? event.payload : {};
  const epoch = Number(event.authority_epoch ?? payload.authority_epoch ?? payload._authority_epoch ?? 0);
  const generation = String(event.service_generation ?? payload.service_generation ?? payload._service_generation ?? "").trim();
  return { epoch, generation };
}

/**
 * RESET_FENCE_V1
 * After an owner-locked operational reset, legacy PDA queues must prove which authority
 * epoch/generation they were created under. This prevents an old Beta queue from being
 * re-stamped with the new authority and resurrecting pre-reset operational data.
 */
export async function resetFenceGate(request: Request, env: Env): Promise<Response | null> {
  const u = new URL(request.url);
  if (request.method !== "POST" || !["/v1/legacy-mutations", "/v1/legacy-mutations/batch"].includes(u.pathname)) return null;

  const reset = await env.DB.prepare("SELECT value FROM system_meta WHERE key='m2_operational_reset_epoch'").first<{value:string}>();
  const resetEpoch = Number(reset?.value ?? 0);
  if (!Number.isInteger(resetEpoch) || resetEpoch <= 0) return null;

  const authority = await currentAuthority(env.DB);
  if (authority.authority_epoch < resetEpoch) return null;

  let parsed: unknown;
  try { parsed = await request.clone().json(); } catch { return null; }
  const body = parsed && typeof parsed === "object" ? parsed as Record<string, unknown> : {};
  const events = u.pathname.endsWith("/batch")
    ? (Array.isArray(body.events) ? body.events : [])
    : [body];

  for (const raw of events) {
    const event = raw && typeof raw === "object" ? raw as LegacyQueued : {};
    const { epoch, generation } = fenceValues(event);
    if (!Number.isInteger(epoch) || epoch !== authority.authority_epoch || generation !== authority.service_generation) {
      return apiError("RESET_FENCE_REQUIRED","CONFLICT",409,false,undefined,{
        current_epoch: authority.authority_epoch,
        current_generation: authority.service_generation,
        incoming_epoch: Number.isFinite(epoch) ? epoch : null,
        incoming_generation: generation || null,
      });
    }
  }
  return null;
}
