import type { ReactNode } from "react";

type MascotGuideProps = {
  title: string;
  body: string;
  label?: string;
  variant?: "login" | "home" | "feedback" | "compact";
  children?: ReactNode;
};

export function MascotGuide({
  title,
  body,
  label = "Pip, your writing coach",
  variant = "compact",
  children,
}: MascotGuideProps) {
  return (
    <aside className={`mascot-guide mascot-guide-${variant}`} aria-label={label}>
      <div className="mascot-portrait">
        <img src="/ai-coach-fox.png" alt="Pip the fox writing coach" />
      </div>
      <div className="mascot-copy">
        <p className="micro-label">{label}</p>
        <h2>{title}</h2>
        <p>{body}</p>
        {children ? <div className="mascot-actions">{children}</div> : null}
      </div>
    </aside>
  );
}
