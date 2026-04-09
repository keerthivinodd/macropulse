"use client";

import { useMemo } from "react";
import { useSimulationStore, LIVE_VALUES } from "@/stores/simulationStore";
import { getSectorMultipliers } from "@/lib/sectorConfig";
import { PERIOD_SCALE } from "@/lib/calcEngine";

export function TotalExposureBanner() {
  const {
    selectedSector, selectedSubIndustry, region, period,
    rateShock, fxVolatility, crudePrice,
    cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield,
  } = useSimulationStore();

  const mult  = useMemo(() => getSectorMultipliers(selectedSector), [selectedSector]);
  const scale = PERIOD_SCALE[period] ?? 1;

  const hasCustom = [cardRepoRate, cardINRRate, cardWPI, cardCrude, cardGSecYield].some((v) => v !== null);

  const effectiveRepo  = cardRepoRate  ?? (LIVE_VALUES.repoRate  + rateShock);
  const effectiveINR   = cardINRRate   ?? (LIVE_VALUES.inrRate   * (1 + fxVolatility / 100));
  const effectiveWPI   = cardWPI       ?? LIVE_VALUES.wpi;
  const effectiveCrude = cardCrude     ?? crudePrice;
  const effectiveGSec  = cardGSecYield ?? (LIVE_VALUES.gSecYield + rateShock * 0.5);

  const total = useMemo(() => {
    const borrowing = 250 * 0.65 * ((effectiveRepo - LIVE_VALUES.repoRate) / 100) * mult.rate * scale;
    const deltaINR  = Math.abs(effectiveINR - LIVE_VALUES.inrRate) / LIVE_VALUES.inrRate;
    const fx        = 12.5 * (LIVE_VALUES.inrRate / 100) * 0.35 * deltaINR * mult.fx * scale;
    const material  = 180 * 0.45 * ((effectiveWPI - LIVE_VALUES.wpi) / 100) * mult.wpi * scale;
    const crude     = 180 * 0.25 * ((effectiveCrude - LIVE_VALUES.crude) / LIVE_VALUES.crude) * mult.crude * scale;
    const mtm       = 60 * 4.2 * ((effectiveGSec - LIVE_VALUES.gSecYield) / 100);
    return borrowing + fx + material + crude + mtm;
  }, [effectiveRepo, effectiveINR, effectiveWPI, effectiveCrude, effectiveGSec, mult, scale]);

  // Base case (all live values)
  const baseTotal = useMemo(() => {
    // All values at live = zero delta everywhere
    return 0;
  }, []);

  const delta = total - baseTotal;
  const isLoss = total > 0;
  const isDeltaUp = delta > 0;

  return (
    <div className="rounded-2xl bg-[#0D1B3E]/5 border border-[#0D1B3E]/10 px-5 py-3">
      <div className="flex items-center justify-between flex-wrap gap-3">
        {/* Left: main total */}
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-semibold text-[#0D1B3E]" style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}>
            Total Exposure ({period})
          </span>
          <span className={`text-xl font-black ${isLoss ? "text-red-700" : "text-teal-700"}`}>
            ₹{Math.abs(total).toFixed(2)} Cr
          </span>
          <span className={`text-[10px] font-semibold ${isLoss ? "text-red-500" : "text-teal-600"}`}>
            {isLoss ? "▲ Net cost increase" : "▼ Net cost decrease"}
          </span>
          {hasCustom && (
            <span
              className="rounded-full bg-teal-50 border border-teal-200 px-2 py-0.5 text-xs font-semibold text-teal-700"
              style={{ fontFamily: "Calibri, 'Trebuchet MS', sans-serif" }}
            >
              Custom
            </span>
          )}
        </div>

        {/* Right: meta + delta */}
        <div className="flex items-center gap-3 text-xs text-gray-500 shrink-0 flex-wrap">
          {Math.abs(delta) > 0.001 && (
            <span className={`text-[10px] font-semibold ${isDeltaUp ? "text-red-600" : "text-teal-600"}`}>
              {isDeltaUp ? "▲" : "▼"} ₹{Math.abs(delta).toFixed(2)} Cr vs base case
            </span>
          )}
          <span>{selectedSubIndustry}</span>
          <span className="text-gray-300">·</span>
          <span>Region: {region}</span>
          <span className="text-gray-300">·</span>
          <span className="text-emerald-600 font-semibold">● live</span>
        </div>
      </div>
    </div>
  );
}
