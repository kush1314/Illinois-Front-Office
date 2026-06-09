"use client";

type Props = {
  source: "synthetic" | "live" | string;
  label?: string;
  date?: string;
  className?: string;
};

export function DataSourceBadge({ source, label, date, className = "" }: Props): JSX.Element {
  const isSynthetic = source === "synthetic";
  const displayLabel = label ?? (isSynthetic ? "Synthetic demo data" : source);
  const dotColor = isSynthetic ? "bg-amber-400" : "bg-emerald-400";

  return (
    <div
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-xs ${
        isSynthetic
          ? "border-amber-200 bg-amber-50 text-amber-700"
          : "border-emerald-200 bg-emerald-50 text-emerald-700"
      } ${className}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
      <span className="font-medium">Source: {displayLabel}</span>
      {date && <span className="opacity-70">· {date}</span>}
    </div>
  );
}
