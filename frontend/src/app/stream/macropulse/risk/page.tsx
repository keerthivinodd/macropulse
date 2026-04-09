"use client";

import RiskLivePage from "./RiskLivePage";

import { AlertTriangle } from "lucide-react";

const risks = [
  { name: "Geopolitical Tension (MENA)", level: "HIGH", score: 82, color: "text-red-600 bg-red-50", bar: "bg-red-500" },
  { name: "Currency Devaluation Risk", level: "MEDIUM", score: 54, color: "text-amber-600 bg-amber-50", bar: "bg-amber-400" },
  { name: "Sovereign Debt Exposure", level: "MEDIUM", score: 48, color: "text-amber-600 bg-amber-50", bar: "bg-amber-400" },
  { name: "Regulatory Compliance Risk", level: "LOW", score: 22, color: "text-emerald-600 bg-emerald-50", bar: "bg-emerald-400" },
];

// Legacy placeholder kept temporarily while the live page is wired for the demo.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LegacyStrategicRiskPage() {
  return (
    <div className="px-8 py-7 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-black text-gray-900">Strategic Risk</h2>
          <p className="text-sm text-gray-500 mt-1">Macro risk exposure across geopolitical, currency, and regulatory dimensions</p>
        </div>
        <span className="flex items-center gap-1.5 text-xs font-semibold text-red-600 bg-red-50 px-3 py-1.5 rounded-full border border-red-200">
          <AlertTriangle className="w-3.5 h-3.5" /> 2 High Risk Signals
        </span>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {risks.map(r => (
          <div key={r.name} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-gray-800">{r.name}</h3>
              <span className={`text-[10px] font-bold tracking-widest px-2.5 py-1 rounded-full uppercase ${r.color}`}>{r.level}</span>
            </div>
            <div className="flex items-end gap-2 mb-3">
              <span className="text-4xl font-black text-gray-900">{r.score}</span>
              <span className="text-sm text-gray-400 mb-1">/ 100</span>
            </div>
            <div className="w-full bg-gray-100 rounded-full h-2">
              <div className={`h-2 rounded-full ${r.bar}`} style={{ width: `${r.score}%` }} />
            </div>
          </div>
        ))}
      </div>

      <div className="bg-[#1a2332] rounded-2xl p-6 text-white">
        <h3 className="text-base font-bold mb-3">Risk Mitigation Recommendations</h3>
        <div className="space-y-2">
          {["Increase FX hedging coverage to 85% of forward exposure","Diversify supplier base away from MENA concentration","Review sovereign bond holdings quarterly"].map((r,i) => (
            <div key={i} className="flex items-start gap-3 text-sm text-slate-300">
              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5 shrink-0" />{r}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default RiskLivePage;
