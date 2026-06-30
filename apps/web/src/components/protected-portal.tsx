"use client";

import type { Role } from "@english-ai-writing/shared";
import { useEffect, useState } from "react";

import { currentUser, logout, routeForRole } from "@/lib/auth";

type PortalState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; user: { display_name: string; email: string; role: Role } };

type ProtectedPortalProps = {
  allowedRoles: Role[];
  title: string;
  subtitle: string;
  actions: string[];
};

export function ProtectedPortal({ allowedRoles, title, subtitle, actions }: ProtectedPortalProps) {
  const [state, setState] = useState<PortalState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    async function loadUser() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/";
        return;
      }
      if (!allowedRoles.includes(user.role)) {
        setState({ status: "denied", message: "Your role cannot access this page." });
        return;
      }
      setState({
        status: "ready",
        user: { display_name: user.display_name, email: user.email, role: user.role },
      });
    }
    void loadUser();
    return () => {
      active = false;
    };
  }, [allowedRoles]);

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  if (state.status === "loading") {
    return (
      <main className="flex min-h-screen items-center justify-center px-6 text-lg font-semibold text-ink">
        Loading secure workspace...
      </main>
    );
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold text-ink">Access denied</h1>
        <p className="mt-4 text-base leading-7 text-ink/65">{state.message}</p>
        <button
          type="button"
          onClick={() => {
            void currentUser().then((user) => {
              window.location.href = user ? routeForRole(user.role) : "/";
            });
          }}
          className="mt-8 btn btn-primary btn-lg"
        >
          Return to my workspace
        </button>
      </main>
    );
  }

  return (
    <main className="app-shell-narrow">
      <header className="app-header">
        <div>
          <p className="eyebrow">
            W F Joseph Lee Primary School
          </p>
          <h1 className="page-title">{title}</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-sm font-semibold text-ink">{state.user.display_name}</p>
            <p className="text-xs text-ink/55">{state.user.role}</p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="btn btn-secondary"
          >
            Logout
          </button>
        </div>
      </header>

      <section className="grid flex-1 items-center gap-8 py-12 md:grid-cols-[0.9fr_1.1fr]">
        <div>
          <p className="text-sm font-semibold uppercase tracking-[0.12em] text-coral">
            Phase 1 secured workspace
          </p>
          <h2 className="mt-4 text-5xl font-semibold leading-tight text-ink">{title}</h2>
          <p className="mt-5 text-lg leading-8 text-ink/70">{subtitle}</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {actions.map((action) => (
            <div
              key={action}
              className="section-card text-base font-semibold text-ink"
            >
              {action}
              <p className="mt-3 text-sm font-normal leading-6 text-ink/55">
                Available in the next implementation phase.
              </p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
