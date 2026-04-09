"use client";

import { useEffect, useRef, useState } from "react";
import {
  Bell,
  Building2,
  ChevronRight,
  Loader2,
  Radio,
  RefreshCw,
  Save,
  Settings,
  TrendingUp,
  Truck,
} from "lucide-react";
import { getCostRoutingStatus, getEventLog, getEventSchemas } from "@/services/macropulse";
import type { CostRoutingStatus, EventLogEntry } from "@/types/macropulse";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import {
  buildDefaultTenantProfile,
  ensureTenantProfile,
  updateTenantProfile,
} from "@/services/macropulse";
import type { TenantProfile } from "@/types/macropulse";

const LOCAL_PROFILE_PREFIX = "macropulse-local-tenant-profile";

function getLocalProfileKey(tenantId: string) {
  return `${LOCAL_PROFILE_PREFIX}:${tenantId}`;
}

function loadLocalProfile(tenantId: string): TenantProfile | null {
  if (typeof window === "undefined") return null;

  try {
    const raw = window.localStorage.getItem(getLocalProfileKey(tenantId));
    return raw ? (JSON.parse(raw) as TenantProfile) : null;
  } catch {
    return null;
  }
}

function saveLocalProfile(profile: TenantProfile) {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.setItem(
      getLocalProfileKey(profile.tenant_id),
      JSON.stringify(profile)
    );
  } catch {
    // Ignore local storage failures and keep the form usable.
  }
}

// ─── tabs ────────────────────────────────────────────────────────────────────

const TABS = [
  { id: "identity", label: "Identity", icon: Building2 },
  { id: "financial", label: "Financial Profile", icon: TrendingUp },
  { id: "logistics", label: "Logistics", icon: Truck },
  { id: "alerts", label: "Alerts & Notifications", icon: Bell },
  { id: "pipeline", label: "Pipeline & Events", icon: Radio },
] as const;

type TabId = (typeof TABS)[number]["id"];

// ─── field helpers ────────────────────────────────────────────────────────────

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="block text-xs font-bold uppercase tracking-widest text-gray-500">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-gray-400">{hint}</span>}
    </label>
  );
}

function TextInput({
  value,
  onChange,
  type = "text",
  placeholder,
}: {
  value: string | number;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-800 bg-gray-50/60 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
    />
  );
}

function NumInput({
  value,
  onChange,
  placeholder,
}: {
  value: number;
  onChange: (v: number) => void;
  placeholder?: string;
}) {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      placeholder={placeholder}
      className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-800 bg-gray-50/60 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
    />
  );
}

function SelectInput({
  value,
  options,
  onChange,
}: {
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (v: string) => void;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm text-gray-800 bg-gray-50/60 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function SectionCard({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-4">
      <div>
        <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider">{title}</h3>
        {description && <p className="mt-0.5 text-xs text-gray-500">{description}</p>}
      </div>
      {children}
    </div>
  );
}

function PercentBar({ pct, color }: { pct: number; color: string }) {
  return (
    <div className="h-1.5 w-full rounded-full bg-gray-100 overflow-hidden mt-1">
      <div className="h-full rounded-full transition-all" style={{ width: `${pct}%`, backgroundColor: color }} />
    </div>
  );
}

// ─── main page ────────────────────────────────────────────────────────────────

export default function ConfigLivePage() {
  const { tenantId, setTenantId, ready } = useMacroPulseTenant();
  const [draftTenantId, setDraftTenantId] = useState(tenantId);
  const [profile, setProfile] = useState<TenantProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("identity");

  // Pipeline & Events tab state
  const [costStatus, setCostStatus] = useState<CostRoutingStatus | null>(null);
  const [eventLog, setEventLog] = useState<EventLogEntry[]>([]);
  const [eventSchemas, setEventSchemas] = useState<Record<string, unknown> | null>(null);
  const [pipelineLoading, setPipelineLoading] = useState(false);
  const pipelineLoaded = useRef(false);

  const loadPipelineData = async () => {
    setPipelineLoading(true);
    try {
      const [cost, events, schemas] = await Promise.all([
        getCostRoutingStatus().catch(() => null),
        getEventLog().catch(() => [] as EventLogEntry[]),
        getEventSchemas().catch(() => null),
      ]);
      setCostStatus(cost);
      setEventLog(events);
      setEventSchemas(schemas);
      pipelineLoaded.current = true;
    } finally {
      setPipelineLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "pipeline" && !pipelineLoaded.current) void loadPipelineData();
  }, [activeTab]);

  useEffect(() => { setDraftTenantId(tenantId); }, [tenantId]);

  useEffect(() => {
    if (!ready) return;
    const load = async () => {
      setLoading(true);
      setLoadError(null);
      try {
        const ensuredProfile = await ensureTenantProfile(tenantId);
        setProfile(ensuredProfile);
        saveLocalProfile(ensuredProfile);
        setMessage(null);
      } catch {
        const localProfile = loadLocalProfile(tenantId);
        const fallbackProfile = localProfile ?? buildDefaultTenantProfile(tenantId);
        setProfile(fallbackProfile);
        setLoadError(
          localProfile
            ? null
            : "Backend profile service is unavailable. Using a local profile on this machine."
        );
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [ready, tenantId]);

  const update = <K extends keyof TenantProfile>(key: K, value: TenantProfile[K]) => {
    if (!profile) return;
    setProfile({ ...profile, [key]: value });
  };

  const save = async () => {
    if (!profile) return;
    setSaving(true);
    setMessage(null);
    try {
      const saved = await updateTenantProfile(profile);
      setProfile(saved);
      saveLocalProfile(saved);
      setMessage({ text: "Configuration saved successfully.", ok: true });
    } catch {
      const localProfile = {
        ...profile,
        updated_at: new Date().toISOString(),
      };
      setProfile(localProfile);
      saveLocalProfile(localProfile);
      setMessage({
        text: "Backend unavailable. Configuration was saved locally on this machine.",
        ok: true,
      });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-[420px] items-center justify-center">
        <Loader2 className="mr-3 h-5 w-5 animate-spin text-slate-400" />
        <span className="text-sm text-slate-500">Loading tenant configuration...</span>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex min-h-[420px] items-center justify-center px-8">
        <div className="rounded-2xl border border-red-100 bg-white p-6 text-center shadow-sm">
          <p className="text-sm font-semibold text-red-600">
            Unable to load tenant configuration.
          </p>
          <button
            onClick={() => setTenantId(tenantId)}
            className="mt-4 inline-flex items-center gap-2 rounded-xl bg-[#1a2332] px-4 py-2 text-sm font-bold text-white transition hover:bg-[#243044]"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  const cogsTotal = profile.cogs.steel_pct + profile.cogs.petroleum_pct +
    profile.cogs.electronics_pct + profile.cogs.freight_pct + profile.cogs.other_pct;

  return (
    <div className="px-8 py-7 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Settings className="h-4 w-4 text-blue-600" />
            <span className="text-[10px] font-bold tracking-widest text-blue-600 uppercase">System Configuration</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900">Tenant Profile</h2>
          <p className="text-sm text-gray-500 mt-1">Full financial and operational profile powering the Day 3 sensitivity engine and alert system.</p>
          {loadError && (
            <p className="mt-3 max-w-2xl rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700">
              {loadError}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={() => void save()}
            className="flex items-center gap-2 rounded-xl bg-[#1a2332] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#243044] transition"
          >
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
            Save All Changes
          </button>
          {message && (
            <span className={`text-sm font-medium ${message.ok ? "text-emerald-600" : "text-red-600"}`}>
              {message.text}
            </span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100/80 p-1 rounded-2xl w-fit">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
              activeTab === id ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-700"
            }`}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        ))}
      </div>

      {/* ── Identity Tab ─────────────────────────────────────────────────── */}
      {activeTab === "identity" && (
        <div className="grid gap-5 xl:grid-cols-2">
          <SectionCard title="Tenant Context" description="Core workspace identity used across all MacroPulse APIs.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Tenant ID">
                <div className="flex gap-2">
                  <TextInput value={draftTenantId} onChange={setDraftTenantId} placeholder="demo-in-001" />
                </div>
              </Field>
              <div className="flex items-end">
                <button
                  onClick={() => setTenantId(draftTenantId)}
                  className="w-full rounded-xl bg-[#1a2332] px-4 py-2.5 text-sm font-bold text-white hover:bg-[#243044] transition flex items-center justify-center gap-2"
                >
                  Load Tenant <ChevronRight className="h-4 w-4" />
                </button>
              </div>
              <Field label="Company Name">
                <TextInput value={profile.company_name} onChange={(v) => update("company_name", v)} />
              </Field>
              <Field label="Primary Region">
                <SelectInput
                  value={profile.primary_region}
                  options={[
                    { value: "IN", label: "India (IN)" },
                    { value: "UAE", label: "UAE" },
                    { value: "SA", label: "Saudi Arabia (SA)" },
                  ]}
                  onChange={(v) => update("primary_region", v as TenantProfile["primary_region"])}
                />
              </Field>
              <Field label="Primary Currency">
                <SelectInput
                  value={profile.primary_currency}
                  options={[
                    { value: "INR", label: "Indian Rupee (INR)" },
                    { value: "AED", label: "UAE Dirham (AED)" },
                    { value: "SAR", label: "Saudi Riyal (SAR)" },
                  ]}
                  onChange={(v) => update("primary_currency", v as TenantProfile["primary_currency"])}
                />
              </Field>
            </div>
          </SectionCard>

          <div className="bg-[#1a2332] rounded-2xl p-6 text-white">
            <h3 className="text-base font-bold mb-3">Active Profile Summary</h3>
            <div className="space-y-3 text-sm">
              {[
                { label: "Tenant ID", value: profile.tenant_id },
                { label: "Company", value: profile.company_name },
                { label: "Region", value: profile.primary_region },
                { label: "Currency", value: profile.primary_currency },
                { label: "Total Loan Book", value: `₹${profile.debt.total_loan_amount_cr.toFixed(0)} Cr` },
                { label: "Net USD Exposure", value: `$${profile.fx.net_usd_exposure_m.toFixed(0)}M` },
                { label: "Annual COGS", value: `₹${profile.cogs.total_cogs_cr.toFixed(0)} Cr` },
              ].map((item) => (
                <div key={item.label} className="flex justify-between border-b border-white/10 pb-2.5">
                  <span className="text-white/60">{item.label}</span>
                  <span className="font-semibold">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Financial Profile Tab ─────────────────────────────────────────── */}
      {activeTab === "financial" && (
        <div className="grid gap-5 xl:grid-cols-2">
          {/* Debt */}
          <SectionCard title="Debt Profile" description="Drives repo rate sensitivity and borrowing cost impact.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Total Loan Book (₹ Cr)">
                <NumInput value={profile.debt.total_loan_amount_cr} onChange={(v) => update("debt", { ...profile.debt, total_loan_amount_cr: v })} />
              </Field>
              <Field label="Rate Type">
                <SelectInput
                  value={profile.debt.rate_type}
                  options={[
                    { value: "MCLR", label: "MCLR" },
                    { value: "Fixed", label: "Fixed" },
                    { value: "Floating", label: "Floating" },
                  ]}
                  onChange={(v) => update("debt", { ...profile.debt, rate_type: v as "MCLR" | "Fixed" | "Floating" })}
                />
              </Field>
              <Field label="Floating Proportion (%)" hint="% of total debt at floating rate">
                <NumInput value={profile.debt.floating_proportion_pct} onChange={(v) => update("debt", { ...profile.debt, floating_proportion_pct: v })} />
              </Field>
              <Field label="Effective Rate (%)">
                <NumInput value={profile.debt.current_effective_rate_pct} onChange={(v) => update("debt", { ...profile.debt, current_effective_rate_pct: v })} />
              </Field>
              <Field label="Short-Term Debt (₹ Cr)">
                <NumInput value={profile.debt.short_term_debt_cr} onChange={(v) => update("debt", { ...profile.debt, short_term_debt_cr: v })} />
              </Field>
              <Field label="Long-Term Debt (₹ Cr)">
                <NumInput value={profile.debt.long_term_debt_cr} onChange={(v) => update("debt", { ...profile.debt, long_term_debt_cr: v })} />
              </Field>
            </div>
          </SectionCard>

          {/* FX */}
          <SectionCard title="FX Exposure" description="USD/INR, AED/INR, and SAR/INR net open positions.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Net USD Exposure ($M)">
                <NumInput value={profile.fx.net_usd_exposure_m} onChange={(v) => update("fx", { ...profile.fx, net_usd_exposure_m: v })} />
              </Field>
              <Field label="Net AED Exposure ($M)">
                <NumInput value={profile.fx.net_aed_exposure_m} onChange={(v) => update("fx", { ...profile.fx, net_aed_exposure_m: v })} />
              </Field>
              <Field label="Net SAR Exposure ($M)">
                <NumInput value={profile.fx.net_sar_exposure_m} onChange={(v) => update("fx", { ...profile.fx, net_sar_exposure_m: v })} />
              </Field>
              <Field label="Hedge Ratio (%)">
                <NumInput value={profile.fx.hedge_ratio_pct} onChange={(v) => update("fx", { ...profile.fx, hedge_ratio_pct: v })} />
              </Field>
              <Field label="Hedge Instrument">
                <SelectInput
                  value={profile.fx.hedge_instrument}
                  options={[
                    { value: "Forward", label: "Forward Contracts" },
                    { value: "Options", label: "Currency Options" },
                    { value: "Natural", label: "Natural Hedge" },
                    { value: "None", label: "Unhedged" },
                  ]}
                  onChange={(v) => update("fx", { ...profile.fx, hedge_instrument: v as TenantProfile["fx"]["hedge_instrument"] })}
                />
              </Field>
            </div>
          </SectionCard>

          {/* COGS */}
          <SectionCard title="COGS Breakdown" description="Input cost composition drives crude oil and WPI sensitivity.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="Total Annual COGS (₹ Cr)">
                <NumInput value={profile.cogs.total_cogs_cr} onChange={(v) => update("cogs", { ...profile.cogs, total_cogs_cr: v })} />
              </Field>
              <div className="flex items-center justify-between col-span-2 pt-1">
                <span className="text-xs text-gray-500">Composition total:</span>
                <span className={`text-xs font-bold ${Math.abs(cogsTotal - 100) > 1 ? "text-red-600" : "text-emerald-600"}`}>
                  {cogsTotal.toFixed(0)}% {Math.abs(cogsTotal - 100) > 1 ? "(should equal 100%)" : "✓"}
                </span>
              </div>
              {[
                { key: "steel_pct", label: "Steel (%)", color: "#6366f1" },
                { key: "petroleum_pct", label: "Petroleum (%)", color: "#f97316" },
                { key: "electronics_pct", label: "Electronics (%)", color: "#3b82f6" },
                { key: "freight_pct", label: "Freight (%)", color: "#10b981" },
                { key: "other_pct", label: "Other (%)", color: "#94a3b8" },
              ].map((item) => (
                <div key={item.key}>
                  <Field label={item.label}>
                    <NumInput
                      value={profile.cogs[item.key as keyof typeof profile.cogs] as number}
                      onChange={(v) => update("cogs", { ...profile.cogs, [item.key]: v })}
                    />
                  </Field>
                  <PercentBar pct={profile.cogs[item.key as keyof typeof profile.cogs] as number} color={item.color} />
                </div>
              ))}
            </div>
          </SectionCard>

          {/* Portfolio */}
          <SectionCard title="Investment Portfolio" description="G-Sec holdings drive yield sensitivity and MTM impact.">
            <div className="grid gap-4 sm:grid-cols-2">
              <Field label="G-Sec Holdings (₹ Cr)">
                <NumInput
                  value={profile.portfolio.gsec_holdings_cr}
                  onChange={(v) => update("portfolio", { ...profile.portfolio, gsec_holdings_cr: v })}
                />
              </Field>
              <Field label="Modified Duration (years)" hint="Higher duration = more interest rate sensitivity">
                <NumInput
                  value={profile.portfolio.modified_duration}
                  onChange={(v) => update("portfolio", { ...profile.portfolio, modified_duration: v })}
                />
              </Field>
            </div>
          </SectionCard>
        </div>
      )}

      {/* ── Logistics Tab ─────────────────────────────────────────────────── */}
      {activeTab === "logistics" && (
        <div className="grid gap-5 xl:grid-cols-2">
          <SectionCard title="Logistics & Supply Chain" description="Primary trade routes and inventory parameters.">
            <div className="grid gap-4">
              <Field label="Primary Routes" hint="Comma-separated trade routes (e.g. Mumbai-Dubai, Chennai-Jebel Ali)">
                <TextInput
                  value={profile.logistics.primary_routes.join(", ")}
                  onChange={(v) => update("logistics", { ...profile.logistics, primary_routes: v.split(",").map((s) => s.trim()).filter(Boolean) })}
                  placeholder="Mumbai-Dubai, Chennai-Jebel Ali"
                />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Monthly Shipment Value (₹ Cr)">
                  <NumInput
                    value={profile.logistics.monthly_shipment_value_cr}
                    onChange={(v) => update("logistics", { ...profile.logistics, monthly_shipment_value_cr: v })}
                  />
                </Field>
                <Field label="Inventory Buffer (days)" hint="Buffer stock before supply disruption">
                  <NumInput
                    value={profile.logistics.inventory_buffer_days}
                    onChange={(v) => update("logistics", { ...profile.logistics, inventory_buffer_days: v })}
                  />
                </Field>
              </div>
            </div>
          </SectionCard>

          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
            <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider mb-4">Route Summary</h3>
            <div className="space-y-3">
              {profile.logistics.primary_routes.map((route, i) => (
                <div key={i} className="flex items-center gap-3 rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3">
                  <Truck className="h-4 w-4 text-blue-500 shrink-0" />
                  <span className="text-sm font-medium text-gray-700">{route}</span>
                  <span className="ml-auto text-xs text-gray-400">Route {i + 1}</span>
                </div>
              ))}
              {profile.logistics.primary_routes.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">No routes configured</p>
              )}
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border border-blue-100 bg-blue-50/50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-widest text-blue-600">Monthly Shipment</p>
                <p className="text-xl font-black text-gray-900 mt-1">₹{profile.logistics.monthly_shipment_value_cr} Cr</p>
              </div>
              <div className="rounded-xl border border-emerald-100 bg-emerald-50/50 p-4">
                <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-600">Buffer Stock</p>
                <p className="text-xl font-black text-gray-900 mt-1">{profile.logistics.inventory_buffer_days} days</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Alerts & Notifications Tab ────────────────────────────────────── */}
      {activeTab === "alerts" && (
        <div className="grid gap-5 xl:grid-cols-2">
          <SectionCard title="Alert Delivery Channels" description="Configure where P1/P2/P3 alerts and HITL notifications are dispatched.">
            <div className="grid gap-4">
              <Field label="Alert Email">
                <TextInput
                  type="email"
                  value={profile.notification_config.email ?? ""}
                  onChange={(v) => update("notification_config", { ...profile.notification_config, email: v })}
                  placeholder="cfo@company.com"
                />
              </Field>
              <Field label="Microsoft Teams Webhook" hint="Paste your Teams incoming webhook URL">
                <TextInput
                  value={profile.notification_config.teams_webhook ?? ""}
                  onChange={(v) => update("notification_config", { ...profile.notification_config, teams_webhook: v })}
                  placeholder="https://outlook.office.com/webhook/..."
                />
              </Field>
              <Field label="Slack Webhook" hint="Paste your Slack incoming webhook URL">
                <TextInput
                  value={profile.notification_config.slack_webhook ?? ""}
                  onChange={(v) => update("notification_config", { ...profile.notification_config, slack_webhook: v })}
                  placeholder="https://hooks.slack.com/services/..."
                />
              </Field>
            </div>
          </SectionCard>

          <SectionCard title="Active Channels" description="Toggle which channels receive macro alerts.">
            <div className="space-y-3">
              {(["email", "teams", "slack"] as const).map((channel) => {
                const enabled = profile.notification_config.channels.includes(channel);
                const label = channel === "email" ? "Email" : channel === "teams" ? "Microsoft Teams" : "Slack";
                const icon = channel === "email" ? "📧" : channel === "teams" ? "💼" : "💬";
                const hasValue = channel === "email"
                  ? !!profile.notification_config.email
                  : channel === "teams"
                  ? !!profile.notification_config.teams_webhook
                  : !!profile.notification_config.slack_webhook;

                return (
                  <label
                    key={channel}
                    className={`flex items-center justify-between rounded-xl border p-4 cursor-pointer transition ${
                      enabled ? "border-blue-200 bg-blue-50/50" : "border-gray-100 bg-gray-50/40"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{icon}</span>
                      <div>
                        <p className="text-sm font-semibold text-gray-800">{label}</p>
                        <p className="text-xs text-gray-500">{hasValue ? "Configured" : "Not configured"}</p>
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={enabled}
                      onChange={(e) => {
                        const channels = e.target.checked
                          ? [...profile.notification_config.channels, channel]
                          : profile.notification_config.channels.filter((c) => c !== channel);
                        update("notification_config", { ...profile.notification_config, channels: channels as typeof profile.notification_config.channels });
                      }}
                      className="h-5 w-5 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
                    />
                  </label>
                );
              })}
            </div>

            <div className="mt-4 rounded-xl border border-slate-100 bg-slate-50 p-4">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-500 mb-3">Alert Routing Rules</p>
              <div className="space-y-2 text-xs text-slate-600">
                {[
                  { tier: "P1", label: "Immediate dispatch", color: "bg-red-500" },
                  { tier: "P2", label: "Confidence ≥ 85% → auto, else HITL queue", color: "bg-amber-500" },
                  { tier: "P3", label: "Batched daily digest", color: "bg-slate-400" },
                ].map((r) => (
                  <div key={r.tier} className="flex items-center gap-2">
                    <span className={`inline-flex items-center justify-center w-6 h-5 rounded text-[10px] font-bold text-white ${r.color}`}>{r.tier}</span>
                    <span>{r.label}</span>
                  </div>
                ))}
              </div>
            </div>
          </SectionCard>
        </div>
      )}

      {/* ── Pipeline & Events Tab ─────────────────────────────────────── */}
      {activeTab === "pipeline" && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500">Live cost routing status and pub/sub event log from the Day 5 backend.</p>
            <button
              onClick={() => void loadPipelineData()}
              className="flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600 hover:bg-gray-50 transition"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${pipelineLoading ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>

          {pipelineLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-slate-400 mr-2" />
              <span className="text-sm text-slate-500">Loading pipeline data...</span>
            </div>
          )}

          {/* Cost Routing */}
          {!pipelineLoading && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider mb-1">LiteLLM Cost Routing</h3>
              <p className="text-xs text-gray-500 mb-4">GPT-4o → GPT-3.5-turbo → local model fallback chain with budget cap</p>
              {costStatus ? (
                <>
                  <div className="grid gap-3 sm:grid-cols-3 mb-5">
                    <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Total Requests</p>
                      <p className="text-2xl font-black text-gray-900 mt-1">{costStatus.total_requests}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Total Cost</p>
                      <p className="text-2xl font-black text-gray-900 mt-1">${costStatus.total_cost_usd.toFixed(4)}</p>
                    </div>
                    <div className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
                      <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Budget Status</p>
                      <p className={`text-sm font-bold mt-1 ${
                        (costStatus.budget as Record<string,string>)?.status === "exceeded" ? "text-red-600"
                        : (costStatus.budget as Record<string,string>)?.status === "warning" ? "text-amber-600"
                        : "text-emerald-600"
                      }`}>{String((costStatus.budget as Record<string,string>)?.status ?? "ok").toUpperCase()}</p>
                    </div>
                  </div>
                  {Object.entries(costStatus.by_model).length > 0 && (
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr className="border-b border-gray-100">
                            {["Model", "Requests", "Input Tokens", "Output Tokens", "Cost (USD)"].map((h) => (
                              <th key={h} className="text-left py-2 pr-4 text-[10px] font-bold uppercase tracking-widest text-gray-400">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {Object.entries(costStatus.by_model).map(([model, rec]) => (
                            <tr key={model} className="border-b border-gray-50">
                              <td className="py-2.5 pr-4 font-semibold text-gray-800">{model}</td>
                              <td className="py-2.5 pr-4 text-gray-600">{rec.requests}</td>
                              <td className="py-2.5 pr-4 text-gray-600">{rec.total_input_tokens.toLocaleString()}</td>
                              <td className="py-2.5 pr-4 text-gray-600">{rec.total_output_tokens.toLocaleString()}</td>
                              <td className="py-2.5 pr-4 font-semibold text-gray-800">${rec.total_cost_usd.toFixed(4)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </>
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400">
                  Cost routing data unavailable — backend connection required.
                </div>
              )}
            </div>
          )}

          {/* Event Log */}
          {!pipelineLoading && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider mb-1">Redis Pub/Sub Event Log</h3>
              <p className="text-xs text-gray-500 mb-4">
                Published to: <span className="font-semibold">macro.currency_signal</span> → GeoRisk ·{" "}
                <span className="font-semibold">macro.slowdown_risk</span> → ChurnGuard ·{" "}
                <span className="font-semibold">macro.commodity_inflation</span> → SLAMonitor
              </p>
              {eventLog.length > 0 ? (
                <div className="space-y-2 max-h-72 overflow-y-auto">
                  {eventLog.slice(-20).reverse().map((evt) => (
                    <div key={evt.event_id} className="flex items-start gap-3 rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3">
                      <span className={`mt-0.5 shrink-0 h-2 w-2 rounded-full ${
                        evt.channel.includes("currency") ? "bg-blue-500"
                        : evt.channel.includes("slowdown") ? "bg-amber-500"
                        : "bg-emerald-500"
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-semibold text-gray-800 truncate">{evt.event_type}</p>
                          <span className="text-[10px] text-gray-400 shrink-0">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-[11px] text-gray-500 mt-0.5 truncate">{evt.channel} · tenant: {evt.tenant_id}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="rounded-xl border border-dashed border-gray-200 p-6 text-center text-sm text-gray-400">
                  No events published yet — trigger the CFO Brief pipeline or run an agent query.
                </div>
              )}
            </div>
          )}

          {/* Channel schemas */}
          {!pipelineLoading && eventSchemas && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider mb-4">Channel Schemas</h3>
              <div className="grid gap-4 sm:grid-cols-3">
                {Object.entries((eventSchemas.channels ?? {}) as Record<string, Record<string,unknown>>).map(([channel, info]) => (
                  <div key={channel} className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-blue-600 mb-1">{channel}</p>
                    <p className="text-xs font-semibold text-gray-800">{String(info.description ?? "")}</p>
                    <p className="text-xs text-gray-500 mt-1">Consumer: <span className="font-semibold">{String(info.consumer ?? "--")}</span></p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Save bar */}
      <div className="sticky bottom-0 bg-white/90 backdrop-blur-sm border-t border-gray-100 -mx-8 px-8 py-4 flex items-center gap-4">
        <button
          onClick={() => void save()}
          className="flex items-center gap-2 rounded-xl bg-[#1a2332] px-6 py-2.5 text-sm font-bold text-white hover:bg-[#243044] transition"
        >
          {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
          {saving ? "Saving..." : "Save Configuration"}
        </button>
        {message && (
          <span className={`text-sm font-medium ${message.ok ? "text-emerald-600" : "text-red-600"}`}>
            {message.text}
          </span>
        )}
        <span className="ml-auto text-xs text-gray-400">
          Last updated: {profile.updated_at ? new Date(profile.updated_at).toLocaleString() : "—"}
        </span>
      </div>
    </div>
  );
}
