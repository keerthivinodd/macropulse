"use client";

import { useMemo } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { LIVE_VALUES, useSimulationStore } from "@/stores/simulationStore";
import { PERIOD_SCALE } from "@/lib/calcEngine";
import { calcBorrowingImpact, calcFXImpact } from "@/lib/calcEngine";
import { getSectorMultipliers } from "@/lib/sectorConfig";

const RISK_STYLES = {
  LOW:    "bg-emerald-100 text-emerald-800 border-emerald-200",
  MEDIUM: "bg-amber-100 text-amber-800 border-amber-200",
  HIGH:   "bg-red-100 text-red-800 border-red-200",
};

interface SliderProps {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
  positiveColor?: string;
  negativeColor?: string;
}

function Slider({ label, value, min, max, step, format, onChange, positiveColor = "text-teal-600", negativeColor = "text-red-600" }: SliderProps) {
  const pct = ((value - min) / (max - min)) * 100;
  const isPositive = value >= 0;

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <span className="text-sm font-semibold text-gray-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>{label}</span>
        <span className={`text-base font-bold ${isPositive ? positiveColor : negativeColor}`}>
          {format(value)}
        </span>
      </div>
      <div className="relative">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="h-1.5 w-full cursor-pointer appearance-none rounded-full bg-gray-200 accent-[#0D1B3E] transition-all duration-150"
          style={{
            background: `linear-gradient(to right, ${
              isPositive ? "#0F6E56" : "#A32D2D"
            } 0%, ${
              isPositive ? "#0F6E56" : "#A32D2D"
            } ${pct}%, #e5e7eb ${pct}%, #e5e7eb 100%)`,
          }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[11px] text-gray-400">
        <span>{format(min)}</span>
        <span>0</span>
        <span>{format(max)}</span>
      </div>
    </div>
  );
}

export function ScenarioVariables() {
  const {
    rateShock, setRateShock,
    fxVolatility, setFxVolatility,
    crudePrice, setCrudePrice,
    selectedSector, period,
    combinedMacroOverride, setCombinedMacroOverride,
    cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield,
  } = useSimulationStore();

  const mult = useMemo(() => getSectorMultipliers(selectedSector), [selectedSector]);
  const scale = PERIOD_SCALE[period] ?? 1;

  const effectiveRepo = cardRepoRate ?? (LIVE_VALUES.repoRate + rateShock);
  const effectiveINR = cardINRRate ?? (LIVE_VALUES.inrRate * (1 + fxVolatility / 100));
  const effectiveWPI = cardWPI ?? LIVE_VALUES.wpi;
  const effectiveCrude = cardCrude ?? crudePrice;
  const effectiveGSec = cardGSecYield ?? (LIVE_VALUES.gSecYield + rateShock * 0.5);

  const totalAbsImpact = useMemo(() => {
    return (
      Math.abs(calcBorrowingImpact(effectiveRepo - LIVE_VALUES.repoRate, mult, scale)) +
      Math.abs(calcFXImpact(((effectiveINR / LIVE_VALUES.inrRate) - 1) * 100, mult, scale)) +
      Math.abs(180 * 0.45 * ((effectiveWPI - LIVE_VALUES.wpi) / 100) * mult.wpi * scale) +
      Math.abs(180 * 0.25 * ((effectiveCrude - LIVE_VALUES.crude) / LIVE_VALUES.crude) * mult.crude * scale) +
      Math.abs(60 * 4.2 * ((effectiveGSec - LIVE_VALUES.gSecYield) / 100))
    );
  }, [effectiveRepo, effectiveINR, effectiveWPI, effectiveCrude, effectiveGSec, mult, scale]);

  const borrowingImpact = useMemo(
    () => calcBorrowingImpact(effectiveRepo - LIVE_VALUES.repoRate, mult, scale),
    [effectiveRepo, mult, scale]
  );
  const fxImpact = useMemo(
    () => calcFXImpact(((effectiveINR / LIVE_VALUES.inrRate) - 1) * 100, mult, scale),
    [effectiveINR, mult, scale]
  );
  const materialImpact = useMemo(
    () => 180 * 0.45 * ((effectiveWPI - LIVE_VALUES.wpi) / 100) * mult.wpi * scale,
    [effectiveWPI, mult, scale]
  );
  const crudeImpact = useMemo(
    () => 180 * 0.25 * ((effectiveCrude - LIVE_VALUES.crude) / LIVE_VALUES.crude) * mult.crude * scale,
    [effectiveCrude, mult, scale]
  );
  const mtmImpact = useMemo(
    () => 60 * 4.2 * ((effectiveGSec - LIVE_VALUES.gSecYield) / 100),
    [effectiveGSec]
  );

  const computedPct = useMemo(() => {
    const normalized =
      ((effectiveRepo - LIVE_VALUES.repoRate) / 2.5) * 2.2 +
      ((((effectiveINR / LIVE_VALUES.inrRate) - 1) * 100) / 10) * 2.4 +
      ((effectiveWPI - LIVE_VALUES.wpi) / 4) * 1.8 +
      ((effectiveCrude - LIVE_VALUES.crude) / 25) * 2.2 +
      ((effectiveGSec - LIVE_VALUES.gSecYield) / 1.5) * 1.4;
    return Math.max(-10, Math.min(5, -normalized));
  }, [effectiveRepo, effectiveINR, effectiveWPI, effectiveCrude, effectiveGSec]);
  const riskLevel = useMemo(() => {
    const normalizedImpact =
      Math.abs(computedPct) * 0.9 +
      Math.min(4, Math.abs(borrowingImpact) / 1.5) +
      Math.min(3, Math.abs(fxImpact) / 1.2) +
      Math.min(3, Math.abs(materialImpact + crudeImpact) / 2.5) +
      Math.min(2, Math.abs(mtmImpact) / 1.5);

    if (normalizedImpact >= 8.5) return "HIGH";
    if (normalizedImpact >= 4.5) return "MEDIUM";
    return "LOW";
  }, [computedPct, borrowingImpact, fxImpact, materialImpact, crudeImpact, mtmImpact]);
  const combinedPct = combinedMacroOverride ?? computedPct;
  const sliderPct = ((combinedPct - (-10)) / (5 - (-10))) * 100;
  const isManualOverride = combinedMacroOverride !== null;

  const scenarioTakeaways = useMemo(() => {
    const periodLabel = period === "YTD" ? "FY" : period;
    const repoLevel = effectiveRepo;
    const inrLevel = effectiveINR;
    const crudeDelta = effectiveCrude - LIVE_VALUES.crude;
    const wpiDelta = effectiveWPI - LIVE_VALUES.wpi;
    const gsecDelta = effectiveGSec - LIVE_VALUES.gSecYield;

    const repoText =
      `${repoLevel.toFixed(2)}% repo (${repoLevel - LIVE_VALUES.repoRate >= 0 ? "+" : ""}${(repoLevel - LIVE_VALUES.repoRate).toFixed(2)} pts vs live)`;
    const fxText =
      `USD/INR ${inrLevel.toFixed(2)} (${(((inrLevel / LIVE_VALUES.inrRate) - 1) * 100) >= 0 ? "+" : ""}${(((inrLevel / LIVE_VALUES.inrRate) - 1) * 100).toFixed(1)}% vs live)`;
    const wpiText =
      `WPI ${effectiveWPI.toFixed(2)}% (${wpiDelta >= 0 ? "+" : ""}${wpiDelta.toFixed(2)} pts vs live)`;
    const crudeText =
      `Brent at $${effectiveCrude.toFixed(1)} (${crudeDelta >= 0 ? "+" : ""}${crudeDelta.toFixed(1)} vs live)`;
    const gsecText =
      `10Y G-Sec ${effectiveGSec.toFixed(2)}% (${gsecDelta >= 0 ? "+" : ""}${gsecDelta.toFixed(2)} pts vs live)`;

    const marginDirection = combinedPct <= 0 ? "Margin pressure" : "Margin support";
    const impactParts = [
      `Borrowing impact: Rs ${borrowingImpact.toFixed(2)} Cr`,
      `FX impact: Rs ${fxImpact.toFixed(2)} Cr`,
      `Material inflation impact: Rs ${materialImpact.toFixed(2)} Cr`,
      `Crude impact: Rs ${crudeImpact.toFixed(2)} Cr`,
      `Treasury MTM impact: Rs ${mtmImpact.toFixed(2)} Cr`,
    ];

    const actionText =
      riskLevel === "HIGH"
        ? "CFO action: trigger hedge, liquidity, and procurement review now."
        : riskLevel === "MEDIUM"
          ? "CFO action: review exposures in the next planning cycle."
          : "CFO action: monitor, but no immediate intervention is required.";

    return [
      `${periodLabel} outlook: ${marginDirection}.`,
      `Macro setup: ${repoText}, ${fxText}, ${wpiText}, ${crudeText}, ${gsecText}.`,
      ...impactParts,
      actionText,
    ];
  }, [period, combinedPct, borrowingImpact, fxImpact, materialImpact, crudeImpact, mtmImpact, effectiveRepo, effectiveINR, effectiveWPI, effectiveCrude, effectiveGSec, riskLevel]);

  return (
    <div className="flex flex-col gap-5 self-start rounded-2xl border border-gray-100 bg-white p-5 shadow-sm xl:p-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900">Scenario Variables</h3>
          <p className="mt-1 text-sm text-gray-500">Dynamic Macro Drivers</p>
        </div>
        <span className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-bold ${RISK_STYLES[riskLevel]}`}>
          {riskLevel === "HIGH" || riskLevel === "MEDIUM"
            ? <AlertTriangle className="h-3 w-3" />
            : <RefreshCw className="h-3 w-3" />
          }
          {riskLevel} RISK
        </span>
      </div>

      {/* Sliders */}
      <Slider
        label="Interest Rate Shock"
        value={rateShock}
        min={-5}
        max={5}
        step={0.1}
        format={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
        onChange={setRateShock}
        positiveColor="text-red-600"
        negativeColor="text-teal-600"
      />

      <Slider
        label="USD/INR FX Volatility"
        value={fxVolatility}
        min={-15}
        max={5}
        step={0.1}
        format={(v) => `${v >= 0 ? "+" : ""}${v.toFixed(1)}%`}
        onChange={setFxVolatility}
        positiveColor="text-teal-600"
        negativeColor="text-red-600"
      />

      {/* Crude input */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <span className="text-sm font-semibold text-gray-500" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>Brent Crude Oil ($/BBL)</span>
          <span className={`text-base font-bold ${crudePrice > 110 ? "text-red-600" : crudePrice < 60 ? "text-amber-600" : "text-gray-700"}`}>
            ${crudePrice.toFixed(1)}
          </span>
        </div>
        <input
          type="number"
          min={50}
          max={150}
          step={0.5}
          value={crudePrice}
          onChange={(e) => {
            const v = parseFloat(e.target.value);
            if (!isNaN(v)) setCrudePrice(Math.max(50, Math.min(150, v)));
          }}
          className="w-full rounded-xl border border-gray-200 bg-gray-50/60 px-4 py-2.5 text-base font-bold text-gray-800 transition focus:outline-none focus:ring-2 focus:ring-[#0D1B3E]"
        />
      </div>

      {/* Combined macro impact — interactive slider */}
      <div className={`rounded-2xl border p-4 transition-colors ${
        isManualOverride
          ? "border-amber-200 bg-gradient-to-br from-amber-50 to-white"
          : "border-teal-100 bg-gradient-to-br from-[#E1F5EE] to-white"
      }`}>
        <div className="mb-3 flex items-start justify-between gap-2">
          <div>
            <p
              className={`text-sm font-semibold ${isManualOverride ? "text-amber-700" : "text-teal-700"}`}
              style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
            >
              Combined Macro Impact
            </p>
            <p className="mt-0.5 text-xs text-gray-500">INR vs USD/AED + Oil Sensitivity</p>
          </div>
          <div className="flex flex-col items-end gap-1">
              <span className={`rounded-full px-2.5 py-1 text-sm font-bold ${
              combinedPct >= 0 ? "bg-teal-100 text-teal-700" : "bg-red-100 text-red-700"
            }`}>
              {combinedPct >= 0 ? "+" : ""}{combinedPct.toFixed(1)}%
            </span>
            {isManualOverride && (
              <span
                className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700"
                style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
              >
                Manual
              </span>
            )}
          </div>
        </div>

        {/* Actual range slider */}
        <div className="relative mt-1">
          {/* Neutral tick mark */}
          <div
            className="pointer-events-none absolute top-0 bottom-0 flex flex-col items-center"
            style={{ left: `${((0 - (-10)) / (5 - (-10))) * 100}%`, transform: "translateX(-50%)" }}
          >
            <div className="mt-3 h-3 w-0.5 rounded-full bg-gray-400 opacity-50" />
          </div>

          <input
            type="range"
            min={-10}
            max={5}
            step={0.1}
            value={combinedPct}
            onChange={(e) => setCombinedMacroOverride(parseFloat(e.target.value))}
            className="relative h-1.5 w-full cursor-pointer appearance-none rounded-full transition-all duration-150"
            style={{
              background: (() => {
                const neutralPct = ((0 - (-10)) / (5 - (-10))) * 100;
                const lo = Math.min(sliderPct, neutralPct);
                const hi = Math.max(sliderPct, neutralPct);
                const fill = combinedPct >= 0 ? "#0F6E56" : "#ef4444";
                return `linear-gradient(to right, #d1d5db 0%, #d1d5db ${lo}%, ${fill} ${lo}%, ${fill} ${hi}%, #d1d5db ${hi}%, #d1d5db 100%)`;
              })(),
            }}
          />
        </div>

        <div className="mt-1 flex justify-between text-[11px] text-gray-400">
          <span>-10%</span>
          <span>Neutral 0%</span>
          <span>+5%</span>
        </div>

        {isManualOverride && (
          <button
            onClick={() => setCombinedMacroOverride(null)}
            className="mt-2 text-[11px] font-semibold text-teal-600 transition hover:text-teal-800"
          >
            ↺ Reset to computed ({computedPct.toFixed(1)}%)
          </button>
        )}
      </div>

      {/* Scenario takeaway */}
      <div className="rounded-xl border-l-4 border-teal-400 bg-[#E1F5EE] px-4 py-3">
        <p
          className="text-sm font-semibold tracking-[0.08em] text-[#0D1B3E]"
          style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
        >
          Scenario Takeaway
        </p>
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm leading-6 text-gray-700">
          {scenarioTakeaways.map((point) => (
            <li key={point}>{point}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
