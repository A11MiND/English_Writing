"use client";

import type { AccountStatus, AdminUser, AiServiceStatus, ImportRole, ImportUsersPayload, SchoolClass } from "@english-ai-writing/shared";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";

import { AppShell, type AppShellUser } from "@/components/app-shell";
import { currentUser, logout } from "@/lib/auth";
import {
  createClass,
  getAiServiceStatus,
  importUsers,
  listClasses,
  listUsers,
  parseUserCsv,
  updateUserStatus,
} from "@/lib/school-data";

type AdminState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | {
      status: "ready";
      user: AppShellUser;
      classes: SchoolClass[];
      users: AdminUser[];
      aiStatus: AiServiceStatus;
    };

const sampleStudentCsv =
  "email,display_name,student_number,level,class_name\nnew.student@wfjosephlee.edu.hk,New Student,S0101,P5,P5A";

export function AdminConsole() {
  const [state, setState] = useState<AdminState>({ status: "loading" });
  const [classForm, setClassForm] = useState({ name: "P4B", level: "P4", academic_year: "2026-2027" });
  const [importRole, setImportRole] = useState<ImportRole>("STUDENT");
  const [csv, setCsv] = useState(sampleStudentCsv);
  const [csvFile, setCsvFile] = useState<{ name: string; size: number } | null>(null);
  const [notice, setNotice] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [importResult, setImportResult] = useState<ImportUsersPayload | null>(null);

  async function refresh(user?: AppShellUser) {
    const [classes, users, aiStatus] = await Promise.all([listClasses(), listUsers(), getAiServiceStatus()]);
    setState((current) => {
      const shellUser = user ?? (current.status === "ready" ? current.user : null);
      if (!shellUser) return current;
      return { status: "ready", user: shellUser, classes, users, aiStatus };
    });
  }

  useEffect(() => {
    let active = true;
    async function load() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/";
        return;
      }
      if (!["SYSTEM_ADMIN", "SCHOOL_ADMIN"].includes(user.role)) {
        setState({ status: "denied", message: "Your role cannot access admin management." });
        return;
      }
      await refresh({ display_name: user.display_name, email: user.email, role: user.role });
    }
    void load().catch((error) => {
      setState({ status: "denied", message: error instanceof Error ? error.message : "Unable to load admin data." });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/";
  }

  async function onCreateClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      await createClass(classForm);
      setNotice(`Class ${classForm.name} created.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to create class.");
    }
  }

  async function onImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    const parsed = parseUserCsv(csv);
    if (parsed.errors.length > 0) {
      setError(parsed.errors.join(" "));
      return;
    }
    try {
      const result = await importUsers(importRole, parsed.rows);
      setImportResult(result);
      setNotice(`Import finished: ${result.successful_count} successful, ${result.rejected_count} rejected.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to import users.");
    }
  }

  async function onCsvFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".csv") && file.type !== "text/csv") {
      setError("Upload a .csv file.");
      return;
    }
    if (file.size > 512 * 1024) {
      setError("CSV file must be 512KB or smaller.");
      return;
    }
    setError("");
    setImportResult(null);
    setCsvFile({ name: file.name, size: file.size });
    setCsv(await file.text());
  }

  async function onUpdateStatus(userId: string, status: AccountStatus) {
    setNotice("");
    setError("");
    try {
      await updateUserStatus(userId, status);
      setNotice(`Account status updated to ${status}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update account status.");
    }
  }

  const parsedCsv = parseUserCsv(csv);
  const previewRows = parsedCsv.rows.slice(0, 3);

  if (state.status === "loading") {
    return <main className="loading-state">Loading admin console...</main>;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <h1 className="text-4xl font-semibold">Access denied</h1>
        <p className="mt-4 text-ink/65">{state.message}</p>
      </main>
    );
  }

  return (
    <AppShell title="Admin management" user={state.user} onLogout={() => void onLogout()}>
      {notice ? (
        <div className="notice-success" data-testid="admin-notice">
          {notice}
        </div>
      ) : null}
      {error ? (
        <div className="notice-error" data-testid="admin-error">
          {error}
        </div>
      ) : null}

      <section className="mt-6 grid gap-4 md:grid-cols-4">
        <div className="metric-card">
          <p className="metric-label">AI provider</p>
          <p className="metric-value">{state.aiStatus.provider_display_name}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Model</p>
          <p className="metric-value">{state.aiStatus.model ?? "Not set"}</p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Configuration</p>
          <p className={`metric-value ${state.aiStatus.configured ? "text-moss" : "text-coral"}`}>
            {state.aiStatus.configured ? "Ready" : "Missing key"}
          </p>
        </div>
        <div className="metric-card">
          <p className="metric-label">Last AI call</p>
          <p className="metric-value">{state.aiStatus.last_call_status ?? "No calls"}</p>
        </div>
      </section>

      <section className="grid gap-5 py-6 lg:grid-cols-[0.95fr_1.05fr]">
        <form onSubmit={onImport} className="section-card">
          <h2 className="text-xl font-semibold text-ink">CSV import</h2>
          <div className="mt-4 flex gap-2">
            {(["STUDENT", "TEACHER"] as const).map((role) => (
              <button
                key={role}
                type="button"
                onClick={() => setImportRole(role)}
                className={`rounded-md border px-4 py-2 text-sm font-semibold ${
                  importRole === role ? "border-moss bg-moss text-white" : "border-ink/15 bg-paper text-ink"
                }`}
              >
                {role}
              </button>
            ))}
          </div>
          <textarea
            value={csv}
            onChange={(event) => {
              setCsv(event.target.value);
              setCsvFile(null);
              setImportResult(null);
            }}
            rows={8}
            className="mt-4 w-full form-control font-mono"
            data-testid="admin-import-textarea"
          />
          <label className="mt-3 block">
            <span className="text-sm font-semibold text-ink">Upload CSV file</span>
            <input
              type="file"
              accept=".csv,text/csv"
              onChange={onCsvFile}
              className="mt-2 block w-full text-sm text-ink file:mr-4 file:rounded-md file:border-0 file:bg-moss file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white"
            />
          </label>
          <div className="mt-3 rounded-md bg-chalk px-3 py-3 text-sm text-ink/70" data-testid="admin-import-preview">
            {csvFile ? (
              <p className="font-semibold text-ink">
                Loaded {csvFile.name} · {Math.ceil(csvFile.size / 1024)} KB
              </p>
            ) : (
              <p className="font-semibold text-ink">Manual CSV input</p>
            )}
            <p className="mt-1">
              Parsed rows: {parsedCsv.rows.length}
              {parsedCsv.errors.length > 0 ? ` · Parse issues: ${parsedCsv.errors.length}` : ""}
            </p>
            {parsedCsv.errors.length > 0 ? (
              <ul className="mt-2 grid gap-1 text-coral">
                {parsedCsv.errors.slice(0, 3).map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            ) : null}
            {previewRows.length > 0 ? (
              <div className="mt-3 grid gap-1 text-xs">
                {previewRows.map((row) => (
                  <p key={`${row.email}-${row.display_name}`}>
                    {row.email} · {row.display_name} · {row.class_name ?? row.staff_code ?? "-"}
                  </p>
                ))}
              </div>
            ) : null}
          </div>
          <p className="mt-2 text-sm text-ink/60">
            Headers: email, display_name, student_number, level, class_name, staff_code.
          </p>
          <button type="submit" className="mt-4 btn btn-primary btn-lg" data-testid="admin-import-submit">
            Import users
          </button>
          {importResult ? (
            <div className="mt-5 grid gap-3 text-sm" data-testid="admin-import-result">
              {importResult.successful_rows.map((row) => (
                <div key={`${row.row}-${row.email}`} className="rounded-md bg-moss/10 px-3 py-2 text-moss">
                  Row {row.row}: imported {row.email}
                </div>
              ))}
              {importResult.rejected_rows.map((row) => (
                <div key={`${row.row}-${row.email}`} className="rounded-md bg-coral/10 px-3 py-2 text-coral">
                  Row {row.row}: {row.email} rejected - {row.reasons.join(" ")}
                </div>
              ))}
            </div>
          ) : null}
        </form>

        <form onSubmit={onCreateClass} className="section-card">
          <h2 className="text-xl font-semibold text-ink">Class management</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <input
              value={classForm.name}
              onChange={(event) => setClassForm({ ...classForm, name: event.target.value })}
              className="form-control"
              placeholder="Class name"
            />
            <select
              value={classForm.level}
              onChange={(event) => setClassForm({ ...classForm, level: event.target.value })}
              className="form-control"
            >
              <option>P4</option>
              <option>P5</option>
              <option>P6</option>
            </select>
            <input
              value={classForm.academic_year}
              onChange={(event) => setClassForm({ ...classForm, academic_year: event.target.value })}
              className="form-control"
              placeholder="Academic year"
            />
          </div>
          <button type="submit" className="mt-4 btn btn-primary btn-lg">
            Create class
          </button>
          <div className="mt-6 table-shell">
            <table className="w-full text-left text-sm">
              <thead className="table-head">
                <tr>
                  <th className="px-3 py-2">Class</th>
                  <th className="px-3 py-2">Level</th>
                  <th className="px-3 py-2">Teachers</th>
                  <th className="px-3 py-2">Students</th>
                </tr>
              </thead>
              <tbody>
                {state.classes.map((schoolClass) => (
                  <tr key={schoolClass.id} className="table-row">
                    <td className="px-3 py-2 font-semibold">{schoolClass.name}</td>
                    <td className="px-3 py-2">{schoolClass.level}</td>
                    <td className="px-3 py-2">{schoolClass.teacher_count ?? 0}</td>
                    <td className="px-3 py-2">{schoolClass.student_count ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </form>
      </section>

      <section className="section-card">
        <h2 className="text-xl font-semibold text-ink">Account management</h2>
        <div className="mt-4 table-shell">
          <table className="w-full text-left text-sm">
            <thead className="table-head">
              <tr>
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Email</th>
                <th className="px-3 py-2">Role</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Class</th>
                <th className="px-3 py-2">Actions</th>
              </tr>
            </thead>
            <tbody>
              {state.users.map((account) => (
                <tr key={account.id} className="table-row">
                  <td className="px-3 py-2 font-semibold">{account.display_name}</td>
                  <td className="px-3 py-2">{account.email}</td>
                  <td className="px-3 py-2">{account.role}</td>
                  <td className="px-3 py-2">{account.status}</td>
                  <td className="px-3 py-2">{account.class_name ?? account.staff_code ?? "-"}</td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-2">
                      {account.status !== "ACTIVE" ? (
                        <button
                          type="button"
                          className="btn btn-outline px-3 py-1 text-xs"
                          onClick={() => onUpdateStatus(account.id, "ACTIVE")}
                        >
                          Restore
                        </button>
                      ) : null}
                      {account.status !== "SUSPENDED" ? (
                        <button
                          type="button"
                          className="btn btn-outline px-3 py-1 text-xs"
                          onClick={() => onUpdateStatus(account.id, "SUSPENDED")}
                        >
                          Suspend
                        </button>
                      ) : null}
                      {account.status !== "ARCHIVED" ? (
                        <button
                          type="button"
                          className="btn btn-danger px-3 py-1 text-xs"
                          onClick={() => onUpdateStatus(account.id, "ARCHIVED")}
                        >
                          Archive
                        </button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </AppShell>
  );
}
