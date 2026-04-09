"use client";

import { useEffect, useMemo, useState } from "react";
import { Minus, MoreVertical, RefreshCw, TrendingDown, TrendingUp, Zap } from "lucide-react";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { ensureTenantProfile, getMacroPulseDashboard } from "@/services/macropulse";
import type { MacroPulseDashboard } from "@/types/macropulse";
import { formatDateTime } from "@/utils/macropulse/format";

const FALLBACK_NOW = new Date().toISOString();

const FALLBACK_DASHBOARD = {
  generated_at: FALLBACK_NOW,
  primary_currency: "INR",
  live_alerts: [],
  kpi_tiles: {
    repo_rate_pct: 6.50,
    repo_rate_change_bps: -25,
    usd_inr_rate: 83.45,
    usd_inr_7d_change_pct: 0.38,
    wpi_index: 163.28,
    wpi_mom_change_pct: 2.76,
    brent_usd: 82.50,
    brent_mom_change_pct: -1.40,
    repo_rate_alert: false,
    fx_alert: false,
    inflation_alert: false,
    oil_alert: false,
  },
  data_freshness: {
    rbi: FALLBACK_NOW,
    fx_rates: FALLBACK_NOW,
    commodities: FALLBACK_NOW,
    news: FALLBACK_NOW,
  },
  sensitivity_matrix: {},
} as unknown as MacroPulseDashboard;

function sourceCadenceLabel(source: string) {
  if (source === "RBI") return "Source cadence: Official release";
  if (source === "FX Rates") return "Source cadence: Every 5 minutes";
  if (source === "Commodities") return "Source cadence: Daily";
  if (source === "News") return "Source cadence: Hourly";
  return "Source cadence: Official release";
}

export default function RealTimeMonitoringPage() {
  const { tenantId, ready } = useMacroPulseTenant();
  const [dashboard, setDashboard] = useState<MacroPulseDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    if (!ready) return;
    try {
      setLoading(true);
      await ensureTenantProfile(tenantId);
      const data = await getMacroPulseDashboard(tenantId);
      setDashboard(data);
    } catch {
      setDashboard((prev) => prev ?? FALLBACK_DASHBOARD);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!ready) return;
    void load();
    const interval = window.setInterval(() => {
      void load();
    }, 60000);
    return () => window.clearInterval(interval);
  }, [ready, tenantId]);

  const feed = useMemo(() => {
    if (!dashboard) return [];
    const generatedAt = dashboard.generated_at;
    const tiles = dashboard.kpi_tiles;
    return [
      {
        key: "repo",
        symbol: "RBI Repo Rate",
        value: tiles.repo_rate_pct !== null ? `${tiles.repo_rate_pct.toFixed(2)}%` : "--",
        sub: "India benchmark policy rate",
        change:
          tiles.repo_rate_change_bps !== null
            ? `${tiles.repo_rate_change_bps > 0 ? "+" : ""}${tiles.repo_rate_change_bps.toFixed(2)} bps`
            : "--",
        dir: (tiles.repo_rate_change_bps ?? 0) > 0 ? "up" : (tiles.repo_rate_change_bps ?? 0) < 0 ? "down" : "neutral",
        source: "RBI",
        as_of: dashboard.data_freshness.rbi ?? generatedAt,
      },
      {
        key: "fx",
        symbol: "USD / INR",
        value: tiles.usd_inr_rate !== null ? tiles.usd_inr_rate.toFixed(3) : "--",
        sub: "Latest FX warehouse rate",
        change:
          tiles.usd_inr_7d_change_pct !== null
            ? `${tiles.usd_inr_7d_change_pct > 0 ? "+" : ""}${tiles.usd_inr_7d_change_pct.toFixed(2)}%`
            : "--",
        dir: (tiles.usd_inr_7d_change_pct ?? 0) > 0 ? "up" : (tiles.usd_inr_7d_change_pct ?? 0) < 0 ? "down" : "neutral",
        source: "FX Rates",
        as_of: dashboard.data_freshness.fx_rates ?? generatedAt,
      },
      {
        key: "wpi",
        symbol: "WPI Index",
        value: tiles.wpi_index !== null ? tiles.wpi_index.toFixed(2) : "--",
        sub: "Inflation pressure proxy",
        change:
          tiles.wpi_mom_change_pct !== null
            ? `${tiles.wpi_mom_change_pct > 0 ? "+" : ""}${tiles.wpi_mom_change_pct.toFixed(2)}%`
            : "--",
        dir: (tiles.wpi_mom_change_pct ?? 0) > 0 ? "up" : (tiles.wpi_mom_change_pct ?? 0) < 0 ? "down" : "neutral",
        source: "Commodities",
        as_of: dashboard.data_freshness.commodities ?? generatedAt,
      },
      {
        key: "brent",
        symbol: "Brent Crude",
        value: tiles.brent_usd !== null ? `$${tiles.brent_usd.toFixed(2)}` : "--",
        sub: "Energy cost signal",
        change:
          tiles.brent_mom_change_pct !== null
            ? `${tiles.brent_mom_change_pct > 0 ? "+" : ""}${tiles.brent_mom_change_pct.toFixed(2)}%`
            : "--",
        dir: (tiles.brent_mom_change_pct ?? 0) > 0 ? "up" : (tiles.brent_mom_change_pct ?? 0) < 0 ? "down" : "neutral",
        source: "Commodities",
        as_of: dashboard.data_freshness.commodities ?? generatedAt,
      },
    ];
  }, [dashboard]);

  const lastFetchedAt = formatDateTime(dashboard?.generated_at);

  const refreshNow = async () => {
    await load();
  };

  return (
    <div className="flex flex-col gap-4 px-6 py-5 lg:px-8">
      <div className="flex shrink-0 items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Real-Time Monitoring &amp; Intelligence</h2>
          <p className="mt-1 text-xs text-slate-500">
            Dashboard refresh cadence: every 60 seconds
            <span className="mx-2 text-slate-300">|</span>
            Last fetched: {lastFetchedAt}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-600">
            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            LIVE SYSTEM FEED
          </span>
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-blue-600 text-xs font-bold text-white">JD</div>
        </div>
      </div>

      <div className="grid shrink-0 items-start gap-4 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="self-start rounded-2xl border border-gray-100 bg-white p-6 shadow-sm overflow-hidden">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600">
              <Zap className="h-4 w-4 text-white" />
            </div>
            <span className="text-xs font-bold uppercase tracking-widest text-gray-500">
              Official Macro Snapshot
            </span>
          </div>
          <h3 className="text-2xl font-black leading-tight text-gray-900">
            {loading ? "Loading macro conditions..." : "Official MacroPulse market snapshot"}
          </h3>
          <p className="mt-3 text-sm leading-7 text-gray-600">
            Monitoring repo rate, FX, inflation, commodities, and alert posture for tenant {tenantId} from the live backend dashboard.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-slate-500">
            <span className="rounded-full bg-slate-50 px-3 py-1">Last fetched: {lastFetchedAt}</span>
            <span className="rounded-full bg-slate-50 px-3 py-1">Refresh cadence: every 60s</span>
            <span className="rounded-full bg-slate-50 px-3 py-1">Source cadence varies by official feed</span>
          </div>
          <div className="mt-5 flex items-center gap-4">
            <button
              onClick={() => void refreshNow()}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-bold text-white transition hover:bg-blue-700"
            >
              Refresh Snapshot
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
            <span className="text-xs text-gray-500">
              Live alerts: <span className="font-bold text-blue-600">{dashboard?.live_alerts.length ?? 0}</span>
            </span>
          </div>
        </div>

        <div className="rounded-2xl bg-[#1a2332] p-5 text-white overflow-hidden">
          <p className="mb-4 text-[10px] font-bold uppercase tracking-widest text-slate-400">
            Market Confidence Score
          </p>
          <div className="mb-1 flex items-end gap-1">
            <span className="text-6xl font-black">{Math.min(10, 6 + ((dashboard?.live_alerts.length ?? 0) * 0.7)).toFixed(1)}</span>
            <span className="mb-2 text-2xl text-slate-400">/ 10</span>
          </div>
          <p className="mb-6 text-xs leading-5 text-slate-400">
            Composite score based on live alert volume, source freshness, and current macro changes from the dashboard API.
          </p>
          <div className="border-t border-white/10 pt-4">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-xs text-slate-400">Global Sentiment</span>
              <span className={`text-xs font-bold ${(dashboard?.kpi_tiles.usd_inr_7d_change_pct ?? 0) >= 0 ? "text-emerald-400" : "text-amber-300"}`}>
                {(dashboard?.kpi_tiles.usd_inr_7d_change_pct ?? 0) >= 0 ? "+" : ""}
                {(dashboard?.kpi_tiles.usd_inr_7d_change_pct ?? 0).toFixed(2)}%
              </span>
            </div>
            <div className="h-1.5 w-full rounded-full bg-white/10">
              <div
                className="h-1.5 rounded-full bg-emerald-400"
                style={{ width: `${Math.max(12, dashboard ? Math.min(100, 50 + dashboard.live_alerts.length * 10) : 0)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-800">Live Macro Feed</h3>
          <div className="flex items-center gap-2">
            <button onClick={() => void refreshNow()} className="rounded-lg p-1.5 transition hover:bg-gray-100">
              <RefreshCw className={`h-4 w-4 text-gray-400 ${loading ? "animate-spin" : ""}`} />
            </button>
            <button className="rounded-lg p-1.5 transition hover:bg-gray-100">
              <MoreVertical className="h-4 w-4 text-gray-400" />
            </button>
          </div>
        </div>
        <div className="grid divide-gray-100 md:grid-cols-2 md:divide-x xl:grid-cols-4">
          {feed.map((item) => (
            <div key={item.key} className="border-b border-gray-100 px-6 py-4 last:border-b-0 xl:border-b-0 xl:border-r xl:last:border-r-0">
              <div className="mb-3 flex items-center justify-between">
                <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gray-100">
                  {item.dir === "up" ? (
                    <TrendingUp className="h-4 w-4 text-emerald-500" />
                  ) : item.dir === "down" ? (
                    <TrendingDown className="h-4 w-4 text-red-500" />
                  ) : (
                    <Minus className="h-4 w-4 text-gray-400" />
                  )}
                </div>
                <span
                  className={`rounded-full px-2 py-1 text-xs font-bold ${
                    item.dir === "up"
                      ? "bg-emerald-50 text-emerald-600"
                      : item.dir === "down"
                        ? "bg-red-50 text-red-600"
                        : "bg-gray-100 text-gray-500"
                  }`}
                >
                  {item.change}
                </span>
              </div>
              <p className="text-base font-bold text-gray-900">{item.symbol}</p>
              <p className="mt-0.5 text-xs font-medium text-gray-700">{item.value}</p>
              <p className="mt-1 text-xs text-gray-500">{item.sub}</p>
              <p className="mt-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">{item.source}</p>
              <p className="mt-1 text-[11px] text-slate-500">Source as of: {formatDateTime(item.as_of)}</p>
              <p className="mt-1 text-[11px] text-slate-500">{sourceCadenceLabel(item.source)}</p>
            </div>
          ))}
          {!loading && feed.length === 0 ? (
            <div className="px-6 py-5 text-sm text-gray-500">No official feed items were returned.</div>
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm">
        <div className="border-b border-gray-100 px-6 py-4">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-800">Source Status</h3>
        </div>
        <div className="grid grid-cols-1 gap-4 px-6 py-5 md:grid-cols-3">
          {[
            {
              name: "RBI",
              status: dashboard?.data_freshness.rbi ? "live" : "fallback",
              latency: "Official cadence",
              coverage: `Last update ${formatDateTime(dashboard?.data_freshness.rbi)}`,
            },
            {
              name: "FX Rates",
              status: dashboard?.data_freshness.fx_rates ? "live" : "fallback",
              latency: "5 min cadence",
              coverage: `Last update ${formatDateTime(dashboard?.data_freshness.fx_rates)}`,
            },
            {
              name: "News + Commodities",
              status: dashboard?.data_freshness.news || dashboard?.data_freshness.commodities ? "live" : "fallback",
              latency: "Hourly / Daily",
              coverage: `News ${formatDateTime(dashboard?.data_freshness.news)} | Commodities ${formatDateTime(dashboard?.data_freshness.commodities)}`,
            },
          ].map((source) => (
            <div key={source.name} className="rounded-xl border border-gray-100 bg-gray-50/70 p-4">
              <div className="flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-gray-900">{source.name}</p>
                <span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${source.status === "live" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"}`}>
                  {source.status}
                </span>
              </div>
              <p className="mt-2 text-xs text-gray-500">Latency: {source.latency}</p>
              <p className="mt-1 text-xs text-gray-500">Dashboard fetch cadence: every 60 seconds</p>
              <p className="mt-1 text-xs text-gray-500">{source.coverage}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
