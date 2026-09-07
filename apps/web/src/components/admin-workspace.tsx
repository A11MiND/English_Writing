"use client";

import type {
  AccountStatus,
  AdminUser,
  AiSettings,
  AiServiceStatus,
  ImportRole,
  ImportUsersPayload,
  SchoolClass,
} from "@english-ai-writing/shared";
import type { ChangeEvent, FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";

import { AppShell, type AppShellUser } from "@/components/app-shell";
import { currentUser, logout } from "@/lib/auth";
import { SkeletonScreen } from "@/components/skeleton";
import {
  createClass,
  getAiSettings,
  getAiServiceStatus,
  importUsers,
  listClasses,
  listUsers,
  parseUserCsv,
  testAiConnection,
  updateAiSettings,
  updateUserStatus,
  resetUserPassword,
} from "@/lib/school-data";

export type AdminScreen = "overview" | "classes" | "settings";

type AdminState =
  | { status: "loading" }
  | { status: "denied"; message: string }
  | {
      status: "ready";
      user: AppShellUser;
      classes: SchoolClass[];
      users: AdminUser[];
      aiStatus: AiServiceStatus;
      aiSettings: AiSettings;
    };

const sampleStudentCsv =
  "email,display_name,student_number,level,class_name\nnew.student@school.example,New Student,S0101,P5,P5A";

function statusBadge(status: string) {
  if (status === "ACTIVE") return "badge-success";
  if (status === "SUSPENDED") return "badge-warning";
  if (status === "ARCHIVED") return "badge-danger";
  return "badge-soft";
}

function Metric({ label, value, note }: { label: string; value: string | number; note: string }) {
  return (
    <div className="metric emphasis">
      <p className="micro-label">{label}</p>
      <p className="metric-value">{value}</p>
      <p className="metric-note">{note}</p>
    </div>
  );
}

export function AdminWorkspace({ screen }: { screen: AdminScreen }) {
  const [state, setState] = useState<AdminState>({ status: "loading" });
  const [classForm, setClassForm] = useState({ name: "P4B", level: "P4", academic_year: "2026-2027" });
  const [importRole, setImportRole] = useState<ImportRole>("STUDENT");
  const [csv, setCsv] = useState(sampleStudentCsv);
  const [csvFile, setCsvFile] = useState<{ name: string; size: number } | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [resetTarget, setResetTarget] = useState<{ id: string; email: string } | null>(null);
  const [resetPassword, setResetPassword] = useState("");
  const [resetBusyUserId, setResetBusyUserId] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportUsersPayload | null>(null);
  const [settings, setSettings] = useState({
    requireTeacherRelease: true,
    blockExamPaste: true,
    logExamFocus: true,
    exportScope: "Teacher-owned classes only",
    notifyMissing: true,
  });
  const [aiForm, setAiForm] = useState({
    provider: "deepseek",
    model: "",
    base_url: "",
    api_key: "",
    timeout_seconds: 30,
  });

  function showToast(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 2600);
  }

  async function refresh(user?: AppShellUser) {
    const [classes, users, aiStatus, aiSettings] = await Promise.all([
      listClasses(),
      listUsers(),
      getAiServiceStatus(),
      getAiSettings(),
    ]);
    setAiForm({
      provider: aiSettings.provider,
      model: aiSettings.model ?? "",
      base_url: aiSettings.base_url ?? "",
      api_key: "",
      timeout_seconds: Math.round(aiSettings.timeout_seconds),
    });
    setState((current) => {
      const shellUser = user ?? (current.status === "ready" ? current.user : null);
      if (!shellUser) return current;
      return { status: "ready", user: shellUser, classes, users, aiStatus, aiSettings };
    });
  }

  useEffect(() => {
    let active = true;
    async function load() {
      const user = await currentUser();
      if (!active) return;
      if (!user) {
        window.location.href = "/login";
        return;
      }
      if (!["SYSTEM_ADMIN", "SCHOOL_ADMIN"].includes(user.role)) {
        setState({ status: "denied", message: "Your role cannot access admin management." });
        return;
      }
      await refresh({ display_name: user.display_name, email: user.email, role: user.role });
    }
    void load().catch((err) => {
      setState({ status: "denied", message: err instanceof Error ? err.message : "Unable to load admin data." });
    });
    return () => {
      active = false;
    };
  }, []);

  async function onLogout() {
    await logout();
    window.location.href = "/login";
  }

  async function onCreateClass(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      await createClass(classForm);
      setNotice(`Class ${classForm.name} created.`);
      showToast("Class created.");
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
      showToast("Import completed with row-level results.");
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

  async function onConfirmReset() {
    if (!resetTarget) return;
    if (resetPassword.length < 8) {
      setError("A temporary password needs at least 8 characters.");
      return;
    }
    setResetBusyUserId(resetTarget.id);
    setError("");
    setNotice("");
    try {
      await resetUserPassword(resetTarget.id, resetPassword);
      setNotice(`Temporary password set for ${resetTarget.email}. Share it with them directly.`);
      setResetTarget(null);
      setResetPassword("");
    } catch (resetError) {
      setError(resetError instanceof Error ? resetError.message : "Unable to reset this password.");
    } finally {
      setResetBusyUserId(null);
    }
  }

  async function onUpdateStatus(userId: string, status: AccountStatus) {
    setNotice("");
    setError("");
    try {
      await updateUserStatus(userId, status);
      setNotice(`Account status updated to ${status}.`);
      showToast(status === "ACTIVE" ? "Account restored." : `Account ${status.toLowerCase()}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to update account status.");
    }
  }

  async function onSaveAiSettings(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setNotice("");
    setError("");
    try {
      await updateAiSettings({
        provider: aiForm.provider,
        model: aiForm.model || null,
        base_url: aiForm.base_url || null,
        api_key: aiForm.api_key || undefined,
        timeout_seconds: aiForm.timeout_seconds,
      });
      setNotice("AI provider settings saved.");
      showToast("AI settings saved.");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to save AI settings.");
    }
  }

  async function onTestAiConnection() {
    setNotice("");
    setError("");
    try {
      const result = await testAiConnection();
      setNotice(result.message);
      showToast(`AI connection tested with ${result.provider}.`);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "AI connection test failed.");
    }
  }

  if (state.status === "loading") {
    return <SkeletonScreen label="Loading admin workspace..." variant="workspace" />;
  }

  if (state.status === "denied") {
    return (
      <main className="centered-state">
        <div>
          <h1 className="screen-title">Access denied</h1>
          <p className="lead">{state.message}</p>
        </div>
      </main>
    );
  }

  const parsedCsv = parseUserCsv(csv);
  const teacherCount = state.users.filter((user) => user.role === "TEACHER").length;
  const studentCount = state.users.filter((user) => user.role === "STUDENT").length;
  const blockedCount = state.users.filter((user) => user.status !== "ACTIVE").length;

  return (
    <AppShell
      title={screen === "overview" ? "School overview" : screen === "classes" ? "People & classes" : "AI & safety"}
      subtitle={
        screen === "overview"
          ? "See whether people, classes, and the writing service are ready for teaching."
          : screen === "classes"
          ? "Manage class rosters, account status, and teacher ownership."
          : "Control AI access, teacher release rules, exam safeguards, and exports."
      }
      user={state.user}
      onLogout={() => void onLogout()}
    >
      {notice ? <div className="notice-success">{notice}</div> : null}
      {error ? <div className="notice-error">{error}</div> : null}

      {screen === "overview" ? (
        <>
          <section className="admin-overview-hero">
            <div>
              <p className="micro-label">School administration</p>
              <h2>The school is ready for today’s writing lessons.</h2>
              <p>Keep setup work separate from teaching. Use this page to spot anything that could block a teacher or pupil before class starts.</p>
              <div className="teacher-home-actions">
                <Link className="btn btn-primary" href="/admin/classes">Manage people & classes</Link>
                <Link className="btn btn-secondary" href="/admin/settings">Review AI & safety</Link>
              </div>
            </div>
            <aside className="admin-readiness">
              <span className={`state-dot ${state.aiStatus.configured ? "ready" : "error"}`} aria-hidden="true" />
              <div>
                <p className="micro-label">Service readiness</p>
                <strong>{state.aiStatus.configured ? "AI writing support is configured" : "AI setup needs attention"}</strong>
                <p>{state.aiStatus.provider_display_name} · {state.aiStatus.model ?? "Choose a model"}</p>
              </div>
            </aside>
          </section>

          <section className="teacher-home-metrics" aria-label="School account overview">
            <Metric label="Classes" value={state.classes.length} note="Active class records" />
            <Metric label="Pupils" value={studentCount} note="Student accounts" />
            <Metric label="Teachers" value={teacherCount} note="Teacher accounts" />
            <Metric label="Needs attention" value={blockedCount} note="Suspended or archived" />
          </section>

          <section className="admin-action-list">
            <Link href="/admin/classes">
              <span>01</span>
              <div><strong>People & classes</strong><p>Create classes, import school accounts, and manage access.</p></div>
              <b>Open</b>
            </Link>
            <Link href="/admin/settings">
              <span>02</span>
              <div><strong>AI & safety</strong><p>Configure the provider and keep every pupil-facing decision teacher-led.</p></div>
              <b>Open</b>
            </Link>
          </section>
        </>
      ) : null}

      {screen === "classes" ? (
        <>
          <section className="grid-4">
            <Metric label="Classes" value={state.classes.length} note="Active class records" />
            <Metric label="Students" value={studentCount} note="Student accounts" />
            <Metric label="Teachers" value={teacherCount} note="Teacher accounts" />
            <Metric label="Blocked" value={blockedCount} note="Suspended or archived accounts" />
          </section>

          <section className="grid-2">
            <form className="panel form-grid" onSubmit={onCreateClass}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Create class</h2>
                  <p className="panel-subtitle">Maintain class ownership without developer help.</p>
                </div>
              </div>
              <div className="grid-3">
                <div className="field">
                  <label htmlFor="class-name">Class name</label>
                  <input id="class-name" className="input" value={classForm.name} onChange={(event) => setClassForm({ ...classForm, name: event.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor="class-level">Level</label>
                  <select id="class-level" className="select" value={classForm.level} onChange={(event) => setClassForm({ ...classForm, level: event.target.value })}>
                    <option>P4</option>
                    <option>P5</option>
                    <option>P6</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="academic-year">Academic year</label>
                  <input id="academic-year" className="input" value={classForm.academic_year} onChange={(event) => setClassForm({ ...classForm, academic_year: event.target.value })} />
                </div>
              </div>
              <button type="submit" className="btn btn-primary">Create class</button>
            </form>

            <form className="panel form-grid" onSubmit={onImport}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">CSV import</h2>
                  <p className="panel-subtitle">Import students and teachers with row-level validation.</p>
                </div>
                <span className="badge-soft">{importRole}</span>
              </div>
              <div className="segmented">
                {(["STUDENT", "TEACHER"] as const).map((role) => (
                  <button key={role} type="button" className={`segment ${importRole === role ? "active" : ""}`} onClick={() => setImportRole(role)}>
                    {role}
                  </button>
                ))}
              </div>
              <textarea className="textarea" value={csv} onChange={(event) => {
                setCsv(event.target.value);
                setCsvFile(null);
                setImportResult(null);
              }} />
              <div className="field">
                <label htmlFor="csv-upload">Upload CSV file</label>
                <input id="csv-upload" type="file" accept=".csv,text/csv" onChange={onCsvFile} />
              </div>
              <div className="rubric-item">
                <strong>{csvFile ? `${csvFile.name} - ${Math.ceil(csvFile.size / 1024)} KB` : "Manual CSV input"}</strong>
                <p className="panel-subtitle">Parsed rows: {parsedCsv.rows.length}{parsedCsv.errors.length > 0 ? ` - Parse issues: ${parsedCsv.errors.length}` : ""}</p>
              </div>
              <button type="submit" className="btn btn-secondary">Import users</button>
              {importResult ? (
                <div className="grid-2">
                  <div className="notice-success">{importResult.successful_count} successful rows</div>
                  <div className="notice-error">{importResult.rejected_count} rejected rows</div>
                </div>
              ) : null}
            </form>
          </section>

          <section className="panel">
            <div className="panel-header">
              <div>
                <h2 className="panel-title">Class roster</h2>
                <p className="panel-subtitle">Classes, students, teachers, and account status.</p>
              </div>
              <span className="badge-soft">{state.users.length} accounts</span>
            </div>
            <div className="table-shell">
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Class</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {state.users.map((account) => (
                    <tr key={account.id}>
                      <td><strong>{account.display_name}</strong><br />{account.email}</td>
                      <td>{account.role}</td>
                      <td><span className={statusBadge(account.status)}>{account.status}</span></td>
                      <td>{account.class_name ?? account.staff_code ?? "-"}</td>
                      <td>
                        <div className="row-actions" style={{ marginTop: 0 }}>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={resetBusyUserId === account.id}
                            onClick={() => setResetTarget({ id: account.id, email: account.email })}
                          >
                            {resetBusyUserId === account.id ? "Resetting…" : "Reset password"}
                          </button>
                          {account.status !== "ACTIVE" ? (
                            <button type="button" className="btn btn-secondary" onClick={() => void onUpdateStatus(account.id, "ACTIVE")}>Restore</button>
                          ) : null}
                          {account.status !== "SUSPENDED" ? (
                            <button type="button" className="btn btn-secondary" onClick={() => void onUpdateStatus(account.id, "SUSPENDED")}>Suspend</button>
                          ) : null}
                          {account.status !== "ARCHIVED" ? (
                            <button type="button" className="btn btn-danger" onClick={() => void onUpdateStatus(account.id, "ARCHIVED")}>Archive</button>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  ))}
                  {state.users.length === 0 ? (
                    <tr>
                      <td colSpan={5}>No accounts found.</td>
                    </tr>
                  ) : null}
                </tbody>
              </table>
            </div>
          </section>

        </>
      ) : null}

      {screen === "settings" ? (
        <>
          <section className="grid-4">
            <Metric label="AI provider" value={state.aiStatus.provider_display_name} note={state.aiStatus.model ?? "No model configured"} />
            <Metric label="Configuration" value={state.aiStatus.configured ? "Ready" : "Missing"} note={state.aiSettings.masked_api_key ?? "No API key"} />
            <Metric label="Last AI call" value={state.aiStatus.last_call_status ?? "No calls"} note={state.aiStatus.last_called_at ? new Date(state.aiStatus.last_called_at).toLocaleString() : "No timestamp"} />
            <Metric label="Policy state" value={settings.requireTeacherRelease ? "Teacher-led" : "Review"} note="Feedback release rule" />
          </section>

          <section className="grid-2">
            <form className="panel form-grid" onSubmit={onSaveAiSettings}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Large model API</h2>
                  <p className="panel-subtitle">Configure the real provider used for AI marking and prompt generation.</p>
                </div>
                <span className={state.aiSettings.configured ? "badge-success" : "badge-warning"}>
                  {state.aiSettings.configured ? "Configured" : "Missing"}
                </span>
              </div>
              <div className="grid-2">
                <div className="field">
                  <label htmlFor="ai-provider">Provider</label>
                  <select id="ai-provider" className="select" value={aiForm.provider} onChange={(event) => setAiForm({ ...aiForm, provider: event.target.value })}>
                    <option value="deepseek">DeepSeek</option>
                    <option value="qwen">Qwen</option>
                    <option value="doubao">Doubao</option>
                    <option value="minimax">MiniMax</option>
                    <option value="openai_compatible">OpenAI-compatible</option>
                  </select>
                </div>
                <div className="field">
                  <label htmlFor="ai-model">Model</label>
                  <input id="ai-model" className="input" value={aiForm.model} placeholder="Use provider default" onChange={(event) => setAiForm({ ...aiForm, model: event.target.value })} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="ai-base-url">Base URL</label>
                <input id="ai-base-url" className="input" value={aiForm.base_url} placeholder="Use provider default" onChange={(event) => setAiForm({ ...aiForm, base_url: event.target.value })} />
              </div>
              <div className="grid-2">
                <div className="field">
                  <label htmlFor="ai-key">API key</label>
                  <input id="ai-key" className="input" type="password" value={aiForm.api_key} placeholder={state.aiSettings.masked_api_key ?? "Enter API key"} onChange={(event) => setAiForm({ ...aiForm, api_key: event.target.value })} />
                </div>
                <div className="field">
                  <label htmlFor="ai-timeout">Timeout seconds</label>
                  <input id="ai-timeout" className="input" type="number" min={1} max={120} value={aiForm.timeout_seconds} onChange={(event) => setAiForm({ ...aiForm, timeout_seconds: Number(event.target.value) })} />
                </div>
              </div>
              <div className="row-actions">
                <button type="submit" className="btn btn-primary">Save AI settings</button>
                <button type="button" className="btn btn-secondary" onClick={() => void onTestAiConnection()}>Test connection</button>
              </div>
            </form>

            <form className="panel form-grid" onSubmit={(event) => event.preventDefault()}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">AI review policy</h2>
                  <p className="panel-subtitle">Keep the system teacher-led and avoid exposing raw AI judgements.</p>
                </div>
              </div>
              <label className="rubric-item">
                <input
                  type="checkbox"
                  checked={settings.requireTeacherRelease}
                  onChange={(event) => setSettings({ ...settings, requireTeacherRelease: event.target.checked })}
                />{" "}
                Teacher must release feedback before students can view it
              </label>
              <div className="rubric-item">
                <span className="badge-success">Locked policy</span>
                <strong>AI diagnostics stay teacher-only</strong>
                <p className="panel-subtitle">
                  Students only see teacher-released scores, comments, and practice tasks.
                </p>
              </div>
            </form>

            <form className="panel form-grid" onSubmit={(event) => event.preventDefault()}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Exam safeguards</h2>
                  <p className="panel-subtitle">Exam mode should feel separate from practice mode and record reviewable events.</p>
                </div>
              </div>
              <label className="rubric-item">
                <input
                  type="checkbox"
                  checked={settings.blockExamPaste}
                  onChange={(event) => setSettings({ ...settings, blockExamPaste: event.target.checked })}
                />{" "}
                Block paste attempts in Exam Mode
              </label>
              <label className="rubric-item">
                <input
                  type="checkbox"
                  checked={settings.logExamFocus}
                  onChange={(event) => setSettings({ ...settings, logExamFocus: event.target.checked })}
                />{" "}
                Record focus changes for teacher review
              </label>
            </form>

            <form className="panel form-grid" onSubmit={(event) => event.preventDefault()}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Reports and exports</h2>
                  <p className="panel-subtitle">Exports should be audit-friendly and role-aware.</p>
                </div>
              </div>
              <div className="field">
                <label htmlFor="export-scope">Export scope</label>
                <select id="export-scope" className="select" value={settings.exportScope} onChange={(event) => setSettings({ ...settings, exportScope: event.target.value })}>
                  <option>Teacher-owned classes only</option>
                  <option>School admin full school</option>
                  <option>Blocked until review</option>
                </select>
              </div>
              <div className="rubric-item">
                <strong>Audit history</strong>
                <p className="panel-subtitle">Report export API records actor, role, format, class, task, and time.</p>
              </div>
            </form>

            <form className="panel form-grid" onSubmit={(event) => event.preventDefault()}>
              <div className="panel-header">
                <div>
                  <h2 className="panel-title">Notifications</h2>
                  <p className="panel-subtitle">Communication should be explicit and recoverable.</p>
                </div>
              </div>
              <label className="rubric-item">
                <input
                  type="checkbox"
                  checked={settings.notifyMissing}
                  onChange={(event) => setSettings({ ...settings, notifyMissing: event.target.checked })}
                />{" "}
                Allow teachers to remind missing submissions
              </label>
              <button type="button" className="btn btn-primary" onClick={() => showToast("Settings saved for this workspace view.")}>
                Save settings
              </button>
            </form>
          </section>
        </>
      ) : null}

      <div className={`modal-backdrop ${resetTarget ? "open" : ""}`} role="dialog" aria-modal="true" aria-labelledby="reset-password-title">
        <div className="modal">
          <p className="eyebrow">Account recovery</p>
          <h2 className="panel-title" id="reset-password-title" style={{ fontSize: "var(--text-xl)", marginTop: 8 }}>
            Set a temporary password
          </h2>
          <p className="panel-subtitle" style={{ marginTop: 12 }}>
            {resetTarget?.email} will sign in with this password. Share it with them directly and ask them to
            change it from their account page.
          </p>
          <div className="field" style={{ marginTop: 18 }}>
            <label htmlFor="reset-password">Temporary password</label>
            <input
              id="reset-password"
              className="input"
              type="text"
              autoComplete="off"
              minLength={8}
              value={resetPassword}
              onChange={(event) => setResetPassword(event.target.value)}
            />
            <p className="panel-subtitle">At least 8 characters.</p>
          </div>
          <div className="row-actions">
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => {
                setResetTarget(null);
                setResetPassword("");
              }}
            >
              Cancel
            </button>
            <button
              className="btn btn-primary"
              type="button"
              disabled={resetPassword.length < 8 || resetBusyUserId !== null}
              onClick={() => void onConfirmReset()}
            >
              {resetBusyUserId ? "Resetting…" : "Set password"}
            </button>
          </div>
        </div>
      </div>
      <div className={`toast ${toast ? "show" : ""}`} role="status" aria-live="polite">{toast}</div>
    </AppShell>
  );
}
