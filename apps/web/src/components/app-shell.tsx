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

const navByRole: Record<Role, { href: string; label: string }[]> = {
  SYSTEM_ADMIN: [{ href: "/admin", label: "Admin" }],
  SCHOOL_ADMIN: [{ href: "/admin", label: "Admin" }],
  TEACHER: [{ href: "/teacher", label: "Teacher" }],
  STUDENT: [{ href: "/student", label: "Student" }],
};

export function AppShell({ title, user, children, onLogout, maxWidth = "wide" }: AppShellProps) {
  const pathname = usePathname();
  const navItems = navByRole[user.role] ?? [];
  const contentWidth = maxWidth === "standard" ? "max-w-6xl" : "max-w-7xl";

  return (
    <main className="min-h-screen px-4 py-4 text-ink md:px-6">
      <div className={`mx-auto grid w-full ${contentWidth} gap-5 lg:grid-cols-[232px_1fr]`}>
        <aside className="surface-card h-fit p-4 lg:sticky lg:top-4">
          <div className="border-b border-ink/10 pb-4">
            <p className="text-xs font-semibold uppercase tracking-[0.16em] text-moss">W F Joseph Lee</p>
            <p className="mt-2 text-lg font-semibold leading-tight">English AI Writing</p>
          </div>
          <nav className="mt-4 grid gap-2">
            {navItems.map((item) => {
              const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`rounded-md px-3 py-2 text-sm font-semibold transition ${
                    active ? "bg-moss text-white" : "text-ink/70 hover:bg-chalk hover:text-ink"
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </aside>

        <section className="min-w-0">
          <header className="surface-card flex flex-col gap-4 p-5 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="eyebrow">W F Joseph Lee Primary School</p>
              <h1 className="page-title">{title}</h1>
            </div>
            <div className="flex items-center gap-3">
              <div className="rounded-md bg-chalk px-3 py-2 text-right">
                <p className="text-sm font-semibold text-ink">{user.display_name}</p>
                <p className="text-xs font-semibold text-moss">{user.role}</p>
              </div>
              <button type="button" onClick={onLogout} className="btn btn-secondary">
                Logout
              </button>
            </div>
          </header>
          <div className="py-5">{children}</div>
        </section>
      </div>
    </main>
  );
}
