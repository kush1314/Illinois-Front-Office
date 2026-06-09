import { ReactNode } from "react";

export function SectionCard({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }): JSX.Element {
  return (
    <section className="rounded-xl2 border border-slate-200 bg-card p-5 shadow-panel">
      <div className="mb-3">
        <h2 className="text-xl font-semibold text-navy">{title}</h2>
        {subtitle ? <p className="mt-1 text-sm text-muted">{subtitle}</p> : null}
      </div>
      {children}
    </section>
  );
}
