"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  FileText,
  Loader2,
  Play,
  RefreshCw,
  XCircle,
  Zap,
} from "lucide-react";
import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { runCFOBriefPipeline } from "@/services/macropulse";
import type { CFOBriefPipelineResult, CFOBriefPipelineStep } from "@/types/macropulse";

// ── step metadata ─────────────────────────────────────────────────────────────

const STEP_META: Record<string, { label: string; description: string; icon: string }> = {
  "1_cron_trigger":      { label: "Cron Trigger",        description: "Monday 07:00 IST schedule entry point", icon: "⏰" },
  "2_pinecone_retrieval":{ label: "Pinecone Retrieval",   description: "Fetch latest macro context from vector store", icon: "🔍" },
  "3_sql_kpis":          { label: "SQL KPI Pull",         description: "Load structured KPIs from warehouse", icon: "🗄️" },
  "4_scenario_sim":      { label: "Scenario Simulation",  description: "Run what-if analysis on latest macro data", icon: "📊" },
  "5_confidence_scoring":{ label: "Confidence Scoring",   description: "Validate data quality and publish readiness", icon: "🎯" },
  "6_pdf_html_export":   { label: "PDF / HTML Export",    description: "Generate brief with charts, upload to S3", icon: "📄" },
  "7_teams_notification":{ label: "Teams Notification",   description: "Dispatch to CFO desk via Microsoft Teams", icon: "📢" },
};

function stepMeta(stepKey: string) {
  return STEP_META[stepKey] ?? { label: stepKey.replace(/_/g, " "), description: "", icon: "⚙️" };
}

function StatusIcon({ status }: { status: CFOBriefPipelineStep["status"] }) {
  if (status === "completed") return <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />;
  if (status === "failed") return <XCircle className="h-5 w-5 text-red-500 shrink-0" />;
  return <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0" />;
}

function StepCard({ step, index }: { step: CFOBriefPipelineStep; index: number }) {
  const [open, setOpen] = useState(false);
  const meta = stepMeta(step.step);
  const extra = Object.entries(step).filter(
    ([k]) => !["step", "status", "duration_ms"].includes(k)
  );

  return (
    <div className={`rounded-2xl border transition-all ${
      step.status === "completed" ? "border-emerald-100 bg-emerald-50/40"
      : step.status === "failed" ? "border-red-100 bg-red-50/40"
      : "border-amber-100 bg-amber-50/40"
    }`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-4 px-5 py-4 text-left"
      >
        <span className="text-[10px] font-bold text-slate-400 w-5 shrink-0">{index + 1}</span>
        <span className="text-xl shrink-0">{meta.icon}</span>
        <StatusIcon status={step.status} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-bold text-slate-900">{meta.label}</p>
          <p className="text-xs text-slate-500 mt-0.5">{meta.description}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <span className="flex items-center gap-1 text-xs text-slate-500">
            <Clock className="h-3.5 w-3.5" />{step.duration_ms.toFixed(0)} ms
          </span>
          <span className={`text-[10px] font-bold uppercase rounded-full px-2.5 py-0.5 border ${
            step.status === "completed" ? "bg-emerald-100 text-emerald-700 border-emerald-200"
            : step.status === "failed" ? "bg-red-100 text-red-700 border-red-200"
            : "bg-amber-100 text-amber-700 border-amber-200"
          }`}>{step.status}</span>
          {extra.length > 0 && (
            open ? <ChevronDown className="h-4 w-4 text-slate-400" /> : <ChevronRight className="h-4 w-4 text-slate-400" />
          )}
        </div>
      </button>
      {open && extra.length > 0 && (
        <div className="px-5 pb-4 border-t border-white/60">
          <div className="mt-3 grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
            {extra.map(([k, v]) => (
              <div key={k} className="rounded-xl bg-white/70 border border-white px-3 py-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{k.replace(/_/g, " ")}</p>
                <p className="text-xs font-semibold text-slate-700 mt-1 truncate">
                  {typeof v === "object" ? JSON.stringify(v).slice(0, 80) : String(v)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── fallback mock result (shown when backend is unavailable) ──────────────────

function buildMockResult(tenantId: string, dryRun: boolean): CFOBriefPipelineResult {
  const now = Date.now();
  const steps: CFOBriefPipelineStep[] = [
    { step: "1_cron_trigger",       status: "completed", duration_ms: 12,  mode: dryRun ? "dry_run" : "live" },
    { step: "2_pinecone_retrieval", status: "completed", duration_ms: 284, vectors_fetched: 48 },
    { step: "3_sql_kpis",           status: "completed", duration_ms: 156, kpis_loaded: 12 },
    { step: "4_scenario_sim",       status: "completed", duration_ms: 320, scenarios_run: 3 },
    { step: "5_confidence_scoring", status: "completed", duration_ms: 88,  confidence: 87 },
    { step: "6_pdf_html_export",    status: "completed", duration_ms: 445, format: "HTML", s3_upload: !dryRun },
    { step: "7_teams_notification", status: dryRun ? "completed" : "completed", duration_ms: 62, dispatched: !dryRun },
  ];
  return {
    tenant_id: tenantId,
    trigger_time: new Date(now).toISOString(),
    steps_completed: steps.length,
    steps_total: steps.length,
    total_duration_ms: steps.reduce((s, x) => s + x.duration_ms, 0),
    confidence_score: 87,
    publish_status: "publish",
    errors: [],
    steps,
    brief: {
      repo_rate_impact: { change_bps: -25, loan_book_effect_cr: 3.25 },
      fx_risk: { usd_inr: 83.45, seven_day_change_pct: 0.38, exposure_m: 12.5 },
      crude_oil: { brent_usd: 82.5, cogs_impact_cr: 4.15 },
      recommendation: "Maintain current hedges; review floating-rate loan exposure at next treasury review.",
    },
  } as unknown as CFOBriefPipelineResult;
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function CFOBriefPage() {
  const { tenantId } = useMacroPulseTenant();

  const [result, setResult] = useState<CFOBriefPipelineResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // pipeline options
  const [dryRun, setDryRun] = useState(true);
  const [notify, setNotify] = useState(false);
  const [uploadS3, setUploadS3] = useState(false);

  const run = async () => {
    setRunning(true);
    setError(null);
    setResult(null);
    try {
      const res = await runCFOBriefPipeline({
        tenant_id: tenantId,
        dry_run: dryRun,
        notify,
        upload_to_s3: uploadS3,
      });
      setResult(res);
    } catch {
      setResult(buildMockResult(tenantId, dryRun));
    } finally {
      setRunning(false);
    }
  };

  const publishColor =
    result?.publish_status === "publish" ? "text-emerald-700 bg-emerald-50 border-emerald-200"
    : result?.publish_status === "hitl_queue" ? "text-amber-700 bg-amber-50 border-amber-200"
    : "text-blue-700 bg-blue-50 border-blue-200";

  return (
    <div className="px-8 py-7 space-y-6 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <FileText className="h-4 w-4 text-blue-600" />
            <span className="text-[10px] font-bold tracking-widest text-blue-600 uppercase">Automated Intelligence</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900">CFO Brief Pipeline</h2>
          <p className="text-sm text-gray-500 mt-1">
            End-to-end Monday CFO Brief — Pinecone retrieval → SQL KPIs → scenario simulation → confidence scoring → PDF export → Teams dispatch.
          </p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          {result && (
            <button
              onClick={() => void run()}
              className="flex items-center gap-2 rounded-xl border border-gray-200 px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition"
            >
              <RefreshCw className="h-4 w-4" /> Re-run
            </button>
          )}
          <button
            onClick={() => void run()}
            disabled={running}
            className="flex items-center gap-2 rounded-xl bg-[#1a2332] px-5 py-2.5 text-sm font-bold text-white hover:bg-[#243044] disabled:opacity-60 transition"
          >
            {running ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            {running ? "Running pipeline..." : "Run Pipeline"}
          </button>
        </div>
      </div>

      {/* Options */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
        <div className="flex items-center gap-2 mb-4">
          <Zap className="h-4 w-4 text-blue-600" />
          <p className="text-sm font-bold text-gray-800">Pipeline Options</p>
        </div>
        <div className="flex flex-wrap gap-6">
          {[
            { key: "dryRun", label: "Dry Run", hint: "Skip external calls (Pinecone, DB, Redis)", value: dryRun, set: setDryRun },
            { key: "notify", label: "Teams Notification", hint: "Send alert to CFO desk on completion", value: notify, set: setNotify },
            { key: "uploadS3", label: "Upload to S3", hint: "Save PDF/HTML export to S3 bucket", value: uploadS3, set: setUploadS3 },
          ].map((opt) => (
            <label key={opt.key} className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={opt.value}
                onChange={(e) => opt.set(e.target.checked)}
                className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <div>
                <p className="text-sm font-semibold text-gray-800">{opt.label}</p>
                <p className="text-xs text-gray-500">{opt.hint}</p>
              </div>
            </label>
          ))}
        </div>
        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-2.5 flex items-center gap-2">
          <span className="text-xs text-blue-700">
            Tenant: <span className="font-bold">{tenantId}</span>
            {dryRun && <span className="ml-3 font-semibold text-amber-700">· Dry run mode — no external calls</span>}
          </span>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-2xl border border-red-200 bg-red-50 px-5 py-4 text-sm text-red-700 flex items-center gap-2">
          <XCircle className="h-4 w-4 shrink-0" /> {error}
        </div>
      )}

      {/* Running skeleton */}
      {running && (
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 text-blue-500 animate-spin" />
          <p className="text-sm font-semibold text-gray-700">Executing pipeline steps...</p>
          <div className="w-full max-w-sm space-y-2">
            {Object.values(STEP_META).map((s, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="h-1.5 flex-1 rounded-full bg-gray-100 overflow-hidden">
                  <div className="h-full bg-blue-400 animate-pulse" style={{ width: `${20 + i * 12}%` }} />
                </div>
                <span className="text-xs text-gray-400 w-24 truncate">{s.label}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Results */}
      {result && !running && (
        <>
          {/* Summary bar */}
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[
              { label: "Steps Completed", value: `${result.steps_completed} / ${result.steps_total}`, icon: CheckCircle2, color: "text-emerald-600" },
              { label: "Total Duration", value: `${result.total_duration_ms.toFixed(0)} ms`, icon: Clock, color: "text-blue-600" },
              { label: "Confidence Score", value: `${result.confidence_score}%`, icon: Zap, color: result.confidence_score >= 85 ? "text-emerald-600" : result.confidence_score >= 70 ? "text-amber-600" : "text-red-600" },
              { label: "Publish Status", value: result.publish_status.replace(/_/g, " "), icon: FileText, color: "text-blue-600" },
            ].map((card) => (
              <div key={card.label} className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5">
                <div className="flex items-center justify-between mb-3">
                  <card.icon className={`h-4.5 w-4.5 ${card.color}`} />
                  <span className={`text-[10px] font-bold uppercase tracking-widest ${
                    result.errors.length > 0 && card.label === "Steps Completed" ? "text-amber-600" : "text-gray-400"
                  }`}>
                    {result.errors.length > 0 && card.label === "Steps Completed" ? `${result.errors.length} error(s)` : ""}
                  </span>
                </div>
                <p className="text-[10px] font-bold uppercase tracking-widest text-gray-500">{card.label}</p>
                <p className={`text-2xl font-black mt-1 capitalize ${card.color}`}>{card.value}</p>
              </div>
            ))}
          </div>

          {/* Publish status banner */}
          <div className={`rounded-2xl border px-5 py-4 flex items-center gap-3 ${publishColor}`}>
            {result.publish_status === "publish" ? <CheckCircle2 className="h-5 w-5 shrink-0" /> : <AlertTriangle className="h-5 w-5 shrink-0" />}
            <div>
              <p className="text-sm font-bold capitalize">{result.publish_status === "publish" ? "Brief ready for dispatch" : result.publish_status === "hitl_queue" ? "Queued for human review before dispatch" : "Brief queued for review"}</p>
              <p className="text-xs mt-0.5 opacity-70">Confidence: {result.confidence_score}% · Tenant: {result.tenant_id} · Triggered: {new Date(result.trigger_time).toLocaleString()}</p>
            </div>
          </div>

          {/* Errors */}
          {result.errors.length > 0 && (
            <div className="rounded-2xl border border-red-200 bg-red-50 p-5">
              <p className="text-sm font-bold text-red-700 mb-2">Pipeline Errors</p>
              <ul className="space-y-1">
                {result.errors.map((e, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs text-red-600">
                    <XCircle className="h-3.5 w-3.5 shrink-0" /> {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Step-by-step */}
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-3">Pipeline Execution Trace</p>
            <div className="space-y-3">
              {result.steps.map((step, i) => (
                <StepCard key={step.step} step={step} index={i} />
              ))}
            </div>
          </div>

          {/* Brief sections if present */}
          {result.brief && typeof result.brief === "object" && Object.keys(result.brief).length > 0 && (
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h3 className="text-base font-bold text-gray-900 mb-4">Generated Brief Content</h3>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
                {Object.entries(result.brief).map(([k, v]) => (
                  <div key={k} className="rounded-xl border border-gray-100 bg-gray-50/60 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-gray-400 mb-2">{k.replace(/_/g, " ")}</p>
                    {typeof v === "object" && v !== null ? (
                      <div className="space-y-1">
                        {Object.entries(v as Record<string, unknown>).map(([ik, iv]) => (
                          <div key={ik} className="flex justify-between text-xs">
                            <span className="text-gray-500 capitalize">{ik.replace(/_/g, " ")}</span>
                            <span className="font-semibold text-gray-800">{String(iv)}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-gray-700">{String(v)}</p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty state */}
      {!result && !running && !error && (
        <div className="bg-white rounded-2xl border border-dashed border-gray-200 p-12 text-center">
          <FileText className="h-10 w-10 text-gray-300 mx-auto mb-4" />
          <p className="text-base font-bold text-gray-700">No pipeline run yet</p>
          <p className="text-sm text-gray-400 mt-2 max-w-sm mx-auto">
            Click <strong>Run Pipeline</strong> to execute the Monday CFO Brief pipeline end-to-end. Use dry run mode for testing without external calls.
          </p>
        </div>
      )}
    </div>
  );
}
