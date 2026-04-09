"use client";

import { useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { FilterSidebar } from "@/components/stream/macropulse/simulation/FilterBar";
import { ScenarioVariables } from "@/components/stream/macropulse/simulation/ScenarioVariables";
import { PLSensitivityChart } from "@/components/stream/macropulse/simulation/PLSensitivityChart";
import { FinancialImpactCards } from "@/components/stream/macropulse/simulation/FinancialImpactCards";
import { TotalExposureBanner } from "@/components/stream/macropulse/simulation/TotalExposureBanner";

export default function SimulationImpactPage() {
  const [filtersCollapsed, setFiltersCollapsed] = useState(false);

  return (
    <div className="flex min-h-full min-w-0 flex-col bg-[radial-gradient(circle_at_top,_rgba(157,227,229,0.34),_transparent_34%),linear-gradient(180deg,_#eef8f8_0%,_#f8fcfc_100%)] xl:flex-row">
      {!filtersCollapsed && <FilterSidebar onCollapse={() => setFiltersCollapsed(true)} />}

      {/* Main scrollable content */}
      <div className="min-w-0 flex-1">
        {/* Page header */}
        <div className="border-b border-gray-200/70 bg-white/55 px-6 py-5 backdrop-blur-sm xl:px-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-[28px] font-black leading-tight text-gray-900">Simulation Impact</h2>
              <p className="mt-1.5 max-w-4xl text-sm leading-6 text-gray-500">
                Tune macro variables and sector exposure in real time. See cascaded P&amp;L, margin, and borrowing impact instantly.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setFiltersCollapsed((value) => !value)}
              className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3.5 py-2 text-sm font-semibold text-slate-700 transition hover:border-slate-300 hover:bg-slate-50"
            >
              {filtersCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
              {filtersCollapsed ? "Show Filters" : "Hide Filters"}
            </button>
          </div>
        </div>

        <div className="space-y-5 p-4 sm:p-5 xl:p-6">
          {/* Row 1: Scenario Variables + P&L Chart side by side */}
          <div className="grid gap-5 2xl:grid-cols-[minmax(340px,420px)_minmax(0,1fr)]">
            <ScenarioVariables />
            <PLSensitivityChart />
          </div>

          {/* Row 2: Total Exposure Banner — full width */}
          <TotalExposureBanner />

          {/* Row 3: Financial Impact Cards — full width horizontal scroll */}
          <FinancialImpactCards />
        </div>
      </div>
    </div>
  );
}
