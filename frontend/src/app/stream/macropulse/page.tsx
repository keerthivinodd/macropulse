"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  BadgeCheck,
  Banknote,
  Bot,
  Gauge,
  GitMerge,
  HeartPulse,
  Loader2,
  RefreshCw,
  Shield,
  Waves,
} from "lucide-react";
import Link from "next/link";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { ensureTenantProfile, getMacroPulseDashboard } from "@/services/macropulse";
import type { MacroPulseDashboard } from "@/types/macropulse";
import { formatDateTime, formatNumber } from "@/utils/macropulse/format";

const CAPABILITIES = [
  {
    icon: Activity,
    title: "Real-Time Macro Monitoring",
    description: "Live ingestion of RBI policy rates, FX markets, WPI inflation, Brent crude, and regional central bank signals across India, UAE, and Saudi Arabia.",
    href: "/stream/macropulse/realtime",
    color: "text-sky-700",
    bg: "bg-sky-50",
    border: "border-sky-100",
  },
  {
    icon: GitMerge,
    title: "Simulation Impact",
    description: "Model historical shocks (2008 crisis, COVID, oil crash) or custom macro scenarios to stress-test margins and quantify worst-case P&L exposure — with live financial impact analysis.",
    href: "/stream/macropulse/simulation",
    color: "text-violet-700",
    bg: "bg-violet-50",
    border: "border-violet-100",
  },
  {
    icon: Bot,
    title: "MacroPulse Agent",
    description: "AI-powered CFO assistant that answers natural language macro questions, runs simulations, and generates actionable financial briefs on demand.",
    href: "/stream/macropulse/agent",
    color: "text-indigo-700",
    bg: "bg-indigo-50",
    border: "border-indigo-100",
  },
];

const FALLBACK_TILES = {
  repo_rate_pct: 6.50, repo_rate_change_bps: -25,
  usd_inr_rate: 83.45, usd_inr_7d_change_pct: 0.38,
  wpi_index: 163.28, wpi_mom_change_pct: 2.76,
  brent_usd: 82.50, brent_mom_change_pct: -1.40,
  repo_rate_alert: false, fx_alert: false, inflation_alert: false, oil_alert: false,
};

export default function MacroPulsePage() {
  const { tenantId, ready } = useMacroPulseTenant();
  const [dashboard, setDashboard] = useState<MacroPulseDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!ready) return;
    setLoading(true);
    try {
      await ensureTenantProfile(tenantId);
      const data = await getMacroPulseDashboard(tenantId);
      setDashboard(data);
    } catch {
      // keep dashboard as-is; tiles fall back to FALLBACK_TILES below
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, [ready, tenantId]);

  const tiles = dashboard?.kpi_tiles ?? FALLBACK_TILES;

  const topSensitivity = useMemo(() => {
    if (!dashboard) return [];
    return Object.entries(dashboard.sensitivity_matrix)
      .sort((a, b) => Math.abs(b[1]?.impact_cr ?? 0) - Math.abs(a[1]?.impact_cr ?? 0))
      .slice(0, 3);
  }, [dashboard]);

  return (
    <div className="h-full overflow-y-auto px-6 py-6 lg:px-8 space-y-6">

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <div className="macropulse-panel rounded-[24px] border border-white/70 p-6">
        <div className="flex flex-col gap-5 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex items-start gap-4">
            <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-[#1a2332] shadow-lg">
              <HeartPulse className="h-7 w-7 text-cyan-300" />
            </div>
            <div>
              <div className="macropulse-chip inline-flex items-center rounded-full border border-white/70 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.28em] text-sky-800 mb-2">
                Intelli Stream
              </div>
              <h1 className="text-3xl font-black leading-tight tracking-tight text-[#0f2356]">
                MacroPulse
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">
                An end-to-end macroeconomic intelligence platform — ingesting central bank policy signals, FX markets, commodity prices, and inflation data to deliver CFO-ready financial impact analysis in real time.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={() => void load()}
              className="macropulse-chip inline-flex items-center gap-2 rounded-full border border-cyan-200/80 px-4 py-2 text-sm font-semibold text-sky-800"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Live KPI strip */}
        <div className="mt-6 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {loading ? (
            <div className="col-span-4 flex items-center justify-center py-8 text-slate-500">
              <Loader2 className="mr-3 h-5 w-5 animate-spin" />
              Loading live macro snapshot...
            </div>
          ) : (
            [
              { label: "Repo Rate", value: `${formatNumber(tiles.repo_rate_pct)}%`, change: tiles.repo_rate_change_bps, suffix: " bps", icon: Banknote },
              { label: "USD / INR", value: formatNumber(tiles.usd_inr_rate, 3), change: tiles.usd_inr_7d_change_pct, suffix: "%", icon: Gauge },
              { label: "WPI Index", value: formatNumber(tiles.wpi_index), change: tiles.wpi_mom_change_pct, suffix: "%", icon: Waves },
              { label: "Brent Crude", value: `$${formatNumber(tiles.brent_usd)}`, change: tiles.brent_mom_change_pct, suffix: "%", icon: Activity },
            ].map((card) => (
              <div key={card.label} className="macropulse-card rounded-[20px] border border-white/80 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-cyan-100 bg-white/70">
                    <card.icon className="h-4 w-4 text-sky-700" />
                  </div>
                  <span className={`text-xs font-bold ${(card.change ?? 0) > 0 ? "text-red-600" : (card.change ?? 0) < 0 ? "text-emerald-600" : "text-slate-400"}`}>
                    {card.change == null ? "--" : `${card.change > 0 ? "+" : ""}${card.change.toFixed(2)}${card.suffix}`}
                  </span>
                </div>
                <p className="mt-3 text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">{card.label}</p>
                <p className="mt-1 text-2xl font-black tracking-tight text-slate-900">{card.value}</p>
              </div>
            ))
          )}
        </div>
      </div>

      {/* ── Capabilities Grid ─────────────────────────────────────────────── */}
      <div>
        <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-sky-700 mb-3">Platform Capabilities</p>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <Link
              key={cap.href}
              href={cap.href}
              className="group macropulse-card rounded-[22px] border border-white/80 p-5 transition hover:shadow-md"
            >
              <div className={`mb-3 flex h-10 w-10 items-center justify-center rounded-xl border ${cap.border} ${cap.bg}`}>
                <cap.icon className={`h-5 w-5 ${cap.color}`} />
              </div>
              <h3 className="text-sm font-bold text-slate-900">{cap.title}</h3>
              <p className="mt-1.5 text-xs leading-5 text-slate-500">{cap.description}</p>
              <div className={`mt-3 flex items-center gap-1 text-xs font-semibold ${cap.color} opacity-0 group-hover:opacity-100 transition`}>
                Open <ArrowRight className="h-3.5 w-3.5" />
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* ── Live Status + Sensitivity ─────────────────────────────────────── */}
      {!loading && dashboard && (
        <div className="grid gap-4 xl:grid-cols-[1fr_340px]">
          {/* Sensitivity */}
          <div className="macropulse-soft-card rounded-[22px] border border-white/70 p-5">
            <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-sky-700">Top Sensitivities</p>
            <h3 className="mt-1 text-base font-bold text-slate-900">Highest financial exposures right now</h3>
            <div className="mt-4 space-y-3">
              {topSensitivity.map(([key, metric]) => (
                <div key={key} className="rounded-2xl border border-white/80 bg-white/70 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                        {key.replaceAll("_", " ")}
                      </p>
                      <p className="mt-0.5 text-sm text-slate-700">{metric.label}</p>
                    </div>
                    <span className="text-sm font-bold text-slate-900 shrink-0">₹{metric.impact_cr.toFixed(2)} Cr</span>
                  </div>
                </div>
              ))}
              {topSensitivity.length === 0 && (
                <p className="text-sm text-slate-400">No sensitivity data yet.</p>
              )}
            </div>
          </div>

          {/* Signal posture + freshness */}
          <div className="space-y-4">
            <div className="macropulse-soft-card rounded-[22px] border border-white/70 p-5">
              <div className="flex items-start gap-3">
                <div className={`rounded-xl p-2 ${tiles?.repo_rate_alert || tiles?.fx_alert || tiles?.inflation_alert || tiles?.oil_alert ? "bg-red-100" : "bg-emerald-100"}`}>
                  <Shield className={`h-4 w-4 ${tiles?.repo_rate_alert || tiles?.fx_alert || tiles?.inflation_alert || tiles?.oil_alert ? "text-red-600" : "text-emerald-600"}`} />
                </div>
                <div>
                  <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-sky-700">Signal Posture</p>
                  <h3 className="mt-1 text-sm font-bold text-slate-900">
                    {tiles?.repo_rate_alert || tiles?.fx_alert || tiles?.inflation_alert || tiles?.oil_alert
                      ? "Actionable macro alert(s) detected"
                      : "No high-priority alerts"}
                  </h3>
                  <p className="mt-1 text-xs text-slate-500">
                    {dashboard.live_alerts.length} active alert{dashboard.live_alerts.length !== 1 ? "s" : ""} · {dashboard.primary_currency} · {formatDateTime(dashboard.generated_at)}
                  </p>
                </div>
              </div>
            </div>

            <div className="macropulse-soft-card rounded-[22px] border border-white/70 p-5">
              <p className="text-[10px] font-semibold uppercase tracking-[0.28em] text-sky-700 mb-3">Source Freshness</p>
              <div className="space-y-2">
                {[
                  { label: "RBI", value: dashboard.data_freshness.rbi },
                  { label: "FX Rates", value: dashboard.data_freshness.fx_rates },
                  { label: "Commodities", value: dashboard.data_freshness.commodities },
                  { label: "News", value: dashboard.data_freshness.news },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between rounded-xl border border-white/80 bg-white/70 px-3 py-2">
                    <div className="flex items-center gap-2">
                      <BadgeCheck className="h-3.5 w-3.5 text-emerald-500" />
                      <span className="text-xs font-medium text-slate-700">{item.label}</span>
                    </div>
                    <span className="text-[11px] text-slate-500">{formatDateTime(item.value)}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
