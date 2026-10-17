/**
 * Auth mode helper for frontends.
 * Cloud Run deploys use demo role headers (VITE_AUTH_MODE=demo).
 */

export function authMode(): "demo" {
  return "demo";
}

/** Always null in demo mode — API client sends X-Demo-* headers instead. */
export async function getIdToken(_forceRefresh = false): Promise<string | null> {
  return null;
}
