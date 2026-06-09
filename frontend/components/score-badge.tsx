"use client";

type Variant = "success" | "warning" | "danger" | "info" | "muted";

type Props = {
  label: string;
  value: number | string;
  variant?: Variant;
  showBar?: boolean;
  max?: number;
  size?: "sm" | "md";
};

const variantStyles: Record<Variant, { bg: string; text: string; bar: string }> = {
  success: { bg: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-500" },
  warning: { bg: "bg-amber-50", text: "text-amber-700", bar: "bg-amber-500" },
  danger:  { bg: "bg-red-50",   text: "text-red-700",   bar: "bg-red-500"   },
  info:    { bg: "bg-blue-50",  text: "text-blue-700",  bar: "bg-blue-500"  },
  muted:   { bg: "bg-gray-100", text: "text-gray-600",  bar: "bg-gray-400"  },
};

function autoVariant(value: number, label: string): Variant {
  const isRisk = label.toLowerCase().includes("risk");
  if (isRisk) {
    if (value >= 70) return "danger";
    if (value >= 45) return "warning";
    return "success";
  }
  if (value >= 70) return "success";
  if (value >= 45) return "warning";
  return "danger";
}

export function ScoreBadge({ label, value, variant, showBar = false, max = 100, size = "md" }: Props): JSX.Element {
  const numVal = typeof value === "number" ? value : parseFloat(value);
  const resolved = variant ?? (typeof value === "number" ? autoVariant(numVal, label) : "muted");
  const styles = variantStyles[resolved];
  const pct = Math.min(100, (numVal / max) * 100);

  return (
    <div className={`rounded-lg ${size === "sm" ? "px-2 py-1" : "px-3 py-2"} ${styles.bg}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className={`text-xs font-medium ${styles.text} opacity-80`}>{label}</span>
        <span className={`font-bold ${size === "sm" ? "text-sm" : "text-base"} ${styles.text}`}>
          {typeof value === "number" ? value.toFixed(0) : value}
        </span>
      </div>
      {showBar && typeof value === "number" && (
        <div className="mt-1.5 h-1 w-full rounded-full bg-black/10">
          <div
            className={`h-1 rounded-full ${styles.bar} transition-all`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}
