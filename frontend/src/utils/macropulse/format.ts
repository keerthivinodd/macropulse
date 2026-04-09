/**
 * MacroPulse shared display formatters.
 * Single source of truth — import these instead of defining locally.
 */

export function formatNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "--";
  return value.toFixed(digits);
}

/** Short date+time in en-IN locale — e.g. "02 Apr, 9:30 am" */
export function formatDateTime(value?: string | null): string {
  if (!value) return "--";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "--";
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

/** "+1.3%" or "-4.2%" */
export function formatSigned(value: number, suffix = "%"): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(1)}${suffix}`;
}
