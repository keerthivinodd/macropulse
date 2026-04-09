"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, ChevronLeft, Download, Play, X } from "lucide-react";
import { useSimulationStore, ALL_VARIABLES } from "@/stores/simulationStore";
import type { Variable, Region, Period } from "@/stores/simulationStore";
import { COMPANY_GROUPS, getSectorById } from "@/lib/sectorConfig";

const REGIONS: Region[] = ["IN", "UAE", "SA"];
const PERIODS: Period[] = ["1M", "3M", "6M", "YTD"];

const REGION_LABELS: Record<Region, string> = {
  IN:  "India (IN)",
  UAE: "UAE",
  SA:  "Saudi Arabia (SA)",
};

const COMPANY_COLORS: Record<string, string> = {
  "tata":         "bg-blue-600",
  "reliance":     "bg-sky-600",
  "adani":        "bg-green-700",
  "mahindra":     "bg-red-600",
  "jsw":          "bg-orange-600",
  "aditya-birla": "bg-violet-600",
  "amazon":       "bg-amber-600",
  "apple":        "bg-slate-500",
  "microsoft":    "bg-blue-500",
  "cocacola":     "bg-red-500",
  "samsung":      "bg-indigo-600",
  "toyota":       "bg-rose-600",
};

function getCompanyColor(id: string) {
  return COMPANY_COLORS[id] ?? "bg-gray-500";
}

function getInitials(name: string) {
  return name.split(" ").slice(0, 2).map((w) => w[0]).join("").toUpperCase();
}

function getSectorEmoji(label: string) {
  const l = label.toLowerCase();
  if (l.includes("metal") || l.includes("mining") || l.includes("alumin")) return "🏭";
  if (l.includes("steel")) return "🏭";
  if (l.includes("cement")) return "🏗️";
  if (l.includes("it service") || l.includes("tcs") || l.includes("tech mahindra")) return "💻";
  if (l.includes("cloud") || l.includes("azure") || l.includes("aws")) return "☁️";
  if (l.includes("automobile") || l.includes("motor") || l.includes("vehicle")) return "🚗";
  if (l.includes("electric vehicle") || l.includes("ev ")) return "🔋";
  if (l.includes("farm") || l.includes("agri") || l.includes("tractor")) return "🌾";
  if (l.includes("renew") || l.includes("green energy") || l.includes("solar")) return "🌱";
  if (l.includes("new energy")) return "🌱";
  if (l.includes("energy") || l.includes("power")) return "⚡";
  if (l.includes("oil") || l.includes("petro") || l.includes("refin")) return "🛢️";
  if (l.includes("telecom") || l.includes("jio") || l.includes("vodafone")) return "📡";
  if (l.includes("digital")) return "📡";
  if (l.includes("financial service") || l.includes("finance") || l.includes("capital")) return "🏦";
  if (l.includes("fashion") || l.includes("retail") || l.includes("pantaloon") || l.includes("westside")) return "🛍️";
  if (l.includes("chemical") || l.includes("grasim") || l.includes("fibre")) return "🧪";
  if (l.includes("media") || l.includes("network18")) return "📺";
  if (l.includes("streaming") || l.includes("prime video") || l.includes("xbox")) return "🎬";
  if (l.includes("gaming")) return "🎮";
  if (l.includes("port") || l.includes("logistic")) return "🚢";
  if (l.includes("airport")) return "✈️";
  if (l.includes("hospit") || l.includes("taj") || l.includes("club mahindra")) return "🏨";
  if (l.includes("real estate") || l.includes("lifespace")) return "🏢";
  if (l.includes("infrastructure") || l.includes("infra")) return "🔧";
  if (l.includes("sports")) return "🏆";
  if (l.includes("consumer good") || l.includes("fmcg")) return "🛒";
  if (l.includes("e-commerce") || l.includes("amazon retail")) return "🛒";
  if (l.includes("semi")) return "💾";
  if (l.includes("mobile") || l.includes("galaxy") || l.includes("iphone")) return "📱";
  if (l.includes("display")) return "🖥️";
  if (l.includes("appliance")) return "🏠";
  if (l.includes("service") || l.includes("app store")) return "📦";
  if (l.includes("productiv") || l.includes("microsoft 365")) return "📝";
  if (l.includes("ai ") || l.includes("copilot")) return "🤖";
  if (l.includes("professional") || l.includes("linkedin")) return "👔";
  if (l.includes("adverti")) return "📢";
  if (l.includes("beverage") || l.includes("sparkling") || l.includes("juice")) return "🥤";
  if (l.includes("bottling")) return "🏭";
  return "📊";
}

export function FilterSidebar({ onCollapse }: { onCollapse?: () => void }) {
  const {
    variables, setVariables,
    region, setRegion,
    period, setPeriod,
    selectedCompany, setCompany,
    selectedSectorId, setSector,
    setIsRunning,
  } = useSimulationStore();

  const [companyOpen, setCompanyOpen] = useState(false);
  const [sectorOpen, setSectorOpen] = useState(false);
  const [companySearch, setCompanySearch] = useState("");
  const companyRef = useRef<HTMLDivElement>(null);
  const sectorRef  = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (companyRef.current && !companyRef.current.contains(e.target as Node)) {
        setCompanyOpen(false);
      }
      if (sectorRef.current && !sectorRef.current.contains(e.target as Node)) {
        setSectorOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const currentCompany = COMPANY_GROUPS.find((c) => c.id === selectedCompany) ?? null;
  const currentSector  = getSectorById(selectedSectorId) ?? null;

  const filtered = companySearch.trim()
    ? COMPANY_GROUPS.filter((c) => c.name.toLowerCase().includes(companySearch.toLowerCase()))
    : COMPANY_GROUPS;

  const indiaGroups  = filtered.filter((c) => c.geography === "India");
  const globalGroups = filtered.filter((c) => c.geography === "Global");

  const toggleVariable = (v: Variable) => {
    if (variables.includes(v)) {
      if (variables.length === 1) return;
      setVariables(variables.filter((x) => x !== v));
    } else {
      setVariables([...variables, v]);
    }
  };

  const allSelected = variables.length === ALL_VARIABLES.length;

  const handleRunSimulation = () => {
    setIsRunning(true);
    setTimeout(() => setIsRunning(false), 650);
  };

  const handleExport = () => {
    const state = useSimulationStore.getState();
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `macropulse-simulation-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const clearAll = () => {
    setVariables([...ALL_VARIABLES]);
    setRegion("IN");
    setPeriod("YTD");
  };

  return (
    <aside className="flex w-full shrink-0 flex-col border-b border-r-0 border-gray-200 bg-white xl:w-[248px] xl:border-b-0 xl:border-r 2xl:w-[264px]">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-gray-100 px-4 py-4">
        <span className="text-lg font-semibold text-gray-800" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
          Filters
        </span>
        <div className="flex items-center gap-2">
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-xs font-semibold text-blue-600 transition hover:text-blue-800"
          >
            <X className="h-3 w-3" />
            Clear All
          </button>
          {onCollapse && (
            <button
              type="button"
              onClick={onCollapse}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-gray-200 text-slate-600 transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
              aria-label="Collapse filters"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>

      {/* Scrollable body */}
      <div className="space-y-5 px-4 py-4 xl:flex-1 xl:overflow-y-auto">

        {/* Variables */}
        <div>
          <p className="mb-2.5 text-sm font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Variables
          </p>
          <div className="space-y-2">
            <label className="flex cursor-pointer items-center gap-2.5">
              <input
                type="checkbox"
                checked={allSelected}
                onChange={() => setVariables([...ALL_VARIABLES])}
                className="h-3.5 w-3.5 rounded border-gray-300 accent-[#0D1B3E]"
              />
              <span className="text-sm font-semibold text-gray-800">All Variables</span>
            </label>
            {ALL_VARIABLES.map((v) => (
              <label key={v} className="flex cursor-pointer items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={variables.includes(v)}
                  onChange={() => toggleVariable(v)}
                  className="h-3.5 w-3.5 rounded border-gray-300 accent-[#0D1B3E]"
                />
                <span className={`text-sm transition ${variables.includes(v) ? "font-medium text-gray-800" : "text-gray-500"}`}>
                  {v}
                </span>
              </label>
            ))}
          </div>
        </div>

        <div className="h-px bg-gray-100" />

        {/* Region */}
        <div>
          <p className="mb-2.5 text-sm font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Region
          </p>
          <div className="space-y-1">
            {REGIONS.map((r) => (
              <button
                key={r}
                onClick={() => setRegion(r)}
                className={`w-full rounded-lg px-3 py-2.5 text-left text-sm font-semibold transition ${
                  region === r
                    ? "bg-[#185FA5] text-white"
                    : "text-gray-600 hover:bg-gray-50"
                }`}
              >
                {REGION_LABELS[r]}
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-gray-100" />

        {/* Period */}
        <div>
          <p className="mb-2.5 text-sm font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Period
          </p>
          <div className="grid grid-cols-2 gap-1.5">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded-lg py-2.5 text-center text-sm font-bold transition ${
                  period === p
                    ? "bg-[#0F6E56] text-white"
                    : "border border-gray-200 text-gray-600 hover:bg-gray-50"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="h-px bg-gray-100" />

        {/* Company */}
        <div ref={companyRef}>
          <p className="mb-2.5 text-sm font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Company
          </p>
          <button
            onClick={() => { setCompanyOpen((o) => !o); setSectorOpen(false); }}
            className="flex w-full items-center justify-between rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-medium text-gray-700 transition hover:border-gray-300"
          >
            {currentCompany ? (
              <span className="flex items-center gap-2 min-w-0">
                <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white ${getCompanyColor(currentCompany.id)}`}>
                  {getInitials(currentCompany.name)}
                </span>
                <span className="truncate">{currentCompany.name}</span>
              </span>
            ) : (
              <span className="text-gray-400">Search or select...</span>
            )}
            <ChevronDown className={`ml-1.5 h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform ${companyOpen ? "rotate-180" : ""}`} />
          </button>

          {companyOpen && (
            <div className="mt-1.5 rounded-xl border border-gray-200 bg-white shadow-lg overflow-hidden">
              {/* Search input */}
              <div className="border-b border-gray-100 px-2 py-2">
                <input
                  autoFocus
                  type="text"
                  placeholder="Search companies..."
                  value={companySearch}
                  onChange={(e) => setCompanySearch(e.target.value)}
                  className="w-full rounded-md border border-gray-200 px-2 py-1.5 text-sm outline-none focus:border-blue-400"
                />
              </div>
              <div className="max-h-56 overflow-y-auto">
                {/* India group */}
                {indiaGroups.length > 0 && (
                  <>
                    <div className="bg-gray-50 px-3 py-1.5 text-xs font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
                      India
                    </div>
                    {indiaGroups.map((company) => (
                      <button
                        key={company.id}
                        onClick={() => {
                          setCompany(company.id);
                          setCompanyOpen(false);
                          setCompanySearch("");
                        }}
                        className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-blue-50 ${
                          selectedCompany === company.id ? "bg-blue-50 font-semibold text-[#185FA5]" : "text-gray-700"
                        }`}
                      >
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white ${getCompanyColor(company.id)}`}>
                          {getInitials(company.name)}
                        </span>
                        <span className="truncate">{company.name}</span>
                      </button>
                    ))}
                  </>
                )}
                {/* Global group */}
                {globalGroups.length > 0 && (
                  <>
                    <div className="bg-gray-50 px-3 py-1.5 text-xs font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
                      Global
                    </div>
                    {globalGroups.map((company) => (
                      <button
                        key={company.id}
                        onClick={() => {
                          setCompany(company.id);
                          setCompanyOpen(false);
                          setCompanySearch("");
                        }}
                        className={`flex w-full items-center gap-2 px-3 py-2.5 text-left text-sm transition hover:bg-blue-50 ${
                          selectedCompany === company.id ? "bg-blue-50 font-semibold text-[#185FA5]" : "text-gray-700"
                        }`}
                      >
                        <span className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[9px] font-bold text-white ${getCompanyColor(company.id)}`}>
                          {getInitials(company.name)}
                        </span>
                        <span className="truncate">{company.name}</span>
                      </button>
                    ))}
                  </>
                )}
                {filtered.length === 0 && (
                  <p className="px-3 py-3 text-sm text-gray-400">No companies found.</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sector */}
        <div ref={sectorRef}>
          <p className="mb-2.5 text-sm font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Sector
          </p>
          <button
            disabled={!currentCompany}
            onClick={() => { setSectorOpen((o) => !o); setCompanyOpen(false); }}
            className={`flex w-full items-center justify-between rounded-lg border px-3 py-2.5 text-sm font-medium transition ${
              currentCompany
                ? "border-gray-200 text-gray-700 hover:border-gray-300"
                : "border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed"
            }`}
          >
            {currentCompany ? (
              currentSector ? (
                <span className="flex items-center gap-1.5 min-w-0">
                  <span>{getSectorEmoji(currentSector.label)}</span>
                  <span className="truncate">{currentSector.label.split(" · ")[0]}</span>
                </span>
              ) : (
                <span className="text-gray-400">Select sector...</span>
              )
            ) : (
              <span>Select a company first</span>
            )}
            <ChevronDown className={`ml-1.5 h-3.5 w-3.5 shrink-0 text-gray-400 transition-transform ${sectorOpen ? "rotate-180" : ""}`} />
          </button>

          {sectorOpen && currentCompany && (
            <div className="mt-1.5 max-h-56 overflow-y-auto rounded-xl border border-gray-200 bg-white shadow-lg">
              {currentCompany.sectors.map((sector) => (
                <button
                  key={sector.id}
                  onClick={() => {
                    setSector(sector.id);
                    setSectorOpen(false);
                  }}
                  className={`flex w-full items-start gap-2 px-3 py-2.5 text-left transition hover:bg-blue-50 ${
                    selectedSectorId === sector.id
                      ? "bg-blue-50"
                      : ""
                  }`}
                >
                  <span className="mt-px shrink-0 text-sm">{getSectorEmoji(sector.label)}</span>
                  <span className="min-w-0">
                    <span className={`block truncate text-sm font-semibold ${selectedSectorId === sector.id ? "text-[#185FA5]" : "text-gray-800"}`}>
                      {sector.label.split(" · ")[0]}
                    </span>
                    <span className="block truncate text-xs text-gray-400">
                      {sector.entity}
                    </span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

      </div>

      {/* Footer actions */}
      <div className="space-y-2 border-t border-gray-100 px-4 py-4">
        <span
          className="block rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-center text-sm font-semibold text-amber-700"
          style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
        >
          Indicative Data
        </span>
        <button
          onClick={handleExport}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-gray-200 px-3 py-2.5 text-sm font-semibold text-gray-700 transition hover:bg-gray-50"
        >
          <Download className="h-3.5 w-3.5" />
          Export
        </button>
        <button
          onClick={handleRunSimulation}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-[#0D1B3E] px-3 py-2.5 text-sm font-bold text-white transition hover:bg-[#1a2e52]"
        >
          <Play className="h-3.5 w-3.5" />
          Run Simulation
        </button>
      </div>
    </aside>
  );
}
