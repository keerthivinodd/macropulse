"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { AlertTriangle, Calendar, Download, Filter, Loader2, Play, TrendingDown, TrendingUp } from "lucide-react";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { ensureTenantProfile, getSensitivity } from "@/services/macropulse";
import type { SensitivityResponse, TenantProfile } from "@/types/macropulse";

// ─── filter config ───────────────────────────────────────────────────────────

const VARIABLE_KEYS = [
  { key: "ALL", label: "All Variables" },
  { key: "REPO_RATE", label: "Repo Rate" },
  { key: "FX_USD_INR", label: "FX USD/INR" },
  { key: "WPI_INFLATION", label: "WPI Inflation" },
  { key: "CRUDE_OIL", label: "Crude Oil" },
  { key: "GSEC_YIELD", label: "G-Sec Yield" },
] as const;

const SCENARIO_OPTIONS = [
  { key: "base", label: "Base Case", multiplier: 1, color: "text-slate-700", badge: "bg-slate-100 text-slate-700", barColor: "#1a2332" },
  { key: "stress", label: "Stress (2×)", multiplier: 2, color: "text-amber-700", badge: "bg-amber-100 text-amber-700", barColor: "#d97706" },
  { key: "worst", label: "Worst Case (4×)", multiplier: 4, color: "text-red-700", badge: "bg-red-100 text-red-700", barColor: "#dc2626" },
] as const;

const REGION_OPTIONS = ["IN", "UAE", "SA"] as const;
const PERIOD_OPTIONS = ["1M", "3M", "6M", "YTD"] as const;

type ScenarioKey = (typeof SCENARIO_OPTIONS)[number]["key"];
type RegionKey = (typeof REGION_OPTIONS)[number];
type PeriodKey = (typeof PERIOD_OPTIONS)[number];
type VariableKey = (typeof VARIABLE_KEYS)[number]["key"];

const CARDS_META = [
  { key: "Repo_Rate", title: "Borrowing Cost Impact", badge: "Rate Sensitive", icon: "📊", description: "Effect of RBI repo rate changes on floating rate debt servicing costs." },
  { key: "FX_USD_INR", title: "Currency Risk Exposure", badge: "FX Exposure", icon: "💱", description: "USD/INR volatility impact on net USD-denominated payables and receivables." },
  { key: "WPI_Inflation", title: "Material Price Inflation", badge: "Input Cost", icon: "📦", description: "WPI-driven cost escalation across steel, petroleum, and key raw material inputs." },
  { key: "Crude_Oil", title: "Crude Oil Sensitivity", badge: "Energy Risk", icon: "🛢️", description: "Brent crude price movement translated to COGS and freight cost exposure." },
  { key: "GSec_Yield", title: "Investment MTM Impact", badge: "Treasury", icon: "🏛️", description: "G-Sec yield shift mark-to-market effect on held-to-maturity bond portfolio." },
];

const PERIOD_MULTIPLIER: Record<PeriodKey, number> = { "1M": 0.083, "3M": 0.25, "6M": 0.5, YTD: 0.75 };

// Fallback profile and sensitivity shown when the backend is unavailable
const FALLBACK_PROFILE = {
  tenant_id: "demo-in-001", company_name: "Demo Corp (India)", primary_region: "IN" as const,
  primary_currency: "INR" as const,
  debt: { total_loan_amount_cr: 250, rate_type: "MCLR" as const, current_effective_rate_pct: 9.25, floating_proportion_pct: 65, short_term_debt_cr: 80, long_term_debt_cr: 170 },
  fx: { net_usd_exposure_m: 12.5, net_aed_exposure_m: 0, net_sar_exposure_m: 0, hedge_ratio_pct: 45, hedge_instrument: "Forward" as const },
  cogs: { total_cogs_cr: 180, steel_pct: 22, petroleum_pct: 18, electronics_pct: 15, freight_pct: 12, other_pct: 33 },
  portfolio: { gsec_holdings_cr: 60, modified_duration: 3.8 },
  logistics: { primary_routes: ["Mumbai–Delhi", "Chennai–Bangalore"], monthly_shipment_value_cr: 22, inventory_buffer_days: 45 },
  notification_config: { channels: ["email" as const], teams_webhook: null, slack_webhook: null },
};

const FALLBACK_SENSITIVITY: Record<string, { impact_cr: number; label: string }> = {
  REPO_RATE:     { impact_cr: 3.25, label: "RBI repo rate +25bps → borrowing cost" },
  FX_USD_INR:    { impact_cr: 5.80, label: "USD/INR 1% depreciation → net USD payables" },
  WPI_INFLATION: { impact_cr: 2.40, label: "WPI +1% → input material cost escalation" },
  CRUDE_OIL:     { impact_cr: 4.15, label: "Brent +$5/bbl → COGS and freight" },
  GSEC_YIELD:    { impact_cr: 1.60, label: "G-Sec +10bps → MTM mark-down on portfolio" },
};

// ─── components ──────────────────────────────────────────────────────────────

function ImpactBar({ value, max, color }: { value: number; max: number; color: string }) {
  const pct = max > 0 ? Math.min(100, (Math.abs(value) / max) * 100) : 0;
  return (
    <div className="mt-3 h-1.5 w-full rounded-full bg-gray-100 overflow-hidden">
      <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

function SensitivityCard({
  meta,
  value,
  scenario,
  period,
  isFiltered,
}: {
  meta: (typeof CARDS_META)[number];
  value: number | undefined;
  scenario: (typeof SCENARIO_OPTIONS)[number];
  period: PeriodKey;
  isFiltered: boolean;
}) {
  if (isFiltered) return null;
  const adjusted = value !== undefined ? value * scenario.multiplier * (PERIOD_MULTIPLIER[period] ?? 1) : undefined;
  const isWorst = scenario.key === "worst";
  const isStress = scenario.key === "stress";

  return (
    <div className={`bg-white rounded-2xl p-6 shadow-sm border transition-all duration-300 ${
      isWorst ? "border-red-200 ring-1 ring-red-100" : isStress ? "border-amber-200" : "border-gray-100"
    }`}>
      <div className="flex items-start justify-between mb-4">
        <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-lg ${
          isWorst ? "bg-red-50" : isStress ? "bg-amber-50" : "bg-gray-100"
        }`}>
          {meta.icon}
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className={`text-[10px] font-bold tracking-widest rounded-full px-2.5 py-1 uppercase ${scenario.badge}`}>
            {scenario.label}
          </span>
          <span className="text-[10px] font-bold tracking-widest text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full uppercase">
            {meta.badge}
          </span>
        </div>
      </div>

      <p className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-2">{meta.title}</p>

      <div className="flex items-end gap-2 mb-1">
        <span className={`text-4xl font-black ${isWorst ? "text-red-700" : isStress ? "text-amber-700" : "text-gray-900"}`}>
          {adjusted !== undefined ? `₹${adjusted.toFixed(2)}` : "--"}
        </span>
        <span className="text-sm text-gray-500 mb-1">Cr / {period}</span>
      </div>

      {isWorst && <div className="flex items-center gap-1.5 text-xs text-red-600 font-semibold mb-1"><AlertTriangle className="h-3.5 w-3.5" /> Worst-case scenario</div>}

      <p className="text-xs text-gray-500 leading-5">{meta.description}</p>

      <ImpactBar
        value={adjusted ?? 0}
        max={50}
        color={scenario.barColor}
      />
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function FinancialImpactLivePage() {
  const router = useRouter();
  const { tenantId, ready } = useMacroPulseTenant();
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [usingFallback, setUsingFallback] = useState(false);

  // Filters
  const [variable, setVariable] = useState<VariableKey>("ALL");
  const [scenario, setScenario] = useState<ScenarioKey>("base");
  const [region, setRegion] = useState<RegionKey>("IN");
  const [period, setPeriod] = useState<PeriodKey>("YTD");

  useEffect(() => {
    if (!ready) return;
    const load = async () => {
      setLoading(true);
      try {
        const tenant = await ensureTenantProfile(tenantId);
        const matrix = await getSensitivity(tenantId);
        setProfile(tenant);
        setSensitivity(matrix);
        setUsingFallback(false);
      } catch {
        setProfile(FALLBACK_PROFILE as unknown as TenantProfile);
        setSensitivity({ data: FALLBACK_SENSITIVITY, source: "cache" });
        setUsingFallback(true);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [ready, tenantId]);

  const handleExport = () => {
    const payload = { sensitivity: sensitivityData, scenario, period, region, generated_at: new Date().toISOString() };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `macropulse-sensitivity-${tenantId}-${period}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const activeScenario = useMemo(
    () => SCENARIO_OPTIONS.find((s) => s.key === scenario) ?? SCENARIO_OPTIONS[0],
    [scenario]
  );

  const sensitivityData = sensitivity?.data ?? FALLBACK_SENSITIVITY;

  const totalImpact = useMemo(() => {
    return CARDS_META.reduce((sum, c) => {
      const val = sensitivityData[c.key]?.impact_cr ?? 0;
      return sum + val * activeScenario.multiplier * (PERIOD_MULTIPLIER[period] ?? 1);
    }, 0);
  }, [sensitivityData, activeScenario, period]);

  return (
    <div className="px-8 py-7 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold tracking-widest text-blue-600 uppercase bg-blue-50 px-2.5 py-1 rounded-full">Live Sensitivity</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest">Tenant: {tenantId}</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900">Strategic Exposure Dashboard</h2>
          <p className="text-sm text-gray-500 mt-1">Real P&amp;L sensitivity from live tenant profile · filtered by macro variable, scenario, and time horizon.</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {usingFallback && (
            <span className="text-[10px] font-bold uppercase tracking-wider rounded-full bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-1">
              Indicative data
            </span>
          )}
          <button
            onClick={handleExport}
            className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition"
          >
            <Download className="w-4 h-4" /> Export
          </button>
          <button
            onClick={() => router.push("/stream/macropulse/simulation")}
            className="flex items-center gap-2 px-5 py-2.5 bg-[#1a2332] text-white rounded-lg text-sm font-bold hover:bg-[#243044] transition"
          >
            <Play className="w-4 h-4" /> Run Simulation
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
            <Calendar className="w-4 h-4" /> Live Matrix
          </button>
        </div>
      </div>

      {/* ── Filter Bar ─────────────────────────────────────────────────────── */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-500 uppercase tracking-widest shrink-0">
            <Filter className="h-3.5 w-3.5" /> Filters
          </div>

          {/* Macro Variable */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-semibold">Variable:</span>
            <div className="flex overflow-hidden rounded-lg border border-gray-200">
              {VARIABLE_KEYS.map((v) => (
                <button
                  key={v.key}
                  onClick={() => setVariable(v.key as VariableKey)}
                  className={`px-3 py-1.5 text-xs font-semibold transition ${variable === v.key ? "bg-[#1a2332] text-white" : "text-gray-500 hover:bg-gray-50"}`}
                >
                  {v.label}
                </button>
              ))}
            </div>
          </div>

          {/* Scenario */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-semibold">Scenario:</span>
            <div className="flex overflow-hidden rounded-lg border border-gray-200">
              {SCENARIO_OPTIONS.map((s) => (
                <button
                  key={s.key}
                  onClick={() => setScenario(s.key)}
                  className={`px-3 py-1.5 text-xs font-semibold transition ${
                    scenario === s.key
                      ? s.key === "worst" ? "bg-red-600 text-white" : s.key === "stress" ? "bg-amber-500 text-white" : "bg-[#1a2332] text-white"
                      : "text-gray-500 hover:bg-gray-50"
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>

          {/* Region */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-semibold">Region:</span>
            <div className="flex overflow-hidden rounded-lg border border-gray-200">
              {REGION_OPTIONS.map((r) => (
                <button
                  key={r}
                  onClick={() => setRegion(r)}
                  className={`px-3 py-1.5 text-xs font-semibold transition ${region === r ? "bg-[#1a2332] text-white" : "text-gray-500 hover:bg-gray-50"}`}
                >
                  {r}
                </button>
              ))}
            </div>
          </div>

          {/* Period */}
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-gray-400 font-semibold">Period:</span>
            <div className="flex overflow-hidden rounded-lg border border-gray-200">
              {PERIOD_OPTIONS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPeriod(p)}
                  className={`px-3 py-1.5 text-xs font-semibold transition ${period === p ? "bg-[#1a2332] text-white" : "text-gray-500 hover:bg-gray-50"}`}
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Summary strip */}
        {!loading && (
          <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-6 flex-wrap">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Total Exposure ({period})</p>
              <div className="flex items-center gap-2 mt-0.5">
                {totalImpact >= 0
                  ? <TrendingUp className="h-4 w-4 text-red-500" />
                  : <TrendingDown className="h-4 w-4 text-emerald-500" />}
                <span className={`text-xl font-black ${scenario === "worst" ? "text-red-700" : scenario === "stress" ? "text-amber-700" : "text-gray-900"}`}>
                  ₹{Math.abs(totalImpact).toFixed(2)} Cr
                </span>
                <span className={`text-[11px] font-bold rounded-full px-2.5 py-0.5 ${activeScenario.badge}`}>{activeScenario.label}</span>
              </div>
            </div>
            <div className="text-xs text-gray-500">
              Region: <span className="font-semibold text-gray-700">{region}</span> ·{" "}
              Source: <span className="font-semibold text-gray-700">{sensitivity?.source ?? "--"}</span>
            </div>
          </div>
        )}
      </div>

      {/* ── Cards ──────────────────────────────────────────────────────────── */}
      {loading ? (
        <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-gray-100 bg-white shadow-sm">
          <Loader2 className="mr-3 h-5 w-5 animate-spin text-slate-400" />
          <span className="text-sm text-slate-500">Loading sensitivity matrix...</span>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-5 xl:grid-cols-2 2xl:grid-cols-3">
            {CARDS_META.map((card) => (
              <SensitivityCard
                key={card.key}
                meta={card}
                value={sensitivityData[card.key]?.impact_cr}
                scenario={activeScenario}
                period={period}
                isFiltered={variable !== "ALL" && variable !== card.key}
              />
            ))}
          </div>

          {/* Tenant Baseline */}
          <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-xl font-black text-gray-900">Tenant exposure baseline</h3>
              <p className="text-sm text-gray-500 mt-1 mb-5">Live tenant profile values driving the sensitivity engine. Region: {region}.</p>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {[
                  { label: "Loan Book", value: `₹${profile?.debt.total_loan_amount_cr.toFixed(2) ?? "--"} Cr` },
                  { label: "Floating Debt", value: `${profile?.debt.floating_proportion_pct.toFixed(0) ?? "--"}%` },
                  { label: "Net USD Exposure", value: `$${profile?.fx.net_usd_exposure_m.toFixed(2) ?? "--"}M` },
                  { label: "Annual COGS", value: `₹${profile?.cogs.total_cogs_cr.toFixed(2) ?? "--"} Cr` },
                  { label: "G-Sec Holdings", value: `₹${profile?.portfolio.gsec_holdings_cr.toFixed(2) ?? "--"} Cr` },
                  { label: "Inventory Buffer", value: `${profile?.logistics.inventory_buffer_days ?? "--"} days` },
                ].map((item) => (
                  <div key={item.label} className="rounded-xl border border-gray-100 bg-gray-50/70 p-4">
                    <p className="text-[10px] font-bold tracking-widest text-gray-500 uppercase">{item.label}</p>
                    <p className="mt-2 text-lg font-bold text-gray-900">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className={`rounded-2xl p-6 text-white ${scenario === "worst" ? "bg-red-800" : scenario === "stress" ? "bg-amber-700" : "bg-[#1a2332]"}`}>
              <h3 className="text-lg font-bold">Active scenario</h3>
              <p className="mt-2 text-sm leading-6 text-white/70">
                {scenario === "worst"
                  ? "Worst-case multiplier (4×) applied. These figures represent extreme tail-risk events — use for stress testing and capital buffers, not operating forecasts."
                  : scenario === "stress"
                  ? "Stress scenario (2×) applied. Moderate adverse shock — suitable for sensitivity disclosure and hedge sizing review."
                  : "Base case sensitivity. Reflects current tenant profile and live macro rates without amplification."}
              </p>
              <div className="mt-5 space-y-3 text-sm">
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <span className="text-white/60">Scenario</span>
                  <span className="font-semibold">{activeScenario.label}</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <span className="text-white/60">Multiplier</span>
                  <span className="font-semibold">{activeScenario.multiplier}×</span>
                </div>
                <div className="flex items-center justify-between border-b border-white/10 pb-3">
                  <span className="text-white/60">Period</span>
                  <span className="font-semibold">{period}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-white/60">Matrix source</span>
                  <span className="font-semibold">{sensitivity?.source ?? "--"}</span>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
