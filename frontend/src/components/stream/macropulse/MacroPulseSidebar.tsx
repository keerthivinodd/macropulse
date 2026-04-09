"use client";

import type { ComponentType } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Activity,
  Bot,
  ChevronLeft,
  GitMerge,
  HeartPulse,
  LayoutGrid,
  Settings,
} from "lucide-react";

const TOP_NAV = [
  { label: "Overview", href: "/stream/macropulse", icon: LayoutGrid, exact: true },
];

const FEATURE_NAV = [
  { label: "Real-Time Monitoring", href: "/stream/macropulse/realtime", icon: Activity },
  { label: "Simulation Impact", href: "/stream/macropulse/simulation", icon: GitMerge },
  { label: "MacroPulse Agent", href: "/stream/macropulse/agent", icon: Bot },
];

const SUPPORT_NAV = [
  { label: "System Configuration", href: "/stream/macropulse/config", icon: Settings },
];

export default function MacroPulseSidebar() {
  const pathname = usePathname();
  const router = useRouter();

  const isActive = (href: string, exact?: boolean) =>
    exact ? pathname === href : pathname === href || pathname?.startsWith(href + "/");

  const renderLink = ({
    label,
    href,
    icon: Icon,
    exact,
    compact = false,
  }: {
    label: string;
    href: string;
    icon: ComponentType<{ className?: string }>;
    exact?: boolean;
    compact?: boolean;
  }) => {
    const active = isActive(href, exact);

    return (
      <Link
        key={href}
        href={href}
        className={cn(
          "group flex items-center gap-3 rounded-2xl transition-all duration-200",
          compact ? "px-3 py-2.5 text-sm" : "px-4 py-3 text-[15px]",
          active
            ? "bg-[#243b73] text-white shadow-[0_10px_24px_rgba(15,23,42,0.24)]"
            : "text-slate-300 hover:bg-white/5 hover:text-white"
        )}
      >
        <span
          className={cn(
            "flex shrink-0 items-center justify-center rounded-xl border transition-colors",
            compact ? "h-8 w-8" : "h-9 w-9",
            active
              ? "border-white/15 bg-white/10 text-white"
              : "border-white/8 bg-white/[0.03] text-slate-400 group-hover:text-white"
          )}
        >
          <Icon className={compact ? "h-4 w-4" : "h-[18px] w-[18px]"} />
        </span>
        <span className={cn("leading-tight", active ? "font-semibold" : "font-medium")}>{label}</span>
      </Link>
    );
  };

  return (
    <aside className="macropulse-sidebar relative flex min-h-screen w-[264px] shrink-0 flex-col text-white 2xl:w-[280px]">
      <div className="px-5 pb-5 pt-7">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[#243b73] shadow-[0_12px_24px_rgba(36,59,115,0.45)]">
            <HeartPulse className="h-6 w-6 text-cyan-100" />
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-cyan-300/80">Intelli Stream</p>
            <h1 className="text-lg font-bold tracking-tight text-white">Macro Pulse</h1>
          </div>
        </div>
      </div>

      <div className="px-3">
        <button
          onClick={() => router.push("/stream/applications")}
          className="flex w-full items-center gap-2 rounded-2xl px-3 py-2.5 text-sm text-slate-300 transition hover:bg-white/5 hover:text-white"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to Applications
        </button>
      </div>

      <div className="mt-4 flex-1 overflow-y-auto px-3 pb-5">
        <nav className="space-y-2">
          {TOP_NAV.map((item) => renderLink(item))}
        </nav>

        <div className="mt-6">
          <p className="px-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            Sub Features
          </p>
          <nav className="mt-3 space-y-1.5">
            {FEATURE_NAV.map((item) => renderLink({ ...item, compact: true }))}
          </nav>
        </div>

        <div className="mt-6 border-t border-white/8 pt-4">
          <p className="px-4 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-500">
            Support
          </p>
          <nav className="mt-3 space-y-1.5">
            {SUPPORT_NAV.map((item) => renderLink({ ...item, compact: true }))}
          </nav>
        </div>
      </div>
    </aside>
  );
}
