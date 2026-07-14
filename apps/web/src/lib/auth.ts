import type { ApiResponse, AuthPayload, AuthenticatedUser, Role } from "@english-ai-writing/shared";

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL === "same-origin"
    ? ""
    : process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

export function routeForRole(role: Role) {
  if (role === "STUDENT") return "/student/writing";
  if (role === "TEACHER") return "/teacher";
  return "/admin";
}

async function parseApiResponse<T>(response: Response): Promise<ApiResponse<T>> {
  return (await response.json()) as ApiResponse<T>;
}

export async function login(email: string, password: string): Promise<AuthenticatedUser> {
  const response = await fetch(`${apiBaseUrl}/api/auth/login`, {
    method: "POST",
    credentials: "include",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  const body = await parseApiResponse<AuthPayload>(response);
  if (!body.success) throw new Error(body.message);
  return body.data.user;
}

export async function currentUser(): Promise<AuthenticatedUser | null> {
  const response = await fetch(`${apiBaseUrl}/api/auth/session`, {
    credentials: "include",
    cache: "no-store",
  });
  const body = await parseApiResponse<{ user: AuthenticatedUser | null }>(response);
  if (!body.success) return null;
  return body.data.user;
}

export async function logout(): Promise<void> {
  await fetch(`${apiBaseUrl}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}
