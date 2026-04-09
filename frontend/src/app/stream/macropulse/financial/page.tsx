"use client";

import FinancialImpactLivePage from "./FinancialImpactLivePage";

import { Download, Play, Calendar } from "lucide-react";

const HEATMAP = [
  [1,2,1,0,0,1,2,3,2,1],
  [0,1,2,2,1,0,1,2,3,2],
  [1,0,1,3,2,1,0,1,2,3],
  [2,1,0,1,3,2,1,0,1,2],
];

function HeatCell({ v }: { v: number }) {
  const colors = ["bg-green-100","bg-green-200","bg-red-200","bg-red-400"];
  return <div className={`w-8 h-8 rounded ${colors[v]}`} />;
}

// Legacy placeholder kept temporarily while the live page is wired for the demo.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LegacyFinancialImpactPage() {
  return (
    <div className="px-8 py-7 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-[10px] font-bold tracking-widest text-blue-600 uppercase bg-blue-50 px-2.5 py-1 rounded-full">Market Sensitivity</span>
            <span className="text-[10px] text-gray-400 uppercase tracking-widest">Updated 4M Ago</span>
          </div>
          <h2 className="text-3xl font-black text-gray-900">Strategic Exposure Dashboard</h2>
          <p className="text-sm text-gray-500 mt-1">Real-time mapping of global macroeconomic shifts against corporate liquidity and operational margins.</p>
        </div>
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
            <Download className="w-4 h-4" /> Export Report
          </button>
          <button className="flex items-center gap-2 px-5 py-2.5 bg-[#1a2332] text-white rounded-lg text-sm font-bold hover:bg-[#243044] transition">
            <Play className="w-4 h-4" /> Run Simulation
          </button>
          <button className="flex items-center gap-2 px-4 py-2.5 border border-gray-200 rounded-lg text-sm font-semibold text-gray-700 hover:bg-gray-50 transition">
            <Calendar className="w-4 h-4" /> Q3 FY2024 Analysis
          </button>
        </div>
      </div>

      {/* Top metric cards */}
      <div className="grid grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 text-lg">🏛</div>
            <span className="text-[10px] font-bold tracking-widest text-red-600 bg-red-50 px-2.5 py-1 rounded-full uppercase">High Alert</span>
          </div>
          <p className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-2">Borrowing Cost Impact</p>
          <div className="flex items-end gap-2 mb-1">
            <span className="text-5xl font-black text-gray-900">5.42%</span>
            <span className="text-sm font-bold text-red-500 mb-2">+28bps MoM</span>
          </div>
          <div className="flex items-end gap-1 h-12 mt-3 mb-3">
            {[30,35,28,40,38,42,45,100].map((h,i) => (
              <div key={i} className="flex-1 rounded-t" style={{ height: `${h}%`, background: i === 7 ? "#1a2332" : "#bfdbfe" }} />
            ))}
          </div>
          <p className="text-xs text-gray-500 leading-5">Recent central bank hawkishness has increased interest expense forecasts by <span className="font-bold text-gray-800">$1.2M</span> for the next fiscal year. Mitigation via debt restructuring is recommended.</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 text-lg">💱</div>
            <span className="text-[10px] font-bold tracking-widest text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full uppercase">Hedged</span>
          </div>
          <p className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-2">Currency Risk Exposure</p>
          <div className="flex items-end gap-2 mb-1">
            <span className="text-5xl font-black text-gray-900">€0.92</span>
            <span className="text-sm font-bold text-emerald-500 mb-2">-1.4% Volatility</span>
          </div>
          <svg viewBox="0 0 200 50" className="w-full h-12 mt-3 mb-3">
            <polyline points="0,40 25,35 50,38 75,30 100,28 125,32 150,25 175,22 200,20"
              fill="none" stroke="#1a2332" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <p className="text-xs text-gray-500 leading-5">Favorable EUR/USD movements and active FX hedging strategies have neutralized potential revenue leakage. Current net exposure remains within the <span className="font-bold text-gray-800">+/- 2% safety corridor</span>.</p>
        </div>
      </div>

      {/* Material Price + Crude Oil */}
      <div className="grid grid-cols-2 gap-5">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 text-lg">📊</div>
            <span className="text-[10px] font-bold tracking-widest text-blue-600 bg-blue-50 px-2.5 py-1 rounded-full uppercase">Monitoring</span>
          </div>
          <p className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-2">Material Price Inflation</p>
          <div className="flex items-end gap-2 mb-3">
            <span className="text-4xl font-black text-gray-900">+12.1%</span>
            <span className="text-sm text-gray-500 mb-1">Flat vs Prev Month</span>
          </div>
          <div className="flex items-end gap-2 h-10 mb-3">
            {["#ef4444","#f87171","#fca5a5","#d1fae5","#6ee7b7","#34d399"].map((c,i) => (
              <div key={i} className="flex-1 rounded" style={{ height: "100%", background: c }} />
            ))}
          </div>
          <p className="text-xs text-gray-500 leading-5">Supply chain stabilization has decelerated material inflation. However, semiconductor shortages continue to exert upward pressure on <span className="font-bold text-gray-800">Tier-1 production costs</span>.</p>
        </div>

        <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
          <div className="flex items-center justify-between mb-4">
            <div className="w-10 h-10 rounded-xl bg-gray-100 flex items-center justify-center text-gray-500 text-lg">🛢</div>
            <span className="text-[10px] font-bold tracking-widest text-red-600 bg-red-50 px-2.5 py-1 rounded-full uppercase">Critical</span>
          </div>
          <p className="text-xs font-bold tracking-widest text-gray-500 uppercase mb-2">Crude Oil Sensitivity</p>
          <div className="flex items-end gap-2 mb-3">
            <span className="text-4xl font-black text-gray-900">$84.50</span>
            <span className="text-sm font-bold text-red-500 mb-1">+8.2% Trend</span>
          </div>
          <svg viewBox="0 0 200 50" className="w-full h-12 mb-3">
            <polyline points="0,45 25,42 50,40 75,38 100,35 125,32 150,28 175,25 200,22"
              fill="none" stroke="#1a2332" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <p className="text-xs text-gray-500 leading-5">Energy overheads are surging due to OPEC+ production cuts. A <span className="font-bold text-gray-800">$5/barrel increase</span> correlates directly to a 0.8% drop in logistics gross margins.</p>
        </div>
      </div>

      {/* Monte Carlo */}
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
        <div className="grid grid-cols-[1fr_auto] gap-8 items-start">
          <div>
            <h3 className="text-xl font-black text-gray-900">Monte Carlo Simulation Results</h3>
            <p className="text-sm text-gray-500 mt-1 mb-4">Aggregate impact of concurrent shocks based on 10,000 iterations of market variance.</p>
            <div className="space-y-3">
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-sm text-gray-700">Worst Case Margin Impact</span>
                <span className="text-sm font-bold text-red-500">-4.2%</span>
              </div>
              <div className="flex items-center justify-between py-2">
                <span className="text-sm text-gray-700">Probability of Covenant Breach</span>
                <span className="text-sm font-bold text-emerald-600">0.03%</span>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-10 gap-1">
            {HEATMAP.map((row, ri) => row.map((v, ci) => <HeatCell key={`${ri}-${ci}`} v={v} />))}
          </div>
        </div>
        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center gap-6 text-[10px] font-bold tracking-widest text-gray-500 uppercase">
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-emerald-400" />Liquidity Status: Robust</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-blue-500" />Market Beta: 1.08</span>
          <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-amber-400" />Inflation Exposure: Elevated</span>
          <span className="ml-auto text-gray-300">Authorized Access Only · MacroPulse Securities 2024</span>
        </div>
      </div>
    </div>
  );
}

export default FinancialImpactLivePage;
