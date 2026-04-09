"use client";

import { useMemo } from "react";
import { useSimulationStore, LIVE_VALUES } from "@/stores/simulationStore";
import { getSectorMultipliers } from "@/lib/sectorConfig";
import { PERIOD_SCALE } from "@/lib/calcEngine";

// ─── sparkline ────────────────────────────────────────────────────────────────

function Sparkline({ values }: { values: number[] }) {
  const max = Math.max(...values.map(Math.abs), 0.01);
  const yTop = max;
  const yMid = max / 2;

  return (
    <div className="mt-2">
      <div className="flex">
        {/* Y-axis labels */}
        <div className="flex flex-col justify-between items-end pr-1.5 h-14 shrink-0">
          <span className="text-[8px] text-gray-400 leading-none">{yTop.toFixed(1)}</span>
          <span className="text-[8px] text-gray-400 leading-none">{yMid.toFixed(1)}</span>
          <span className="text-[8px] text-gray-400 leading-none">0</span>
        </div>
        {/* Bars */}
        <div className="flex items-end gap-1.5 h-14 flex-1 border-l border-b border-gray-200 pl-1 pb-0.5">
          {values.map((v, i) => (
            <div
              key={i}
              className={`flex-1 rounded-sm transition-all duration-500 ${v >= 0 ? "bg-red-200" : "bg-teal-200"}`}
              style={{ height: `${Math.max(15, (Math.abs(v) / max) * 100)}%` }}
              title={`Q${i + 1}: ₹${v.toFixed(2)} Cr`}
            />
          ))}
        </div>
      </div>
      {/* X-axis labels */}
      <div className="flex">
        <div className="shrink-0 w-6" /> {/* spacer for y-axis */}
        <div className="flex flex-1 pl-1">
          {values.map((_, i) => (
            <span key={i} className="flex-1 text-center text-[8px] text-gray-400 mt-0.5">
              Q{i + 1}
            </span>
          ))}
        </div>
      </div>
      {/* Axis titles */}
      <div className="flex justify-between mt-0.5">
        <span className="text-[7px] text-gray-300">₹ Cr</span>
        <span className="text-[7px] text-gray-300">Quarter</span>
      </div>
    </div>
  );
}

// ─── card-level parameter slider ──────────────────────────────────────────────

interface CardSliderProps {
  paramLabel: string;
  liveValue: number;
  value: number;           // current slider value
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
  onReset: () => void;
  isCustom: boolean;
}

function CardSlider({
  paramLabel, liveValue, value, min, max, step,
  format, onChange, onReset, isCustom,
}: CardSliderProps) {
  const pct = ((value - min) / (max - min)) * 100;
  const livePct = ((liveValue - min) / (max - min)) * 100;
  const delta = value - liveValue;
  const isAbove = delta > 0.001;
  const isBelow = delta < -0.001;

  return (
    <div className="mt-3 border-t border-gray-100 pt-3">
      {/* Top row: param name + badges */}
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-xs font-semibold text-gray-400" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>{paramLabel}</span>
        <div className="flex items-center gap-1.5">
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-semibold text-gray-500">
            Live {format(liveValue)}
          </span>
          {isCustom && (isAbove || isBelow) && (
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
              isAbove ? "bg-red-50 text-red-600" : "bg-teal-50 text-teal-600"
            }`}>
              {isAbove ? "▲" : "▼"}{isAbove ? "+" : ""}{format(delta).replace("$", "").replace("%", "")}
              {format(liveValue).includes("%") ? "%" : format(liveValue).includes("₹") ? " ₹" : ""}
            </span>
          )}
        </div>
      </div>

      {/* Slider with live marker */}
      <div className="relative">
        {/* Live marker tick */}
        <div
          className="absolute top-0 bottom-0 flex flex-col items-center pointer-events-none"
          style={{ left: `${livePct}%`, transform: "translateX(-50%)" }}
        >
          <span className="mb-0.5 whitespace-nowrap text-[9px] font-bold text-[#0D1B3E]">live</span>
          <div className="w-0.5 h-3 bg-[#0D1B3E] rounded-full mt-3" />
        </div>

        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="relative h-1.5 w-full cursor-pointer appearance-none rounded-full transition-all duration-150"
          style={{
            background: (() => {
              const lo = Math.min(pct, livePct);
              const hi = Math.max(pct, livePct);
              const fillColor = isAbove ? "#ef4444" : isBelow ? "#0F6E56" : "#d1d5db";
              return `linear-gradient(to right, #d1d5db 0%, #d1d5db ${lo}%, ${fillColor} ${lo}%, ${fillColor} ${hi}%, #d1d5db ${hi}%, #d1d5db 100%)`;
            })(),
          }}
        />
      </div>

      {/* Axis + live annotation row */}
      <div className="mt-1 flex items-center justify-between text-[10px] text-gray-400">
        <span>{format(min)}</span>
        <span className="text-[#0D1B3E] font-semibold">{format(liveValue)} (live)</span>
        <span>{format(max)}</span>
      </div>

      {/* Sim value + reset */}
      <div className="mt-1 flex items-center justify-between">
        <span className="text-[10px] text-gray-400">
          Your sim: <span className="font-semibold text-gray-700">{format(value)}</span>
        </span>
        {isCustom && (
          <button
            onClick={onReset}
            className="text-[10px] font-semibold text-teal-600 transition hover:text-teal-800"
          >
            Reset to live
          </button>
        )}
      </div>
    </div>
  );
}

// ─── impact card ──────────────────────────────────────────────────────────────

interface ImpactCardProps {
  icon: string;
  title: string;
  category: string;
  value: number;
  period: string;
  description: string;
  sparkValues: number[];
  isRunning: boolean;
  visible: boolean;
  isCustom: boolean;
  slider: React.ReactNode;
}

function ImpactCard({
  icon, title, category, value, period, description,
  sparkValues, isRunning, visible, isCustom, slider,
}: ImpactCardProps) {
  if (!visible) return null;
  const isLoss = value > 0;

  return (
    <div className={`relative min-w-0 rounded-2xl border bg-white p-5 shadow-sm transition-all duration-300 ${
      isCustom ? "border-teal-200 ring-1 ring-teal-100" : isLoss ? "border-red-100" : "border-teal-100"
    } ${isRunning ? "animate-pulse" : ""}`}>
      {isRunning && <div className="absolute inset-0 rounded-2xl bg-gray-100 animate-pulse" />}

      <div className={`relative transition-opacity duration-200 ${isRunning ? "opacity-0" : "opacity-100"}`}>
        {/* Card header */}
        <div className="mb-4 flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-50 text-lg">
              {icon}
            </div>
            {isCustom && (
              <span className="h-2 w-2 rounded-full bg-teal-500" title="Custom override active" />
            )}
          </div>
          <div className="flex flex-col items-end gap-1">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
              isCustom ? "bg-teal-50 text-teal-700" : "bg-gray-100 text-gray-500"
            }`}
              style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
            >
              {isCustom ? "Custom" : "Base Case"}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
              isLoss ? "bg-red-50 text-red-600" : "bg-teal-50 text-teal-600"
            }`}
              style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
            >
              {category}
            </span>
          </div>
        </div>

        {/* Title + value */}
        <p className="mb-2 text-sm font-semibold text-gray-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>{title}</p>

        <div className="flex items-end gap-1.5">
          <span className={`text-3xl font-black leading-none ${isLoss ? "text-red-700" : "text-teal-700"}`}>
            ₹{Math.abs(value).toFixed(2)}
          </span>
          <span className="mb-1 text-sm text-gray-500">Cr / {period}</span>
        </div>

        <p className="mt-3 text-sm leading-6 text-gray-500">{description}</p>

        <Sparkline values={sparkValues} />

        {/* Per-card slider */}
        {slider}
      </div>
    </div>
  );
}

// ─── main export ──────────────────────────────────────────────────────────────

export function FinancialImpactCards() {
  const {
    rateShock, fxVolatility, crudePrice,
    selectedSector, selectedSubIndustry, region, period, variables, isRunning,
    cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield,
    setCardRepoRate, setCardINRRate, setCardWPI, setCardCrude, setCardGSecYield,
  } = useSimulationStore();

  const mult  = useMemo(() => getSectorMultipliers(selectedSector), [selectedSector]);
  const scale = PERIOD_SCALE[period] ?? 1;

  // Effective values: card override → global scenario shock → live market value
  const effectiveRepo  = cardRepoRate  ?? (LIVE_VALUES.repoRate  + rateShock);
  const effectiveINR   = cardINRRate   ?? (LIVE_VALUES.inrRate   * (1 + fxVolatility / 100));
  const effectiveWPI   = cardWPI       ?? LIVE_VALUES.wpi;
  const effectiveCrude = cardCrude     ?? crudePrice;
  const effectiveGSec  = cardGSecYield ?? (LIVE_VALUES.gSecYield + rateShock * 0.5);

  // Impact calculations using card-level params
  const borrowingVal = useMemo(() =>
    250 * 0.65 * ((effectiveRepo - LIVE_VALUES.repoRate) / 100) * mult.rate * scale,
    [effectiveRepo, mult.rate, scale]);

  const fxVal = useMemo(() => {
    const deltaRatio = Math.abs(effectiveINR - LIVE_VALUES.inrRate) / LIVE_VALUES.inrRate;
    return 12.5 * (LIVE_VALUES.inrRate / 100) * 0.35 * deltaRatio * mult.fx * scale;
  }, [effectiveINR, mult.fx, scale]);

  const materialVal = useMemo(() =>
    180 * ((30 + 15) / 100) * ((effectiveWPI - LIVE_VALUES.wpi) / 100) * mult.wpi * scale,
    [effectiveWPI, mult.wpi, scale]);

  const crudeVal = useMemo(() =>
    180 * (25 / 100) * ((effectiveCrude - LIVE_VALUES.crude) / LIVE_VALUES.crude) * mult.crude * scale,
    [effectiveCrude, mult.crude, scale]);

  const mtmVal = useMemo(() => {
    const raw = 60 * 4.2 * ((effectiveGSec - LIVE_VALUES.gSecYield) / 100);
    return raw; // positive yield move → positive value (cost/loss)
  }, [effectiveGSec]);

  // Sparklines (quarterly Q1–Q4 trend at card-effective values)
  const borrowingSpark = [0.25, 0.5, 0.75, 1.0].map((f) =>
    250 * 0.65 * (((effectiveRepo - LIVE_VALUES.repoRate) * f) / 100) * mult.rate * 0.25);
  const fxSpark = [0.3, 0.6, 0.8, 1.0].map((f) => {
    const delta = Math.abs((effectiveINR - LIVE_VALUES.inrRate) * f) / LIVE_VALUES.inrRate;
    return 12.5 * (LIVE_VALUES.inrRate / 100) * 0.35 * delta * mult.fx * 0.25;
  });
  const materialSpark = [0.8, 0.9, 0.95, 1.0].map((f) =>
    180 * 0.45 * (((effectiveWPI - LIVE_VALUES.wpi) * f) / 100) * mult.wpi * 0.25);
  const crudeSpark = [0.9, 0.95, 1.0, 1.05].map((f) =>
    180 * 0.25 * (((effectiveCrude * f) - LIVE_VALUES.crude) / LIVE_VALUES.crude) * mult.crude * 0.25);
  const mtmSpark = [0.3, 0.5, 0.8, 1.0].map((f) =>
    60 * 4.2 * (((effectiveGSec - LIVE_VALUES.gSecYield) * f) / 100));

  const showRate  = variables.includes("Repo Rate");
  const showFX    = variables.includes("FX USD/INR");
  const showWPI   = variables.includes("WPI Inflation");
  const showCrude = variables.includes("Crude Oil");
  const showGSec  = variables.includes("G-Sec Yield");

  const fmtPct = (v: number) => `${v >= 0 ? "" : ""}${v.toFixed(2)}%`;
  const fmtINR = (v: number) => `₹${v.toFixed(2)}`;
  const fmtUSD = (v: number) => `$${v.toFixed(1)}`;


  return (
    <div>
      <div className="mb-4">
        <h3 className="text-lg font-bold text-gray-900">Real-Time Financial Impact</h3>
        <p className="mt-1 text-sm text-gray-500">
          Adjust each card's parameter independently · {selectedSubIndustry} · Region: {region}
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3">

        {/* Card 1 — Borrowing Cost */}
        <ImpactCard
          icon="📊" title="Borrowing Cost Impact" category="Rate Sensitive"
          value={borrowingVal} period={period} visible={showRate} isRunning={isRunning}
          isCustom={cardRepoRate !== null}
          description="Effect of RBI repo rate changes on floating rate debt servicing costs."
          sparkValues={borrowingSpark}
          slider={
            <CardSlider
              paramLabel="RBI Repo Rate"
              liveValue={LIVE_VALUES.repoRate}
              value={effectiveRepo}
              min={4.0} max={10.0} step={0.05}
              format={fmtPct}
              isCustom={cardRepoRate !== null}
              onChange={(v) => setCardRepoRate(v)}
              onReset={() => setCardRepoRate(null)}
            />
          }
        />

        {/* Card 2 — Currency Risk */}
        <ImpactCard
          icon="💱" title="Currency Risk Exposure" category="FX Exposure"
          value={fxVal} period={period} visible={showFX} isRunning={isRunning}
          isCustom={cardINRRate !== null}
          description="USD/INR volatility impact on net USD-denominated payables and receivables."
          sparkValues={fxSpark}
          slider={
            <CardSlider
              paramLabel="USD/INR Rate"
              liveValue={LIVE_VALUES.inrRate}
              value={effectiveINR}
              min={78} max={92} step={0.10}
              format={fmtINR}
              isCustom={cardINRRate !== null}
              onChange={(v) => setCardINRRate(v)}
              onReset={() => setCardINRRate(null)}
            />
          }
        />

        {/* Card 3 — Material Price Inflation */}
        <ImpactCard
          icon="📦" title="Material Price Inflation" category="Input Cost"
          value={materialVal} period={period} visible={showWPI} isRunning={isRunning}
          isCustom={cardWPI !== null}
          description="WPI-driven cost escalation across steel, petroleum, and key raw material inputs."
          sparkValues={materialSpark}
          slider={
            <CardSlider
              paramLabel="WPI Inflation"
              liveValue={LIVE_VALUES.wpi}
              value={effectiveWPI}
              min={0} max={14} step={0.10}
              format={fmtPct}
              isCustom={cardWPI !== null}
              onChange={(v) => setCardWPI(v)}
              onReset={() => setCardWPI(null)}
            />
          }
        />

        {/* Card 4 — Crude Oil */}
        <ImpactCard
          icon="🛢️" title="Crude Oil Sensitivity" category="Energy Risk"
          value={crudeVal} period={period} visible={showCrude} isRunning={isRunning}
          isCustom={cardCrude !== null}
          description="Brent crude price movement translated to COGS and freight cost exposure."
          sparkValues={crudeSpark}
          slider={
            <CardSlider
              paramLabel="Brent Crude"
              liveValue={LIVE_VALUES.crude}
              value={effectiveCrude}
              min={40} max={140} step={0.50}
              format={fmtUSD}
              isCustom={cardCrude !== null}
              onChange={(v) => setCardCrude(v)}
              onReset={() => setCardCrude(null)}
            />
          }
        />

        {/* Card 5 — MTM Impact */}
        <ImpactCard
          icon="🏛️" title="Investment MTM Impact" category="Treasury"
          value={mtmVal} period={period} visible={showGSec} isRunning={isRunning}
          isCustom={cardGSecYield !== null}
          description="G-Sec yield shift mark-to-market effect on held-to-maturity bond portfolio."
          sparkValues={mtmSpark}
          slider={
            <CardSlider
              paramLabel="G-Sec 10Y Yield"
              liveValue={LIVE_VALUES.gSecYield}
              value={effectiveGSec}
              min={5.0} max={11.0} step={0.05}
              format={fmtPct}
              isCustom={cardGSecYield !== null}
              onChange={(v) => setCardGSecYield(v)}
              onReset={() => setCardGSecYield(null)}
            />
          }
        />
      </div>
    </div>
  );
}
