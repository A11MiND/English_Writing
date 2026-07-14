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

type NavItem = {
  href: string;
  label: string;
};

type AppShellProps = {
  title: string;
  subtitle?: string;
  user: AppShellUser;
  children: ReactNode;
  onLogout: () => void;
  roleNav?: NavItem[];
  variant?: "default" | "review";
};

const teacherNav: NavItem[] = [
  { href: "/teacher", label: "Today" },
  { href: "/teacher/assignments", label: "Prepare & assign" },
  { href: "/teacher/marking", label: "Review writing" },
  { href: "/teacher/reports", label: "Class insights" },
  { href: "/teacher/pupils", label: "Pupils" },
];

const adminNav: NavItem[] = [
  { href: "/admin", label: "Overview" },
  { href: "/admin/classes", label: "People & classes" },
  { href: "/admin/settings", label: "AI & safety" },
];

const fallbackNav: NavItem[] = [
  { href: "/student/writing", label: "My writing" },
  { href: "/student/writing", label: "Feedback" },
];

function navForRole(role: Role) {
  if (role === "TEACHER") return teacherNav;
  if (role === "SYSTEM_ADMIN" || role === "SCHOOL_ADMIN") return adminNav;
  return fallbackNav;
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .map((part) => part.slice(0, 1))
    .join("")
    .slice(0, 2)
    .toUpperCase() || "U";
}

export function AppShell({ title, subtitle, user, children, onLogout, roleNav, variant = "default" }: AppShellProps) {
  const pathname = usePathname();
  const navItems = roleNav ?? navForRole(user.role);
  const userInitials = initials(user.display_name);
  const workspaceLabel = user.role === "TEACHER" ? "Teacher workspace" : user.role === "STUDENT" ? "Pupil workspace" : "School administration";

  return (
    <div className={`app-shell ${variant === "review" ? "review-app-shell" : ""}`}>
      <aside className="sidebar">
        <Link className="brand" href={navItems[0]?.href ?? "/"}>
          <img className="brand-mark brand-mark-fox" src="/brand-fox.png" alt="" />
          <span className="brand-text">
            <span className="brand-title">English AI Writing</span>
            <span className="brand-subtitle">{workspaceLabel}</span>
          </span>
        </Link>

        <nav className="side-nav" aria-label={`${user.role.toLowerCase().replace("_", " ")} navigation`}>
          {navItems.map((item) => {
            const isWorkspaceRoot = item.href === "/teacher" || item.href === "/admin";
            const active = pathname === item.href || (!isWorkspaceRoot && pathname.startsWith(`${item.href}/`));
            return (
              <Link key={item.href} href={item.href} className={active ? "active" : ""}>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      <main className="workspace">
        <div className="workspace-inner">
          <header className="topbar">
            <div>
              <p className="eyebrow">English AI Writing Studio</p>
              <h1 className="screen-title">{title}</h1>
              {subtitle ? <p className="panel-subtitle">{subtitle}</p> : null}
            </div>
            <div className="row-actions" style={{ marginTop: 0 }}>
              <div className="user-chip">
                <span className="avatar">{userInitials}</span>
                <span>
                  <strong style={{ display: "block", color: "var(--fg)" }}>{user.display_name}</strong>
                  <span className="micro-label">{user.role.replace("_", " ")}</span>
                </span>
              </div>
              <button type="button" onClick={onLogout} className="btn btn-secondary">
                Logout
              </button>
            </div>
          </header>
          {children}
        </div>
      </main>
    </div>
  );
}

export function ProductTopNav({
  active,
  children,
  links,
  onLogout,
}: {
  active: string;
  children: ReactNode;
  links: Array<{ href: string; label: string }>;
  onLogout?: () => void;
}) {
  return (
    <div className="page">
      <header className="top-nav">
        <div className="container nav-inner">
          <Link className="brand" href="/login">
            <img className="brand-mark brand-mark-fox" src="/brand-fox.png" alt="" />
            <span className="brand-text">
              <span className="brand-title">English AI Writing</span>
              <span className="brand-subtitle">A writing studio for young learners</span>
            </span>
          </Link>
          <nav className="nav-links" aria-label="Page navigation">
            {links.map((link) => (
              <Link key={link.href} href={link.href} className={active === link.label ? "active" : ""}>
                {link.label}
              </Link>
            ))}
            {onLogout ? (
              <button type="button" onClick={onLogout}>
                Logout
              </button>
            ) : null}
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}

export const teacherNavigation = teacherNav;
export const adminNavigation = adminNav;
