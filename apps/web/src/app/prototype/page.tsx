import Link from "next/link";

import { ProductTopNav } from "@/components/app-shell";

const pages = [
  {
    label: "Login",
    route: "/login",
    role: "Access",
    description: "Role-aware school account entry for teachers, students, and administrators.",
  },
  {
    label: "Marking Workbench",
    route: "/teacher/marking",
    role: "Teacher core",
    description: "AI suggestions, scoring, teacher review, and explicit feedback release.",
  },
  {
    label: "Assignments",
    route: "/teacher/assignments",
    role: "Teacher",
    description: "Create, assign, publish, remind, close, and archive writing tasks.",
  },
  {
    label: "Question Center",
    route: "/teacher/questions",
    role: "Teacher",
    description: "Generate writing prompts bound to level, mode, teaching focus, word range, and rubric.",
  },
  {
    label: "Reports",
    route: "/teacher/reports",
    role: "Teacher",
    description: "Turn class scores into teaching actions and exportable evidence.",
  },
  {
    label: "My Writing",
    route: "/student/writing",
    role: "Student",
    description: "Assigned writing, due dates, modes, submission state, and feedback status.",
  },
  {
    label: "Exam Writing",
    route: "/student/writing",
    role: "Student",
    description: "Timed writing is opened from a real exam task so safeguards can be enforced.",
  },
  {
    label: "Feedback",
    route: "/student/writing",
    role: "Student",
    description: "Released teacher comments, final scores, and practice tasks.",
  },
  {
    label: "Classes & Students",
    route: "/admin/classes",
    role: "Admin",
    description: "Roster, teacher ownership, account state, and class setup.",
  },
  {
    label: "Settings",
    route: "/admin/settings",
    role: "Admin",
    description: "AI visibility, release rules, exam safeguards, exports, and notifications.",
  },
];

export default function PrototypePage() {
  return (
    <ProductTopNav
      active="Prototype"
      links={[
        { href: "/login", label: "Login" },
        { href: "/prototype", label: "Prototype" },
      ]}
    >
      <main className="container">
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Internal preview</p>
            <h1>Turn AI marking into a daily writing workspace for schools.</h1>
            <p className="lead">
              This route maps the supplied HTML prototype to the implemented application routes.
              Final demo workflows cover Student, Teacher, and Admin roles backed by real API state.
            </p>
            <div className="hero-actions">
              <Link className="btn btn-primary" href="/teacher/marking">
                Open teacher workspace
              </Link>
              <Link className="btn btn-secondary" href="/student/writing">
                View student tasks
              </Link>
            </div>
          </div>
          <aside className="product-window" aria-label="Teacher review preview">
            <div className="window-bar">
              <div className="window-dots" aria-hidden="true">
                <span className="dot" />
                <span className="dot" />
                <span className="dot" />
              </div>
              <span className="micro-label">Teacher review</span>
            </div>
            <div className="window-body">
              <div className="mini-editor">
                <div className="mini-doc">
                  <div className="mini-line" />
                  <div className="mini-line" />
                  <p style={{ margin: "0 0 16px", color: "var(--fg-2)", lineHeight: 1.7 }}>
                    Yesterday I <span className="inline-mark">help</span> my classmate carry the books.
                    She was happy because the books were heavy.
                  </p>
                  <div className="mini-line short" />
                </div>
                <div className="mini-suggestion">
                  <p className="micro-label">Grammar suggestion</p>
                  <strong>help -&gt; helped</strong>
                  <p className="panel-subtitle">
                    Added to the teacher review draft. Students only see released teacher feedback.
                  </p>
                </div>
              </div>
            </div>
          </aside>
        </section>

        <section className="panel" style={{ marginBottom: 48 }}>
          <div className="panel-header">
            <div>
              <h2 className="panel-title">Delivery pages</h2>
              <p className="panel-subtitle">
                Each prototype file has a mapped app route. Exam and feedback deep links open from real task data.
              </p>
            </div>
            <span className="badge-soft">Responsive web</span>
          </div>
          <div className="grid-3">
            {pages.map((page) => (
              <Link key={page.label} className="task-card" href={page.route}>
                <span className="badge-soft">{page.role}</span>
                <h3 className="panel-title">{page.label}</h3>
                <p className="panel-subtitle">{page.description}</p>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </ProductTopNav>
  );
}
