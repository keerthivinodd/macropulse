"use client";

import { useMemo, useState } from "react";
import {
  ComposedChart, Line, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Dot,
} from "recharts";
import { LIVE_VALUES, useSimulationStore } from "@/stores/simulationStore";
import { calcAIProbability, calcMonthlyDataFromMarketInputs } from "@/lib/calcEngine";
import { getSectorMultipliers } from "@/lib/sectorConfig";

const PERIOD_MONTHS: Record<string, number> = {
  "1M": 1, "3M": 3, "6M": 6, "YTD": 12,
};

const GEO_LABELS = ["North America (AMER)", "Europe & MEA (EMEA)", "Asia Pacific (APAC)", "GCC (India/UAE/SA)"];

const COLORS = {
  borrowing: "#0D1B3E",
  fx:        "#0F6E56",
  cogs:      "#BA7517",
  combined:  "#185FA5",
  mtm:       "#7c3aed",
};

const LEGEND_ITEMS = [
  { key: "borrowing", label: "Borrowing Cost", color: COLORS.borrowing },
  { key: "combined", label: "Combined Impact", color: COLORS.combined },
  { key: "cogs", label: "Commodity / COGS", color: COLORS.cogs },
  { key: "fx", label: "FX Exposure", color: COLORS.fx },
  { key: "mtm", label: "Treasury / MTM", color: COLORS.mtm },
] as const;

interface TooltipPayload {
  name: string;
  value: number;
  color: string;
}

function formatCurrencyCr(value: number) {
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}₹${Math.abs(value).toFixed(2)} Cr`;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipPayload[]; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-3 shadow-lg text-xs">
      <p className="mb-2 font-bold text-gray-800">{label}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} />
            <span className="text-gray-600">{p.name}</span>
          </div>
          <span className={`font-bold ${p.value >= 0 ? "text-gray-800" : "text-red-600"}`}>
            ₹{p.value.toFixed(3)} Cr
          </span>
        </div>
      ))}
    </div>
  );
}

export function PLSensitivityChart() {
  const {
    rateShock, fxVolatility, crudePrice,
    period, geoFilters, setGeoFilters,
    selectedSector, variables, isRunning,
    cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield,
  } = useSimulationStore();

  const [chartPeriod, setChartPeriod] = useState<"Quarterly" | "Annual">("Annual");

  const numMonths = PERIOD_MONTHS[period] ?? 12;
  const mult = useMemo(() => getSectorMultipliers(selectedSector), [selectedSector]);

  const effectiveMarket = useMemo(() => ({
    repoRate: cardRepoRate ?? (LIVE_VALUES.repoRate + rateShock),
    inrRate: cardINRRate ?? (LIVE_VALUES.inrRate * (1 + fxVolatility / 100)),
    wpi: cardWPI ?? LIVE_VALUES.wpi,
    crude: cardCrude ?? crudePrice,
    gSecYield: cardGSecYield ?? (LIVE_VALUES.gSecYield + rateShock * 0.5),
  }), [cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield, rateShock, fxVolatility, crudePrice]);

  const data = useMemo(
    () => calcMonthlyDataFromMarketInputs(effectiveMarket, LIVE_VALUES, geoFilters, numMonths, mult),
    [effectiveMarket, geoFilters, numMonths, mult]
  );

  // Quarterly aggregation
  const chartData = useMemo(() => {
    if (chartPeriod === "Annual" || data.length <= 3) return data;
    const quarters: typeof data = [];
    for (let i = 0; i < data.length; i += 3) {
      const chunk = data.slice(i, i + 3);
      quarters.push({
        month: `Q${Math.floor(i / 3) + 1}`,
        borrowing: chunk.reduce((s, d) => s + d.borrowing, 0),
        fx:        chunk.reduce((s, d) => s + d.fx, 0),
        cogs:      chunk.reduce((s, d) => s + d.cogs, 0),
        mtm:       chunk.reduce((s, d) => s + d.mtm, 0),
        combined:  chunk.reduce((s, d) => s + d.combined, 0),
      });
    }
    return quarters;
  }, [data, chartPeriod]);

  // Peak detection
  const avgAbs = chartData.length
    ? chartData.reduce((s, d) => s + Math.abs(d.combined), 0) / chartData.length
    : 0;
  const peakThreshold = avgAbs * 1.5;

  const showBorrowing = variables.includes("Repo Rate");
  const showFX        = variables.includes("FX USD/INR");
  const showCOGS      = variables.includes("Crude Oil") || variables.includes("WPI Inflation");
  const showGSec      = variables.includes("G-Sec Yield");
  const scenarioProbability = useMemo(
    () =>
      calcAIProbability(
        effectiveMarket.repoRate - LIVE_VALUES.repoRate,
        ((effectiveMarket.inrRate / LIVE_VALUES.inrRate) - 1) * 100,
        effectiveMarket.crude
      ),
    [effectiveMarket]
  );

  const summary = useMemo(() => {
    const fallback = { month: "-", borrowing: 0, fx: 0, cogs: 0, mtm: 0, combined: 0 };
    const totalImpact = chartData.reduce((sum, point) => sum + point.combined, 0);
    const peakPoint = chartData.reduce(
      (peak, point) => (Math.abs(point.combined) > Math.abs(peak.combined) ? point : peak),
      chartData[0] ?? fallback
    );

    const driverScores = [
      { label: "Borrowing costs", value: chartData.reduce((sum, point) => sum + Math.abs(point.borrowing), 0) },
      { label: "FX exposure", value: chartData.reduce((sum, point) => sum + Math.abs(point.fx), 0) },
      { label: "Commodity / COGS", value: chartData.reduce((sum, point) => sum + Math.abs(point.cogs), 0) },
      { label: "Treasury / MTM", value: chartData.reduce((sum, point) => sum + Math.abs(point.mtm), 0) },
    ];
    const dominantDriver = driverScores.reduce((best, candidate) =>
      candidate.value > best.value ? candidate : best,
    driverScores[0]);

    return { totalImpact, peakPoint, dominantDriver: dominantDriver.label };
  }, [chartData]);

  return (
    <div className="flex h-full min-h-[420px] flex-col rounded-2xl border border-gray-100 bg-white p-4 shadow-sm xl:p-5">
      <div className="mb-3 flex items-start justify-between gap-4">
        <div>
          <h3 className="text-lg font-bold text-gray-900">P&amp;L Sensitivity Projection</h3>
          <p className="mt-0.5 text-sm text-gray-500">
            Projected variance vs. Baseline (FY2024) · {selectedSector} · {period}
          </p>
          <p className="mt-1 text-xs leading-5 text-gray-500">
            Shows the monthly P&amp;L variance created by this macro scenario, helping the CFO team see total impact, peak pressure timing, and the main driver.
          </p>
        </div>
        <div className="flex overflow-hidden rounded-lg border border-gray-200 shrink-0">
          {(["Quarterly", "Annual"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setChartPeriod(v)}
              className={`px-3.5 py-1.5 text-sm font-semibold transition ${
                chartPeriod === v ? "bg-[#0D1B3E] text-white" : "text-gray-500 hover:bg-gray-50"
              }`}
            >
              {v}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-3 grid gap-2 sm:grid-cols-3">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
          <p className="text-sm font-semibold text-slate-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>Projected Total Impact</p>
          <p className={`mt-1 text-base font-bold ${summary.totalImpact >= 0 ? "text-red-700" : "text-emerald-700"}`}>
            {formatCurrencyCr(summary.totalImpact)}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
          <p className="text-sm font-semibold text-slate-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>Peak Pressure Month</p>
          <p className="mt-1 text-base font-bold text-slate-900">
            {summary.peakPoint.month} · {formatCurrencyCr(summary.peakPoint.combined)}
          </p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2">
          <p className="text-sm font-semibold text-slate-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>What To Watch</p>
          <p className="mt-1 text-base font-bold text-slate-900">{summary.dominantDriver}</p>
          <p className="mt-0.5 text-xs text-slate-500">{scenarioProbability}% materiality probability</p>
        </div>
      </div>

      <div className={`flex-1 transition-opacity duration-300 ${isRunning ? "opacity-30" : "opacity-100"}`}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={chartData} margin={{ top: 2, right: 6, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="month"
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => `₹${v.toFixed(1)}`}
              width={42}
            />
            <Tooltip content={<CustomTooltip />} />
            <ReferenceLine y={0} stroke="#d1d5db" strokeDasharray="4 4" label={{ value: "Baseline", position: "right", fontSize: 10, fill: "#9ca3af" }} />

            {/* Combined area — most prominent */}
            <Area
              type="monotone"
              dataKey="combined"
              name="Combined Impact"
              stroke={COLORS.combined}
              strokeWidth={2}
              fill="#dbeafe"
              fillOpacity={0.5}
              animationDuration={400}
              dot={(props) => {
                const { cx = 0, cy = 0, payload } = props as { cx?: number; cy?: number; payload: { combined: number } };
                if (Math.abs(payload.combined) > peakThreshold && peakThreshold > 0) {
                  return (
                    <g key={`peak-${cx}`}>
                      <Dot cx={cx} cy={cy} r={5} fill="#dc2626" stroke="white" strokeWidth={2} />
                      <text x={cx} y={cy - 10} textAnchor="middle" fontSize={9} fill="#dc2626" fontWeight="bold">Peak</text>
                    </g>
                  );
                }
                return <g key={`dot-${cx}`} />;
              }}
            />

            {showBorrowing && (
              <Line
                type="monotone"
                dataKey="borrowing"
                name="Borrowing Cost"
                stroke={COLORS.borrowing}
                strokeWidth={2}
                dot={false}
                animationDuration={400}
              />
            )}
            {showFX && (
              <Line
                type="monotone"
                dataKey="fx"
                name="FX Exposure"
                stroke={COLORS.fx}
                strokeWidth={2}
                dot={false}
                animationDuration={400}
              />
            )}
            {(showCOGS || showGSec) && (
              <Line
                type="monotone"
                dataKey="cogs"
                name="Commodity / COGS"
                stroke={COLORS.cogs}
                strokeWidth={2}
                dot={false}
                animationDuration={400}
              />
            )}
            {showGSec && (
              <Line
                type="monotone"
                dataKey="mtm"
                name="Treasury / MTM"
                stroke={COLORS.mtm}
                strokeWidth={2}
                dot={false}
                animationDuration={400}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1.5 border-b border-gray-100 pb-2 text-sm">
        {LEGEND_ITEMS.filter((item) => {
          if (item.key === "borrowing") return showBorrowing;
          if (item.key === "fx") return showFX;
          if (item.key === "cogs") return showCOGS || showGSec;
          if (item.key === "mtm") return showGSec;
          return true;
        }).map((item) => (
          <div key={item.key} className="flex items-center gap-2 text-gray-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
            <span>{item.label}</span>
          </div>
        ))}
      </div>

      <div className="mt-2">
        <p className="mb-2 text-sm font-semibold text-gray-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>Geographic Filter</p>
        <div className="flex flex-wrap gap-x-4 gap-y-2">
          {GEO_LABELS.map((label, i) => (
            <label key={label} className="flex cursor-pointer items-center gap-2">
              <input
                type="checkbox"
                checked={geoFilters[i]}
                onChange={(e) => {
                  const next = [...geoFilters];
                  next[i] = e.target.checked;
                  setGeoFilters(next);
                }}
                className="h-4 w-4 rounded border-gray-300 accent-[#0D1B3E]"
              />
              <span className="text-sm text-gray-600">{label}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  );
}
