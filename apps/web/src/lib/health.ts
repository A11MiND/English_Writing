import type { ApiResponse, HealthPayload } from "@english-ai-writing/shared";

export const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

type HealthResult =
  | { status: "ok"; payload: HealthPayload; requestId: string }
  | { status: "error"; message: string; requestId?: string };

export function readHealthStatus(response: ApiResponse<HealthPayload>): HealthResult {
  if (!response.success) {
    return {
      status: "error",
      message: response.message,
      requestId: response.request_id,
    };
  }

  return {
    status: "ok",
    payload: response.data,
    requestId: response.request_id,
  };
}
