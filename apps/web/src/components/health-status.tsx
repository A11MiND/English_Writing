"use client";

import { useEffect, useState } from "react";

import type { ApiResponse, HealthPayload } from "@english-ai-writing/shared";

import { apiBaseUrl, readHealthStatus } from "@/lib/health";

type HealthState =
  | { status: "loading"; message: string }
  | { status: "ok"; payload: HealthPayload; requestId: string }
  | { status: "error"; message: string; requestId?: string };

export function HealthStatus() {
  const [state, setState] = useState<HealthState>({
    status: "loading",
    message: "Checking backend health...",
  });

  useEffect(() => {
    let active = true;

    async function checkHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/api/health`, {
          cache: "no-store",
          headers: { "x-request-id": "web-health-check" },
        });
        const body = (await response.json()) as ApiResponse<HealthPayload>;
        if (!active) return;

        const result = readHealthStatus(body);
        setState(result);
      } catch {
        if (!active) return;
        setState({
          status: "error",
          message: "Backend health check could not be reached.",
        });
      }
    }

    void checkHealth();

    return () => {
      active = false;
    };
  }, []);

  return (
    <aside className="surface-card p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className="text-lg font-semibold text-ink">Local health</h3>
          <p className="mt-1 text-sm text-ink/60">Frontend-to-backend connectivity</p>
        </div>
        <span
          className={`h-3 w-3 rounded-full ${
            state.status === "ok"
              ? "bg-moss"
              : state.status === "loading"
                ? "bg-coral"
                : "bg-red-500"
          }`}
          aria-label={`Health status: ${state.status}`}
        />
      </div>

      <div className="mt-6 muted-panel">
        {state.status === "ok" ? (
          <dl className="space-y-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">Service</dt>
              <dd className="font-medium text-ink">{state.payload.service}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">Status</dt>
              <dd className="font-medium text-moss">{state.payload.status}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">Environment</dt>
              <dd className="font-medium text-ink">{state.payload.environment}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-ink/60">Request ID</dt>
              <dd className="max-w-44 truncate font-mono text-xs text-ink">{state.requestId}</dd>
            </div>
          </dl>
        ) : (
          <p className="text-sm leading-6 text-ink/70">{state.message}</p>
        )}
      </div>

      <p className="mt-5 text-xs leading-5 text-ink/55">
        Product modules are wired through the Phase 8 baseline for local pilot testing.
      </p>
    </aside>
  );
}
