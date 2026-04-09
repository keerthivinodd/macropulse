"use client";

import DataSourcesLivePage from "./DataSourcesLivePage";

const sources = [
  { name: "CBUAE — Central Bank UAE", type: "Central Bank", status: "Live", latency: "2s", records: "1.2M" },
  { name: "SAMA — Saudi Arabia Monetary", type: "Central Bank", status: "Live", latency: "4s", records: "980K" },
  { name: "Bloomberg Terminal Feed", type: "Market Data", status: "Live", latency: "1s", records: "45M" },
  { name: "IMF World Economic Outlook", type: "Research", status: "Synced", latency: "Daily", records: "220K" },
  { name: "OPEC Production Reports", type: "Commodity", status: "Live", latency: "15m", records: "88K" },
  { name: "World Bank Open Data", type: "Research", status: "Synced", latency: "Weekly", records: "1.8M" },
];

// Legacy placeholder kept temporarily while the live page is wired for the demo.
// eslint-disable-next-line @typescript-eslint/no-unused-vars
function LegacyDataSourcesPage() {
  return (
    <div className="px-8 py-7 space-y-6">
      <div>
        <h2 className="text-3xl font-black text-gray-900">Regional Data Sources</h2>
        <p className="text-sm text-gray-500 mt-1">Connected data feeds powering MacroPulse intelligence</p>
      </div>
      <div className="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              {["Source","Type","Status","Latency","Records"].map(h => (
                <th key={h} className="px-6 py-3 text-left text-[10px] font-bold tracking-widest text-gray-500 uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {sources.map(s => (
              <tr key={s.name} className="hover:bg-gray-50 transition">
                <td className="px-6 py-4 text-sm font-semibold text-gray-900">{s.name}</td>
                <td className="px-6 py-4 text-sm text-gray-500">{s.type}</td>
                <td className="px-6 py-4">
                  <span className={`text-[10px] font-bold tracking-widest px-2.5 py-1 rounded-full uppercase ${s.status === "Live" ? "text-emerald-600 bg-emerald-50" : "text-blue-600 bg-blue-50"}`}>{s.status}</span>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">{s.latency}</td>
                <td className="px-6 py-4 text-sm font-semibold text-gray-700">{s.records}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default DataSourcesLivePage;
