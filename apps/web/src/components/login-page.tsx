"use client";

import { FormEvent, useEffect, useState } from "react";

import { currentUser, login, routeForRole } from "@/lib/auth";

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let active = true;
    async function checkSession() {
      const user = await currentUser();
      if (active && user) {
        window.location.href = routeForRole(user.role);
      }
    }
    void checkSession();
    return () => {
      active = false;
    };
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const user = await login(email, password);
      window.location.href = routeForRole(user.role);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <section>
        <p className="text-sm font-semibold uppercase tracking-[0.18em] text-moss">
          W F Joseph Lee Primary School
        </p>
        <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-tight text-ink md:text-7xl">
          English AI Writing Platform
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-ink/70">
          Sign in to access school-based writing tasks, Practice Mode, Exam Mode,
          AI-assisted marking review and class reporting.
        </p>
      </section>

      <section className="surface-card p-7">
        <div>
          <h2 className="text-2xl font-semibold text-ink">Login</h2>
          <p className="mt-2 text-sm leading-6 text-ink/60">
            Authentication is handled by the configured OpenAuth service. The
            application only creates its own HTTP-only session after OpenAuth succeeds.
          </p>
        </div>

        <form className="mt-7 space-y-5" onSubmit={onSubmit}>
          <label className="block">
            <span className="text-sm font-semibold text-ink">Email</span>
            <input
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="form-control-lg mt-2"
              type="email"
              autoComplete="email"
              required
            />
          </label>

          <label className="block">
            <span className="text-sm font-semibold text-ink">Password</span>
            <input
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="form-control-lg mt-2"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>

          {error ? (
            <p className="notice-error">
              {error}
            </p>
          ) : null}

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-full"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-xs leading-5 text-ink/55">
          Session IDs are stored only in HTTP-only cookies. Do not use browser local
          storage for authentication tokens.
        </p>
      </section>
    </main>
  );
}
