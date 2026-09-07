type SkeletonScreenProps = {
  label: string;
  variant?: "workspace" | "page";
};

/** Placeholder shown while a screen's data loads, in place of a blank page with one line of text. */
export function SkeletonScreen({ label, variant = "page" }: SkeletonScreenProps) {
  return (
    <main className={`skeleton-screen skeleton-${variant}`} aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      <div className="skeleton-header">
        <div className="skeleton-line skeleton-eyebrow" />
        <div className="skeleton-line skeleton-title" />
        <div className="skeleton-line skeleton-lead" />
      </div>
      <div className="skeleton-cards">
        {[0, 1, 2].map((index) => (
          <div key={index} className="skeleton-card">
            <div className="skeleton-line skeleton-chip" />
            <div className="skeleton-line skeleton-heading" />
            <div className="skeleton-line" />
            <div className="skeleton-line skeleton-short" />
          </div>
        ))}
      </div>
    </main>
  );
}
