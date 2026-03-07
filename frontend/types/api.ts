export type IsolationPolicy = "open" | "isolated" | "inherit_only" | "visible_only";
export type Role = "owner" | "admin" | "member" | "viewer";

export interface OrgUnit {
  id: string;
  name: string;
  slug: string;
  parent: string | null;
  node_type: string;
  isolation_policy: IsolationPolicy;
}

export interface Membership {
  id: string;
  user: number;
  org_unit: string;
  role: Role;
}

export interface APIKeyList {
  id: string;
  name: string;
  prefix: string;
  org_unit: string;
  role: Role;
  expires_at: string | null;
  last_used_at: string | null;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}
