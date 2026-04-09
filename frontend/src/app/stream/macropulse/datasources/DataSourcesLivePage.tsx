"use client";

import { useEffect, useState } from "react";
import { Database, Loader2 } from "lucide-react";

import { useMacroPulseTenant } from "@/hooks/macropulse/useMacroPulseTenant";
import { ensureTenantProfile, getMacroPulseDashboard } from "@/services/macropulse";
import type { MacroPulseDashboard } from "@/types/macropulse";

function formatDateTime(value?: string | null) {
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

export default function DataSourcesLivePage() {
  const { tenantId, ready } = useMacroPulseTenant();
  const [dashboard, setDashboard] = useState<MacroPulseDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    const load = async () => {
      setLoading(true);
      try {
        await ensureTenantProfile(tenantId);
        setDashboard(await getMacroPulseDashboard(tenantId));
      } catch {
        // backend unavailable — table shows "Fallback" status
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [ready, tenantId]);

  const sources = [
    { name: "RBI Macro Rates", type: "Central Bank", status: dashboard?.data_freshness.rbi ? "Live" : "Fallback", cadence: "Official cadence", latest: formatDateTime(dashboard?.data_freshness.rbi) },
    { name: "FX Rates", type: "Market Data", status: dashboard?.data_freshness.fx_rates ? "Live" : "Fallback", cadence: "Every 5 min", latest: formatDateTime(dashboard?.data_freshness.fx_rates) },
    { name: "Commodity Warehouse", type: "Commodity", status: dashboard?.data_freshness.commodities ? "Live" : "Fallback", cadence: "Daily", latest: formatDateTime(dashboard?.data_freshness.commodities) },
    { name: "News Ingestion", type: "News", status: dashboard?.data_freshness.news ? "Live" : "Fallback", cadence: "Hourly", latest: formatDateTime(dashboard?.data_freshness.news) },
    { name: "SAMA / CBUAE / Regional Stats", type: "Regional Macro", status: "Configured", cadence: "Daily", latest: "Backend verified" },
  ];

  return (
    <div className="px-8 py-7 space-y-6">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#1a2332] flex items-center justify-center">
          <Database className="w-5 h-5 text-cyan-200" />
        </div>
        <div>
          <h2 className="text-3xl font-black text-gray-900">Regional Data Sources</h2>
          <p className="text-sm text-gray-500 mt-1">Freshness and connector status for the live MacroPulse backend feeds.</p>
        </div>
      </div>

      {loading ? (
        <div className="flex min-h-[260px] items-center justify-center rounded-2xl border border-gray-100 bg-white shadow-sm">
          <Loader2 className="mr-3 h-5 w-5 animate-spin text-slate-400" />
          <span className="text-sm text-slate-500">Loading data-source status...</span>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-100">
              <tr>
                {["Source", "Type", "Status", "Cadence", "Latest Update"].map((h) => (
                  <th key={h} className="px-6 py-3 text-left text-[10px] font-bold tracking-widest text-gray-500 uppercase">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {sources.map((s) => (
                <tr key={s.name} className="hover:bg-gray-50 transition">
                  <td className="px-6 py-4 text-sm font-semibold text-gray-900">{s.name}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{s.type}</td>
                  <td className="px-6 py-4">
                    <span className={`text-[10px] font-bold tracking-widest px-2.5 py-1 rounded-full uppercase ${
                      s.status === "Live"
                        ? "text-emerald-600 bg-emerald-50"
                        : s.status === "Configured"
                          ? "text-blue-600 bg-blue-50"
                          : "text-amber-600 bg-amber-50"
                    }`}>
                      {s.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{s.cadence}</td>
                  <td className="px-6 py-4 text-sm font-semibold text-gray-700">{s.latest}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
