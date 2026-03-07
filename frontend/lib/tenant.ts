interface TenantEntry {
  slug: string;
  domains: string[];
}

/**
 * Resolve a tenant slug from a hostname using the NEXT_PUBLIC_TENANTS config.
 * Returns null if no tenant matches (caller should show an error or fallback).
 */
export function getTenantSlugFromHostname(hostname: string): string | null {
  const raw = process.env.NEXT_PUBLIC_TENANTS;
  if (!raw) return null;

  let tenants: TenantEntry[];
  try {
    tenants = JSON.parse(raw) as TenantEntry[];
  } catch {
    return null;
  }

  const host = hostname.split(":")[0]; // strip port
  return tenants.find((t) => t.domains.includes(host))?.slug ?? null;
}
