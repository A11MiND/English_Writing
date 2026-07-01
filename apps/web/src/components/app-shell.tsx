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

type NavItem = {
  href: string;
  label: string;
  description: string;
  icon: "home" | "edit" | "score" | "report" | "settings" | "users" | "import" | "class" | "profile";
};

const navByRole: Record<Role, NavItem[]> = {
  SYSTEM_ADMIN: [
    { href: "/admin", label: "Overview", description: "AI status and school controls", icon: "home" },
    { href: "/admin#import", label: "CSV import", description: "Students and teachers", icon: "import" },
    { href: "/admin#classes", label: "Classes", description: "P4 to P6 setup", icon: "class" },
    { href: "/admin#accounts", label: "Accounts", description: "Status and roles", icon: "users" },
  ],
  SCHOOL_ADMIN: [
    { href: "/admin", label: "Overview", description: "AI status and school controls", icon: "home" },
    { href: "/admin#import", label: "CSV import", description: "Students and teachers", icon: "import" },
    { href: "/admin#classes", label: "Classes", description: "P4 to P6 setup", icon: "class" },
    { href: "/admin#accounts", label: "Accounts", description: "Status and roles", icon: "users" },
  ],
  TEACHER: [
    { href: "/teacher", label: "Overview", description: "Class workload", icon: "home" },
    { href: "/teacher#rubrics", label: "Rubrics", description: "School marking criteria", icon: "score" },
    { href: "/teacher#tasks", label: "Tasks", description: "Create and assign writing", icon: "edit" },
    { href: "/teacher#reports", label: "Reports", description: "Class analytics and exports", icon: "report" },
    { href: "/teacher#marking", label: "Marking", description: "AI results and review", icon: "settings" },
  ],
  STUDENT: [
    { href: "/student", label: "Home", description: "Assigned writing tasks", icon: "home" },
    { href: "/student#tasks", label: "Tasks", description: "Practice and Exam Mode", icon: "edit" },
    { href: "/student#profile", label: "Profile", description: "Class and level", icon: "profile" },
  ],
};

const utilityByRole: Record<Role, NavItem[]> = {
  SYSTEM_ADMIN: [
    { href: "/admin#accounts", label: "Account access", description: "Manage status", icon: "users" },
    { href: "/admin#classes", label: "School setup", description: "Classes", icon: "class" },
  ],
  SCHOOL_ADMIN: [
    { href: "/admin#accounts", label: "Account access", description: "Manage status", icon: "users" },
    { href: "/admin#classes", label: "School setup", description: "Classes", icon: "class" },
  ],
  TEACHER: [
    { href: "/teacher#marking", label: "Review queue", description: "Mark writing", icon: "settings" },
    { href: "/teacher#reports", label: "Class evidence", description: "Reports", icon: "report" },
  ],
  STUDENT: [
    { href: "/student#tasks", label: "Writing tasks", description: "Start writing", icon: "edit" },
    { href: "/student#profile", label: "My class", description: "Profile", icon: "profile" },
  ],
};

function ShellIcon({ name }: { name: NavItem["icon"] }) {
  const common = {
    className: "h-4 w-4",
    viewBox: "0 0 20 20",
    fill: "currentColor",
    "aria-hidden": true,
  } as const;

  switch (name) {
    case "edit":
      return (
        <svg {...common}>
          <path d="M13.7 2.6a2.1 2.1 0 0 1 3 3L7.5 14.8l-3.9.8.8-3.9 9.3-9.1Z" />
          <path d="M3.5 17a.8.8 0 0 0 .8.8h11.4a.8.8 0 1 0 0-1.6H4.3a.8.8 0 0 0-.8.8Z" />
        </svg>
      );
    case "score":
      return (
        <svg {...common}>
          <path d="M5 3.5A2.5 2.5 0 0 0 2.5 6v8A2.5 2.5 0 0 0 5 16.5h10A2.5 2.5 0 0 0 17.5 14V6A2.5 2.5 0 0 0 15 3.5H5Zm1.5 4h7a.8.8 0 0 1 0 1.6h-7a.8.8 0 1 1 0-1.6Zm0 3.4h4.5a.8.8 0 1 1 0 1.6H6.5a.8.8 0 1 1 0-1.6Z" />
        </svg>
      );
    case "report":
      return (
        <svg {...common}>
          <path d="M4 3.5A1.5 1.5 0 0 1 5.5 2h7L16 5.5v11A1.5 1.5 0 0 1 14.5 18h-9A1.5 1.5 0 0 1 4 16.5v-13Zm7.5.2V6a1 1 0 0 0 1 1h2.3l-3.3-3.3ZM7 9.8a.8.8 0 0 0 0 1.6h6a.8.8 0 0 0 0-1.6H7Zm0 3a.8.8 0 0 0 0 1.6h4a.8.8 0 0 0 0-1.6H7Z" />
        </svg>
      );
    case "settings":
      return (
        <svg {...common}>
          <path d="M8.8 2.5h2.4l.5 2a6 6 0 0 1 1.5.6l1.8-1 1.7 1.7-1 1.8c.3.5.5 1 .6 1.5l2 .5V12l-2 .5a6 6 0 0 1-.6 1.5l1 1.8-1.7 1.7-1.8-1a6 6 0 0 1-1.5.6l-.5 2H8.8l-.5-2a6 6 0 0 1-1.5-.6l-1.8 1-1.7-1.7 1-1.8a6 6 0 0 1-.6-1.5l-2-.5V9.6l2-.5c.1-.5.3-1 .6-1.5l-1-1.8L5 4.1l1.8 1c.5-.3 1-.5 1.5-.6l.5-2ZM10 7a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z" />
        </svg>
      );
    case "users":
      return (
        <svg {...common}>
          <path d="M7.5 9.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm-5 6.1c0-2.5 2.2-4.4 5-4.4s5 1.9 5 4.4c0 .8-.6 1.4-1.4 1.4H3.9c-.8 0-1.4-.6-1.4-1.4Zm10.2-5.7a3 3 0 1 0 .1-5.8 5 5 0 0 1-.1 5.8Zm1.4 7.1h2c.8 0 1.4-.6 1.4-1.4 0-2.1-1.5-3.8-3.6-4.2.7 1 1.1 2.2 1.1 3.6 0 .8-.3 1.5-.9 2Z" />
        </svg>
      );
    case "import":
      return (
        <svg {...common}>
          <path d="M4 3.5A1.5 1.5 0 0 1 5.5 2h9A1.5 1.5 0 0 1 16 3.5v13a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 4 16.5v-13Zm3.2 7.2 2 2a.8.8 0 0 0 1.1 0l2-2a.8.8 0 0 0-1.1-1.1l-.6.6V5.8a.8.8 0 0 0-1.6 0v4.4l-.6-.6a.8.8 0 1 0-1.1 1.1Z" />
        </svg>
      );
    case "class":
      return (
        <svg {...common}>
          <path d="M3 4.8A1.8 1.8 0 0 1 4.8 3h10.4A1.8 1.8 0 0 1 17 4.8v7.4a1.8 1.8 0 0 1-1.8 1.8H11v1.5h2.2a.8.8 0 1 1 0 1.5H6.8a.8.8 0 1 1 0-1.5H9V14H4.8A1.8 1.8 0 0 1 3 12.2V4.8Zm3.2 2a.8.8 0 0 0 0 1.6h7.6a.8.8 0 0 0 0-1.6H6.2Zm0 3a.8.8 0 0 0 0 1.6h4.6a.8.8 0 0 0 0-1.6H6.2Z" />
        </svg>
      );
    case "profile":
      return (
        <svg {...common}>
          <path d="M10 10a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-6 6.1c0-2.7 2.6-4.8 6-4.8s6 2.1 6 4.8c0 1-.8 1.9-1.9 1.9H5.9A1.9 1.9 0 0 1 4 16.1Z" />
        </svg>
      );
    case "home":
    default:
      return (
        <svg {...common}>
          <path d="M3 9.2 10 3l7 6.2v7.1a1.7 1.7 0 0 1-1.7 1.7h-3.1v-5.2H7.8V18H4.7A1.7 1.7 0 0 1 3 16.3V9.2Z" />
        </svg>
      );
  }
}

export function AppShell({ title, user, children, onLogout, maxWidth = "wide" }: AppShellProps) {
  const pathname = usePathname();
  const navItems = navByRole[user.role] ?? [];
  const utilityItems = utilityByRole[user.role] ?? [];
  const contentWidth = maxWidth === "standard" ? "max-w-[1220px]" : "max-w-[1680px]";
  const initials = user.display_name
    .split(" ")
    .map((part) => part.slice(0, 1))
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <main className="portal-shell text-ink">
      <div className={`portal-frame ${contentWidth}`}>
        <aside className="portal-sidebar">
          <div className="sidebar-brand">
            <div className="brand-mark">W</div>
            <div>
              <p className="sidebar-school">W F Joseph Lee</p>
              <p className="sidebar-product">English AI Writing</p>
            </div>
            <svg className="sidebar-chevron" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M4.2 6.2a.8.8 0 0 1 1.1 0L8 8.9l2.7-2.7a.8.8 0 1 1 1.1 1.1l-3.2 3.2a.8.8 0 0 1-1.1 0L4.2 7.3a.8.8 0 0 1 0-1.1Z" />
            </svg>
          </div>
          <nav className="sidebar-nav" aria-label="Primary navigation">
            {navItems.map((item) => {
              const itemPath = item.href.split("#")[0];
              const active = pathname === item.href || (item.href.indexOf("#") === -1 && pathname === itemPath);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-nav-link ${active ? "sidebar-nav-link-active" : ""}`}
                >
                  <span className="sidebar-nav-icon"><ShellIcon name={item.icon} /></span>
                  <span className="min-w-0">
                    <span className="sidebar-nav-label">{item.label}</span>
                    <span className="sidebar-nav-description">{item.description}</span>
                  </span>
                </Link>
              );
            })}
          </nav>
          <div className="sidebar-help">
            {utilityItems.map((item) => (
              <Link key={item.href} href={item.href} className="sidebar-utility-link">
                <ShellIcon name={item.icon} />
                <span>{item.label}</span>
              </Link>
            ))}
          </div>
          <div className="sidebar-footer">
            <div className="user-avatar">{initials}</div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-ink">{user.display_name}</p>
              <p className="truncate text-xs text-ink/50">{user.email}</p>
            </div>
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
                <div className="user-avatar user-avatar-compact">{initials}</div>
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
