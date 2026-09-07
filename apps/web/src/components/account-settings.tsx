"use client";

import { useEffect, useState, type FormEvent } from "react";

import { AppShell, ProductTopNav, type AppShellUser } from "@/components/app-shell";
import { SkeletonScreen } from "@/components/skeleton";
import { currentUser, logout } from "@/lib/auth";
import { changeOwnPassword } from "@/lib/school-data";

type AccountState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | { status: "ready"; user: AppShellUser };

export function AccountSettings() {
  const [state, setState] = useState<AccountState>({ status: "loading" });
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    let active = true;
    async function load() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/login";
        return;
      }
      setState({
        status: "ready",
        user: { display_name: user.display_name, email: user.email, role: user.role },
      });
    }
    void load().catch((loadError) => {
      setState({
        status: "denied",
        message: loadError instanceof Error ? loadError.message : "Unable to open your account.",
      });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (newPassword !== confirmPassword) {
      setError("The two new passwords do not match.");
      return;
    }
    if (newPassword.length < 8) {
      setError("Use at least 8 characters for the new password.");
      return;
    }
    setBusy(true);
    try {
      await changeOwnPassword(currentPassword, newPassword);
      setNotice("Your password has been changed. Use it the next time you sign in.");
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Unable to change your password.");
    } finally {
      setBusy(false);
    }
  }

  if (state.status === "loading") {
    return <SkeletonScreen label="Loading your account..." variant="page" />;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <div>
          <h1 className="screen-title">Account unavailable</h1>
          <p className="lead">{state.message}</p>
        </div>
      </main>
    );
  }

  const form = (
    <main className="container">
      <section className="panel" style={{ maxWidth: 620 }}>
        <div className="panel-header">
          <div>
            <h2 className="panel-title">Change your password</h2>
            <p className="panel-subtitle">
              Signed in as {state.user.display_name} ({state.user.email}).
            </p>
          </div>
        </div>
        <form className="form-grid" onSubmit={(event) => void onSubmit(event)}>
          <div className="field">
            <label htmlFor="current-password">Current password</label>
            <input
              id="current-password"
              className="input"
              type="password"
              autoComplete="current-password"
              value={currentPassword}
              onChange={(event) => setCurrentPassword(event.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="new-password">New password</label>
            <input
              id="new-password"
              className="input"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={newPassword}
              onChange={(event) => setNewPassword(event.target.value)}
              required
            />
            <p className="panel-subtitle">At least 8 characters.</p>
          </div>
          <div className="field">
            <label htmlFor="confirm-password">Repeat new password</label>
            <input
              id="confirm-password"
              className="input"
              type="password"
              autoComplete="new-password"
              minLength={8}
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
            />
          </div>
          {error ? <p className="notice-error">{error}</p> : null}
          {notice ? <p className="notice-success">{notice}</p> : null}
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Changing…" : "Change password"}
          </button>
        </form>
      </section>
    </main>
  );

  if (state.user.role === "STUDENT") {
    return (
      <ProductTopNav
        active="Account"
        links={[
          { href: "/student/writing", label: "My Writing" },
          { href: "/student/practice", label: "My Practice" },
          { href: "/student/writing?view=feedback", label: "Feedback" },
          { href: "/account", label: "Account" },
        ]}
        onLogout={() => void onLogout()}
      >
        {form}
      </ProductTopNav>
    );
  }

  return (
    <AppShell
      title="Your account"
      subtitle="Update the password you use to sign in."
      user={state.user}
      onLogout={() => void onLogout()}
    >
      {form}
    </AppShell>
  );
}
