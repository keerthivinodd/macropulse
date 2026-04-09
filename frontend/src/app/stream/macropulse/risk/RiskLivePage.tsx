"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, Loader2, ShieldAlert, XCircle } from "lucide-react";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import {
  approveHitl,
  classifyAlert,
  ensureTenantProfile,
  getGuardrailViolations,
  getHitlPending,
  getMacroPulseDashboard,
  rejectHitl,
} from "@/services/macropulse";
import type { GuardrailViolation, HITLPendingAlert, MacroPulseDashboard } from "@/types/macropulse";

export default function RiskLivePage() {
  const { tenantId, ready } = useMacroPulseTenant();
  const [dashboard, setDashboard] = useState<MacroPulseDashboard | null>(null);
  const [pending, setPending] = useState<HITLPendingAlert[]>([]);
  const [violations, setViolations] = useState<GuardrailViolation[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);

  const load = async () => {
    if (!ready) return;
    setLoading(true);
    try {
      await ensureTenantProfile(tenantId);
      const [dash, hitl, guards] = await Promise.all([
        getMacroPulseDashboard(tenantId),
        getHitlPending(tenantId),
        getGuardrailViolations(tenantId),
      ]);
      setDashboard(dash);
      setPending(hitl);
      setViolations(guards);
    } catch {
      // backend unavailable — page renders empty state
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [ready, tenantId]);

  const triggerAlert = async (kind: "p1" | "hitl" | "guardrail") => {
    setBusy(kind);
    try {
      if (kind === "p1") {
        await classifyAlert(tenantId, {
          macro_variable: "repo_rate",
          confidence_score: 0.92,
          title: "Repo rate shock detected for treasury watchlist",
          body: "MacroPulse detected a material policy-rate move affecting debt servicing sensitivity.",
          source_citation: "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
          financial_impact_cr: 0.16,
        });
      } else if (kind === "hitl") {
        await classifyAlert(tenantId, {
          macro_variable: "fx_usd_inr",
          confidence_score: 0.78,
          title: "USD/INR move requires analyst review",
          body: "Confidence fell into the HITL band after abnormal FX move detection.",
          source_citation: "RBI Bulletin ? 2026-04-01T09:30:00+05:30",
          change_pct_24h: 2.4,
        });
      } else {
        try {
          await classifyAlert(tenantId, {
            macro_variable: "repo_rate",
            confidence_score: 0.95,
            title: "Unsourced policy alert",
            body: "This should be blocked by the source guardrail.",
            source_citation: "",
          });
        } catch {
          // Expected guardrail path.
        }
      }
      await load();
    } finally {
      setBusy(null);
    }
  };

  const handleApprove = async (alertId: string) => {
    setBusy(alertId);
    try {
      await approveHitl(alertId, "Keerthi", "Approved from manager demo queue");
      await load();
    } finally {
      setBusy(null);
    }
  };

  const handleReject = async (alertId: string) => {
    setBusy(alertId);
    try {
      await rejectHitl(alertId, "Keerthi", "Rejected during demo review", "Low business relevance");
      await load();
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="px-8 py-7 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-black text-gray-900">Strategic Risk & Alert Operations</h2>
          <p className="text-sm text-gray-500 mt-1">Day 4 alerting, HITL review, and guardrail audit trail wired to the live backend.</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600 bg-red-50 px-3 py-1.5 rounded-full border border-red-200">
          <AlertTriangle className="w-3.5 h-3.5" /> {dashboard?.live_alerts.length ?? 0} live alerts
        </span>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        {[
          {
            key: "p1",
            title: "Create P1 Alert",
            text: "Generates an immediate repo-rate alert that lands in the live dashboard queue.",
          },
          {
            key: "hitl",
            title: "Create HITL Alert",
            text: "Generates a medium-confidence FX alert that routes into the analyst review queue.",
          },
          {
            key: "guardrail",
            title: "Trigger Guardrail",
            text: "Submits an unsourced alert so the violation audit trail can be shown during the demo.",
          },
        ].map((card) => (
          <button
            key={card.key}
            onClick={() => void triggerAlert(card.key as "p1" | "hitl" | "guardrail")}
            className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100 text-left hover:border-blue-200 hover:bg-blue-50/30 transition"
          >
            <p className="text-xs font-bold tracking-widest text-blue-600 uppercase">{card.title}</p>
            <p className="mt-3 text-sm leading-6 text-gray-600">{card.text}</p>
            <p className="mt-4 text-sm font-semibold text-gray-900">
              {busy === card.key ? "Working..." : "Run demo action"}
            </p>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex min-h-[280px] items-center justify-center rounded-2xl border border-gray-100 bg-white shadow-sm">
          <Loader2 className="mr-3 h-5 w-5 animate-spin text-slate-400" />
          <span className="text-sm text-slate-500">Loading alert center...</span>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-900">Human-in-the-loop queue</h3>
            <p className="text-sm text-gray-500 mt-1 mb-5">Approve or reject low-confidence alerts from the actual Day 4 queue.</p>
            <div className="space-y-4">
              {pending.length ? (
                pending.map((item) => (
                  <div key={item.alert_id} className="rounded-2xl border border-gray-100 p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-sm font-semibold text-gray-900">{item.title}</p>
                        <p className="mt-1 text-sm text-gray-500">{item.body}</p>
                        <p className="mt-2 text-[11px] uppercase tracking-[0.18em] text-gray-400">
                          Confidence {Math.round(item.confidence_score * 100)}% • {item.reason}
                        </p>
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => void handleApprove(item.alert_id)}
                          className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-bold text-white"
                        >
                          <CheckCircle2 className="h-3.5 w-3.5" />
                          {busy === item.alert_id ? "..." : "Approve"}
                        </button>
                        <button
                          onClick={() => void handleReject(item.alert_id)}
                          className="inline-flex items-center gap-2 rounded-lg bg-red-600 px-3 py-2 text-xs font-bold text-white"
                        >
                          <XCircle className="h-3.5 w-3.5" />
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-dashed border-gray-200 bg-gray-50/70 p-6 text-sm text-gray-500">
                  No HITL items yet. Use “Create HITL Alert” above to populate the review queue.
                </div>
              )}
            </div>
          </div>

          <div className="space-y-5">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
              <h3 className="text-lg font-bold text-gray-900">Live dispatch queue</h3>
              <div className="mt-4 space-y-3">
                {(dashboard?.live_alerts ?? []).slice(0, 4).map((alert) => (
                  <div key={alert.id} className="rounded-xl border border-gray-100 bg-gray-50/70 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-semibold text-gray-900">{alert.title}</span>
                      <span className={`text-[10px] font-bold tracking-widest uppercase ${alert.tier === "P1" ? "text-red-600" : "text-amber-600"}`}>
                        {alert.tier}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-gray-500">{alert.macro_variable.replaceAll("_", " ")}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-[#1a2332] rounded-2xl p-6 text-white">
              <div className="flex items-center gap-2">
                <ShieldAlert className="h-4 w-4 text-amber-300" />
                <h3 className="text-lg font-bold">Guardrail violations</h3>
              </div>
              <div className="mt-4 space-y-3">
                {violations.length ? (
                  violations.slice(0, 4).map((violation) => (
                    <div key={violation.id} className="rounded-xl border border-white/10 bg-white/5 p-4">
                      <p className="text-sm font-semibold text-white">{violation.reason}</p>
                      <p className="mt-1 text-xs text-slate-400">{violation.alert_title ?? "Untitled alert"}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-400">No guardrail violations logged yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
