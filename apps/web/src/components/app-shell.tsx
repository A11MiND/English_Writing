"use client";

import type { Role } from "@english-ai-writing/shared";
import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

export type AppShellUser = {
  display_name: string;
  email: string;
  role: Role;
};

type AppShellProps = {
  title: string;
  user: AppShellUser;
  children: ReactNode;
  onLogout: () => void;
  maxWidth?: "standard" | "wide";
};

const navByRole: Record<Role, { href: string; label: string; description: string }[]> = {
  SYSTEM_ADMIN: [
    { href: "/admin", label: "Overview", description: "AI status and school controls" },
    { href: "/admin#import", label: "CSV import", description: "Students and teachers" },
    { href: "/admin#classes", label: "Classes", description: "P4 to P6 setup" },
    { href: "/admin#accounts", label: "Accounts", description: "Status and roles" },
  ],
  SCHOOL_ADMIN: [
    { href: "/admin", label: "Overview", description: "AI status and school controls" },
    { href: "/admin#import", label: "CSV import", description: "Students and teachers" },
    { href: "/admin#classes", label: "Classes", description: "P4 to P6 setup" },
    { href: "/admin#accounts", label: "Accounts", description: "Status and roles" },
  ],
  TEACHER: [
    { href: "/teacher", label: "Overview", description: "Class workload" },
    { href: "/teacher#rubrics", label: "Rubrics", description: "School marking criteria" },
    { href: "/teacher#tasks", label: "Tasks", description: "Create and assign writing" },
    { href: "/teacher#reports", label: "Reports", description: "Class analytics and exports" },
    { href: "/teacher#marking", label: "Marking", description: "AI results and review" },
  ],
  STUDENT: [
    { href: "/student", label: "Home", description: "Assigned writing tasks" },
    { href: "/student#tasks", label: "Tasks", description: "Practice and Exam Mode" },
    { href: "/student#profile", label: "Profile", description: "Class and level" },
  ],
};

export function AppShell({ title, user, children, onLogout, maxWidth = "wide" }: AppShellProps) {
  const pathname = usePathname();
  const navItems = navByRole[user.role] ?? [];
  const contentWidth = maxWidth === "standard" ? "max-w-6xl" : "max-w-[1500px]";

  return (
    <main className="portal-shell text-ink">
      <div className={`portal-frame ${contentWidth}`}>
        <aside className="portal-sidebar">
          <div className="sidebar-brand">
            <div className="brand-mark">WFJ</div>
            <div>
              <p className="sidebar-school">W F Joseph Lee</p>
              <p className="sidebar-product">English AI Writing</p>
            </div>
          </div>
          <nav className="sidebar-nav" aria-label="Primary navigation">
            {navItems.map((item) => {
              const active = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-nav-link ${active ? "sidebar-nav-link-active" : ""}`}
                >
                  <span className="sidebar-nav-label">{item.label}</span>
                  <span className="sidebar-nav-description">{item.description}</span>
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-footer">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ink/45">Controlled pilot</p>
            <p className="mt-1 text-sm text-ink/65">One-school UAT workspace</p>
          </div>
        </aside>

        <section className="portal-content">
          <header className="portal-topbar">
            <div>
              <p className="page-kicker">W F Joseph Lee Primary School</p>
              <h1 className="page-title">{title}</h1>
            </div>
            <div className="topbar-actions">
              <div className="user-chip">
                <div className="user-avatar">{user.display_name.slice(0, 1).toUpperCase()}</div>
                <div className="min-w-0 text-right">
                  <p className="truncate text-sm font-semibold text-ink">{user.display_name}</p>
                  <p className="role-badge">{user.role.replace("_", " ")}</p>
                </div>
              </div>
              <button type="button" onClick={onLogout} className="btn btn-secondary">
                Logout
              </button>
            </div>
          </header>
          <div className="mobile-section-nav" aria-label="Section shortcuts">
            {navItems.slice(0, 5).map((item) => (
              <Link key={item.href} href={item.href} className="mobile-nav-pill">
                {item.label}
              </Link>
            ))}
          </div>
          <div className="content-stack">{children}</div>
        </section>
      </div>
    </main>
  );
}
