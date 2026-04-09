"use client";

const regions = [
  { name: "GCC", countries: ["UAE","Saudi Arabia","Qatar","Kuwait"], gdp: "$2.1T", growth: "+3.8%", risk: "Medium", color: "bg-amber-400" },
  { name: "North America", countries: ["USA","Canada","Mexico"], gdp: "$28.4T", growth: "+2.1%", risk: "Low", color: "bg-emerald-400" },
  { name: "Europe & MEA", countries: ["Germany","France","UK","Egypt"], gdp: "$19.2T", growth: "+1.4%", risk: "Medium", color: "bg-amber-400" },
  { name: "Asia Pacific", countries: ["China","Japan","India","Singapore"], gdp: "$35.6T", growth: "+4.9%", risk: "Low", color: "bg-emerald-400" },
];

export default function RegionalViewPage() {
  return (
    <div className="px-8 py-7 space-y-6">
      <div>
        <h2 className="text-3xl font-black text-gray-900">Regional View</h2>
        <p className="text-sm text-gray-500 mt-1">Macroeconomic exposure and opportunity mapping by geography</p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {regions.map(r => (
          <div key={r.name} className="bg-white rounded-2xl p-6 shadow-sm border border-gray-100">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-bold text-gray-900">{r.name}</h3>
              <div className="flex items-center gap-1.5">
                <span className={`w-2 h-2 rounded-full ${r.color}`} />
                <span className="text-xs font-semibold text-gray-500">{r.risk} Risk</span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">GDP</p>
                <p className="text-2xl font-black text-gray-900">{r.gdp}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-widest mb-1">Growth</p>
                <p className="text-2xl font-black text-emerald-600">{r.growth}</p>
              </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {r.countries.map(c => (
                <span key={c} className="text-xs bg-gray-100 text-gray-600 px-2.5 py-1 rounded-full font-medium">{c}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
