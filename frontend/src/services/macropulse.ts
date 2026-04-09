import api from "./api";
import type {
  AgentMetrics,
  AlertResponse,
  CFOBriefPipelineResult,
  CostRoutingStatus,
  EventLogEntry,
  GuardrailViolation,
  HITLPendingAlert,
  MacroPulseAgentQueryResponse,
  MacroPulseAgentSource,
  MacroPulseDashboard,
  MacroPulseRealtimeResponse,
  SensitivityResponse,
  TenantProfile,
} from "@/types/macropulse";

const BASE = "/api/v1/macropulse";
const BASE_API = "/api";

export async function getMacroPulseRealtime(): Promise<MacroPulseRealtimeResponse> {
  const { data } = await api.get<MacroPulseRealtimeResponse>(`${BASE}/realtime`);
  return data;
}

export function buildDefaultTenantProfile(tenantId: string): TenantProfile {
  return {
    tenant_id: tenantId,
    company_name: "Fidelis Demo Manufacturing",
    primary_region: "IN",
    primary_currency: "INR",
    debt: {
      total_loan_amount_cr: 100,
      rate_type: "Floating",
      current_effective_rate_pct: 9.5,
      floating_proportion_pct: 65,
      short_term_debt_cr: 30,
      long_term_debt_cr: 70,
    },
    fx: {
      net_usd_exposure_m: 45,
      net_aed_exposure_m: 10,
      net_sar_exposure_m: 5,
      hedge_ratio_pct: 65,
      hedge_instrument: "Forward",
    },
    cogs: {
      total_cogs_cr: 100,
      steel_pct: 20,
      petroleum_pct: 30,
      electronics_pct: 15,
      freight_pct: 10,
      other_pct: 25,
    },
    portfolio: {
      gsec_holdings_cr: 50,
      modified_duration: 4,
    },
    logistics: {
      primary_routes: ["Mumbai-Dubai", "Chennai-Jebel Ali"],
      monthly_shipment_value_cr: 10,
      inventory_buffer_days: 30,
    },
    notification_config: {
      email: "cfo@fidelis-demo.com",
      channels: ["email"],
    },
  };
}

export async function getMacroPulseDashboard(tenantId: string): Promise<MacroPulseDashboard> {
  const { data } = await api.get<MacroPulseDashboard>(`${BASE}/dashboard/${tenantId}`);
  return data;
}

export async function getTenantProfile(tenantId: string): Promise<TenantProfile> {
  const response = await fetch(`${BASE_API}/tenant/profile/${tenantId}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw Object.assign(new Error(detail?.detail ?? "Unable to load tenant profile."), {
      response: { status: response.status },
    });
  }

  return (await response.json()) as TenantProfile;
}

export async function upsertTenantProfile(profile: TenantProfile): Promise<TenantProfile> {
  const response = await fetch(`${BASE_API}/tenant/profile`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Write-Region": profile.primary_region === "IN" ? "IN" : "UAE",
    },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unable to save tenant profile.");
  }

  return (await response.json()) as TenantProfile;
}

export async function updateTenantProfile(profile: TenantProfile): Promise<TenantProfile> {
  const response = await fetch(`${BASE_API}/tenant/profile/${profile.tenant_id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Write-Region": profile.primary_region === "IN" ? "IN" : "UAE",
    },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unable to update tenant profile.");
  }

  return (await response.json()) as TenantProfile;
}

export async function ensureTenantProfile(tenantId: string): Promise<TenantProfile> {
  try {
    return await getTenantProfile(tenantId);
  } catch (error) {
    const status = (error as { response?: { status?: number } }).response?.status;
    if (status !== 404) {
      throw error;
    }
    return upsertTenantProfile(buildDefaultTenantProfile(tenantId));
  }
}

export async function getSensitivity(tenantId: string): Promise<SensitivityResponse> {
  const response = await fetch(`${BASE_API}/tenant/profile/${tenantId}/sensitivity`, {
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? "Unable to load sensitivity matrix.");
  }

  return (await response.json()) as SensitivityResponse;
}

export async function getHitlPending(tenantId?: string): Promise<HITLPendingAlert[]> {
  const suffix = tenantId ? `/pending/${tenantId}` : "/pending";
  const { data } = await api.get<HITLPendingAlert[]>(`${BASE_API}/hitl${suffix}`);
  return data;
}

export async function approveHitl(alertId: string, reviewer: string, notes: string): Promise<AlertResponse> {
  const { data } = await api.post<AlertResponse>(`${BASE_API}/hitl/${alertId}/approve`, {
    reviewer,
    notes,
  });
  return data;
}

export async function rejectHitl(
  alertId: string,
  reviewer: string,
  notes: string,
  reason: string
): Promise<AlertResponse> {
  const { data } = await api.post<AlertResponse>(`${BASE_API}/hitl/${alertId}/reject`, {
    reviewer,
    notes,
    reason,
  });
  return data;
}

export async function getGuardrailViolations(tenantId: string): Promise<GuardrailViolation[]> {
  const { data } = await api.get<GuardrailViolation[]>(`${BASE_API}/guardrails/violations/${tenantId}`);
  return data;
}

// ── Live market constants (mirrored from simulationStore) ────────────────────
const LV = { repoRate: 6.50, inrRate: 84.20, wpi: 5.10, crude: 87.50, gSecYield: 7.20 };

// ── Conversation turn passed in for context ───────────────────────────────────
export type ConversationTurn = { role: "user" | "agent"; content: string };

// ── Levenshtein distance (for typo tolerance) ────────────────────────────────
function lev(a: string, b: string): number {
  if (a === b) return 0;
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;
  const dp: number[] = Array.from({ length: b.length + 1 }, (_, i) => i);
  for (let i = 1; i <= a.length; i++) {
    let prev = i;
    for (let j = 1; j <= b.length; j++) {
      const cur = a[i - 1] === b[j - 1] ? dp[j - 1] : 1 + Math.min(dp[j - 1], dp[j], prev);
      dp[j - 1] = prev;
      prev = cur;
    }
    dp[b.length] = prev;
  }
  return dp[b.length];
}

// Returns true if any word in the query is "close enough" to the keyword
// Tolerance: 1 edit for short words (≤5 chars), 2 edits for longer ones
function fuzzyMatch(queryWords: string[], keyword: string): boolean {
  const kwWords = keyword.split(" ");
  return kwWords.every((kw) =>
    queryWords.some((qw) => {
      if (qw === kw) return true;
      if (qw.includes(kw) || kw.includes(qw)) return true;
      // Only apply edit-distance to words long enough to avoid false matches
      // e.g. "if"(2) must not match "is", "in", "it" etc.
      if (kw.length < 4 || qw.length < 4) return false;
      const tol = kw.length <= 6 ? 1 : 2;
      return lev(qw, kw) <= tol;
    })
  );
}

// ── Score helper — count how many keywords a query fuzzy-matches ─────────────
function score(q: string, keywords: string[]): number {
  const qWords = q.split(/\s+/).filter(Boolean);
  return keywords.reduce((n, k) => n + (q.includes(k) || fuzzyMatch(qWords, k) ? 1 : 0), 0);
}

// ── Extract the last agent response text from history for follow-up context ──
function lastAgentContent(history: ConversationTurn[]): string {
  for (let i = history.length - 1; i >= 0; i--) {
    if (history[i].role === "agent") return history[i].content.toLowerCase();
  }
  return "";
}

function buildMockAgentResponse(
  text: string,
  history: ConversationTurn[] = [],
  _depth = 0
): MacroPulseAgentQueryResponse {
  // Hard recursion guard — should never be needed after the fuzzy fix, but safety net
  if (_depth > 2) return {
    query_type: "overview", confidence: 80, publish_status: "review",
    impact: `## Macro Overview\n\nCurrent environment: RBI repo **${LV.repoRate}%**, USD/INR **₹${LV.inrRate}**, Brent **$${LV.crude}/bbl**, WPI **${LV.wpi}%**, G-Sec **${LV.gSecYield}%**.\n\nCombined macro headwind for FY26: **₹14.2 Cr**. Top risks: FX (₹7.2 Cr) and commodity inflation (₹8.4 Cr).`,
    recommended_action: "Ask me about a specific variable — rates, FX, crude oil, or bonds.",
    regional_context: "India: Macro stable. GCC: Stable peg. Global: Fed on hold.",
    sources: [], scenario_output: {}, analytics: {},
  };
  const q = text.toLowerCase().trim();
  const prev = lastAgentContent(history);

  // ── Is this a "what is X" / "explain X" concept question? ──────────────
  const isConceptQ = /^(what is |what are |explain |define |how does |how do |what does )/.test(q);

  // ── Scoring by category ──────────────────────────────────────────────────
  const s = {
    // identity only fires when the question is specifically about MacroPulse itself
    identity  : score(q, ["what is macropulse", "what are you", "who are you", "tell me about macropulse", "what can you do", "how do you work", "about macropulse", "explain macropulse", "macropulse agent", "intelli stream"]),
    greeting  : score(q, ["hello", "hi ", "hey", "good morning", "good afternoon", "good evening", "howdy", "greetings"]),
    followup  : score(q, ["more", "elaborate", "explain more", "tell me more", "continue", "go on", "what do you mean", "clarify", "expand", "detail"]),
    whatif    : score(q, ["what if", "what will happen if", "scenario", "simulate", "suppose", "hypothetical", "assume", "if repo", "if crude", "if usd", "if inr", "if rate", "best case", "worst case", "upside", "downside", "what happens if", "increases to", "drops to", "falls to", "rises to"]),
    repo      : score(q, ["repo", "rbi", "mpc", "monetary policy", "policy rate", "reverse repo", "sdf", "msf", "crr", "slr", "rate cut", "rate hike", "basis point", "bps"]),
    emi       : score(q, ["emi", "loan", "floating rate", "fixed rate", "borrowing cost", "interest cost", "debt service", "interest payment", "refinance"]),
    fx        : score(q, ["forex", "usd/inr", "dollar", "rupee", "currency", "aed", "sar", "dxy", "depreciation", "appreciation", "exchange rate"]),
    hedging   : score(q, ["hedge", "hedging", "forward contract", "option", "swap", "derivative", "collar", "natural hedge", "hedge ratio"]),
    crude     : score(q, ["crude", "brent", "crude oil", "wti", "opec", "petroleum", "barrel", "energy"]),
    commodity : score(q, ["commodity", "steel", "copper", "gold", "aluminium", "coal", "freight", "shipping", "supply chain", "raw material", "input cost", "wpi", "inflation", "ppi"]),
    gsec      : score(q, ["g-sec", "gsec", "government bond", "treasury", "10y yield", "duration", "mtm", "mark to market", "bond yield"]),
    gdp       : score(q, ["gdp", "economic growth", "recession", "slowdown", "gva", "iip"]),
    fed       : score(q, ["federal reserve", "fomc", "us rate", "powell", "ffr", "us bond", "us treasury"]),
    margin    : score(q, ["ebitda", "profit", "cogs", "operating cost", "gross margin", "net margin", "earnings"]),
    risk      : score(q, ["risk", "var", "value at risk", "stress test", "worst case", "tail risk", "scenario analysis"]),
    cfo       : score(q, ["cfo", "board", "brief", "executive", "quarterly report", "q1", "q2", "q3", "q4", "fy26", "annual"]),
    // explain scores higher when combined with a known concept keyword
    explain   : score(q, ["what is", "define", "explain", "meaning of", "how does", "how do", "what does", "difference between"]) +
                (isConceptQ ? score(q, ["repo rate", "wpi", "g-sec", "gsec", "mtm", "forward contract", "hedge", "ebitda", "cogs", "duration", "dxy", "opec", "crude oil", "inflation", "bond", "yield", "rbi", "mpc", "forex", "inr"]) : 0),
    workingcap: score(q, ["working capital", "cash flow", "liquidity", "current ratio", "receivable", "payable", "inventory", "cash conversion"]),
  };

  // ── Detect dominant topic ────────────────────────────────────────────────
  type Topic = keyof typeof s;
  const sorted = (Object.keys(s) as Topic[]).sort((a, b) => s[b] - s[a]);
  const top = sorted[0];
  const topScore = s[top];

  // ── Follow-up: if query is very short and ambiguous, use previous context ─
  const isFollowUp = q.split(" ").length <= 6 && (s.followup > 0 || q.match(/^(it|that|this|so|and|but|why|how|when|what about)/));
  const contextTopic = isFollowUp && prev
    ? prev.includes("repo") || prev.includes("rate") ? "repo"
    : prev.includes("fx") || prev.includes("usd") || prev.includes("inr") ? "fx"
    : prev.includes("crude") || prev.includes("oil") ? "crude"
    : prev.includes("g-sec") || prev.includes("yield") || prev.includes("bond") ? "gsec"
    : prev.includes("inflation") || prev.includes("wpi") || prev.includes("cpi") ? "commodity"
    : prev.includes("hedge") ? "hedging"
    : top
    : top;

  let effectiveTopic: Topic = topScore === 0 ? (isFollowUp ? contextTopic : "identity") : contextTopic;

  // ── "what is X?" with no other strong signal → force explain ─────────────
  if (isConceptQ && s.explain >= 2 && effectiveTopic !== "greeting" && effectiveTopic !== "identity") {
    effectiveTopic = "explain";
  }

  // ── whatif: redirect to the relevant topic handler (no recursion) ────────
  if (effectiveTopic === "whatif") {
    if (q.includes("repo") || q.includes("rate")) effectiveTopic = "repo";
    else if (q.includes("crude") || q.includes("oil") || q.includes("brent") || q.includes("barrel")) effectiveTopic = "crude";
    else if (q.includes("usd") || q.includes("inr") || q.includes("fx") || q.includes("rupee") || q.includes("dollar")) effectiveTopic = "fx";
    else if (q.includes("yield") || q.includes("gsec") || q.includes("bond") || q.includes("g-sec")) effectiveTopic = "gsec";
    else effectiveTopic = "risk"; // combined / best-case / worst-case / generic scenario
  }

  // ── Build response by topic ──────────────────────────────────────────────
  interface AgentReply { impact: string; action: string; regional: string; query_type: MacroPulseAgentQueryResponse["query_type"]; confidence: number; sources: MacroPulseAgentSource[] }

  const SOURCES_RBI: MacroPulseAgentSource[] = [
    { name: "RBI Monetary Policy Committee", detail: "Latest MPC resolution, Feb 2026 — repo held at 6.50%", category: "official" },
    { name: "RBI Weekly Statistical Supplement", detail: "Reserve money, forex reserves, liquidity data", category: "official" },
  ];
  const SOURCES_FX: MacroPulseAgentSource[] = [
    { name: "Bloomberg FX Terminal", detail: "USD/INR spot, forwards, options vol surface", category: "market" },
    { name: "RBI Reference Rate", detail: "Daily official fixing rate — ₹84.20", category: "official" },
  ];
  const SOURCES_CRUDE: MacroPulseAgentSource[] = [
    { name: "ICE Brent Futures", detail: "Front-month Brent at $87.5/bbl", category: "market" },
    { name: "PPAC India Petroleum", detail: "Domestic fuel price revision schedule", category: "official" },
    { name: "OPEC+ Supply Tracker", detail: "Current production quotas and compliance rate", category: "news" },
  ];
  const SOURCES_MACRO: MacroPulseAgentSource[] = [
    { name: "MOSPI GDP & WPI Release", detail: "Q3 FY26 advance estimate — 7.2% growth", category: "official" },
    { name: "Bloomberg Economics", detail: "India macro outlook and consensus forecasts", category: "market" },
    { name: "IMF World Economic Outlook", detail: "Global growth projections, Apr 2026 update", category: "official" },
  ];
  const SOURCES_GSEC: MacroPulseAgentSource[] = [
    { name: "CCIL Bond Clearing", detail: "10Y G-Sec yield: 7.20%, modified duration 4.2", category: "market" },
    { name: "RBI OMO Calendar", detail: "Open market operations schedule for H2 FY26", category: "official" },
  ];

  const reply = ((): AgentReply => {
    switch (effectiveTopic) {

      case "greeting":
        return {
          query_type: "overview", confidence: 100,
          impact: "## Hello! 👋\n\nI'm **MacroPulse Agent** — your AI macroeconomic intelligence layer for India and GCC markets.\n\n### What I'm tracking right now\n- **RBI Repo Rate**: 6.50% (hold) — next MPC: June 2026\n- **USD/INR**: ₹84.20 — near RBI's intervention ceiling\n- **Brent Crude**: $87.5/bbl — OPEC+ supporting floor at $80\n- **WPI Inflation**: 5.1% — above neutral, compressing COGS\n- **10Y G-Sec Yield**: 7.20% — stable, rate cut upside ahead\n\n### What I can do\n- **Analyse** your FX, rate, and commodity exposure\n- **Run scenarios** — \"what if crude hits $100?\"\n- **Explain** any financial or macro concept\n- **Generate** CFO briefs and risk summaries\n- **Answer** any macro or finance question\n\nWhat would you like to explore?",
          action: "**Try asking:**\n- What's the impact of a 50 bps RBI rate cut on our loan book?\n- Run a worst-case crude oil scenario for Q4 margins.\n- Generate a CFO brief for this week.",
          regional: "India: Macro stable, RBI in hold-then-ease mode. GCC: Stable peg. Global: Fed pivot narrative intact.",
          sources: [],
        };

      case "identity":
        return {
          query_type: "overview", confidence: 100,
          impact: "## MacroPulse — AI Macroeconomic Intelligence\n\nMacroPulse is a **real-time macro risk platform** built for CFOs, treasurers, and finance teams operating across **India and the GCC**.\n\n### The Problem It Solves\nEvery day, five macro variables silently erode your P&L — interest rates, FX, oil prices, inflation, and bond yields. Most businesses only discover the damage at quarter-end. MacroPulse makes it visible in real time.\n\n### Five Variables, One Platform\n| Variable | Current | Your Exposure |\n|---|---|---|\n| RBI Repo Rate | 6.50% | ₹162.5 Cr floating debt |\n| USD/INR | ₹84.20 | $4.4M unhedged |\n| Brent Crude | $87.5/bbl | 30% of COGS |\n| WPI Inflation | 5.1% | ₹180 Cr COGS base |\n| G-Sec 10Y Yield | 7.20% | ₹60 Cr portfolio |\n\n### Platform Modules\n1. **Real-Time Monitoring** — live dashboards with configurable alert thresholds\n2. **Simulation Impact** — drag any macro variable and instantly see P&L delta\n3. **MacroPulse Agent** — conversational AI for deep analysis and CFO briefs *(you're here)*\n4. **System Configuration** — customise your debt, FX, and COGS profile\n\nAsk me anything — I'm built to answer.",
          action: "**Get started by asking:**\n- Explain the FX impact on our unhedged USD book\n- What's my repo rate sensitivity?\n- Generate a CFO brief for this week",
          regional: "Covering India (IN), UAE, and Saudi Arabia macro environments.",
          sources: [],
        };

      case "repo":
      case "emi": {
        const whatIfRate = q.match(/(\d+(\.\d+)?)\s*(%|percent|bps|basis)/);
        if (whatIfRate || s.whatif > 0) {
          const newRate = whatIfRate ? parseFloat(whatIfRate[1]) : LV.repoRate + 0.25;
          const delta = newRate > 10 ? newRate / 100 - LV.repoRate / 100 : (newRate - LV.repoRate) / 100;
          const annualImpact = (250 * 0.65 * delta * 100).toFixed(2);
          const emiImpact = (250 * 0.65 * delta * 1000 / 12).toFixed(0);
          return {
            query_type: "interest_rate", confidence: 91,
            impact: `## Rate Scenario: Repo at ${newRate > 10 ? newRate + " bps above current" : newRate + "%"}\n\nWith your ₹250 Cr floating rate debt book (65% floating = ₹162.5 Cr):\n\n### Direct Impact\n- **Annual interest cost change**: ₹${annualImpact} Cr ${delta > 0 ? "increase" : "decrease"}\n- **Monthly EMI change**: ~₹${Math.abs(parseInt(emiImpact)).toLocaleString()}/Cr per month\n- **Per ₹1 Cr outstanding**: ₹${(Math.abs(delta) * 10000).toFixed(0)}/month\n\n### Context\nCurrent RBI repo: **${LV.repoRate}%** (held Feb 2026 MPC). RBI forward guidance suggests a potential **25–50 bps cumulative cut** in H2 FY26 if CPI sustains below 4.5%.`,
            action: delta > 0
              ? "**Protect against rate hike:**\n- Convert 40% of floating book to fixed-rate swaps at 7.2%\n- Prepay short-term paper (₹30 Cr tranche) now\n- Set rate alert at 6.75% for early warning"
              : "**Capitalise on rate reduction:**\n- Maintain floating rate exposure to benefit from cuts\n- Refinance any fixed-rate debt above 8.5%\n- Consider extending loan tenors at current rates",
            regional: `RBI MPC: Repo ${LV.repoRate}%, SDF ${LV.repoRate - 0.25}%, MSF ${LV.repoRate + 0.25}%. Liquidity surplus ₹1.2 Lakh Cr. CPI at 4.85%, within target. Next MPC: June 2026.`,
            sources: SOURCES_RBI,
          };
        }
        return {
          query_type: "interest_rate", confidence: 88,
          impact: `## Interest Rate Analysis\n\nRBI held the repo rate at **${LV.repoRate}%** in the Feb 2026 MPC meeting, with a neutral stance. Here's the direct impact on your business:\n\n### Your Debt Profile\n- **Total debt**: ₹250 Cr | Floating: ₹162.5 Cr (65%) | Fixed: ₹87.5 Cr (35%)\n- **Current effective rate**: ~9.5% all-in (RLLR-linked)\n- **Annual interest outgo**: ~₹23.8 Cr\n\n### Rate Sensitivity\n- **25 bps cut** → saves ₹1.02 Cr/year | EMI drops ₹8,500/Cr\n- **50 bps cut** → saves ₹2.03 Cr/year\n- **25 bps hike** → adds ₹1.63 Cr/year cost\n\n### Outlook\nRBI's forward guidance signals a **hold-then-cut cycle** in H2 FY26. First rate cut expected around **Aug–Oct 2026**, contingent on CPI sustaining below 4.5% for two consecutive quarters. Liquidity surplus stands at ₹1.2 Lakh Cr — no tightening expected.`,
          action: "**Immediate (this week)**\n- No rate action required — hold current floating exposure\n- Set repo rate alert at **6.25%** as early cut signal\n\n**Short-term (30 days)**\n- Review fixed vs floating mix (65:35 is slightly aggressive for neutral outlook)\n- Consider interest rate swap on ₹50 Cr of floating book as cost hedge\n- Short-term paper (₹30 Cr) maturing in Q2 — plan refinancing window",
          regional: `India: RBI repo ${LV.repoRate}%, CPI 4.85%, core inflation 4.2%. Liquidity: ₹1.2L Cr surplus. Fed funds at 5.25% — India-US rate differential at 125 bps, supportive of INR. SDF ${LV.repoRate - 0.25}%, 91-day T-Bill at 6.65%.`,
          sources: SOURCES_RBI,
        };
      }

      case "fx":
      case "hedging": {
        const whatIfFX = q.match(/(\d{2,3}(\.\d+)?)\s*(inr|rupee|₹)?/);
        if ((s.whatif > 0 || q.includes("depreciat") || q.includes("appreciat")) && whatIfFX) {
          const newRate = parseFloat(whatIfFX[1]);
          const delta = newRate - LV.inrRate;
          const unhedgedUSD = 12.5 * (1 - 0.65); // $M unhedged
          const impact = (unhedgedUSD * Math.abs(delta)).toFixed(1);
          return {
            query_type: "fx", confidence: 87,
            impact: `## FX Scenario: USD/INR at ₹${newRate}\n\nMove of ${delta > 0 ? "+" : ""}${delta.toFixed(1)} from current ₹${LV.inrRate}.\n\n### Exposure Impact\n- **Net USD exposure**: $12.5M | Hedged 65% ($8.1M) | Unhedged $4.4M\n- **P&L impact on unhedged leg**: ₹${impact} Cr ${delta > 0 ? "additional cost" : "cost saving"}\n- **Hedged leg**: No impact — locked via forwards at ₹${(LV.inrRate + 0.65).toFixed(2)}\n- **AED/SAR**: Stable (GCC peg maintained)\n- **Working capital**: ${delta > 0 ? "Payables increase, receivables unchanged" : "Receivables increase, payables decrease"}\n\n### vs Budget\nAt ₹${newRate}, total FX impact vs ₹82 budget = **₹${((newRate - 82) * 12.5 * 0.35).toFixed(1)} Cr adverse**.`,
            action: delta > 0
              ? "**INR depreciation — act now:**\n- Increase hedge ratio to 85% using forward contracts immediately\n- Accelerate USD receivable collections\n- Defer non-critical USD payables"
              : "**INR appreciation — optimise:**\n- Delay forward contract rollovers to benefit from better rates\n- Lock AED/SAR forwards for Q3 at current levels",
            regional: `Current: USD/INR ₹${LV.inrRate}. RBI corridor: ₹82–86 (informal). Forex reserves $645 Bn (14 months import cover). DXY 104.2. INR 1Y forward ₹${(LV.inrRate + 2.1).toFixed(2)}.`,
            sources: SOURCES_FX,
          };
        }
        return {
          query_type: "fx", confidence: 85,
          impact: `## FX & Currency Risk\n\nUSD/INR is trading at **₹${LV.inrRate}**, near the upper end of RBI's informal intervention corridor (₹82–86).\n\n### Your FX Exposure\n- **Gross USD exposure**: $12.5M | **Hedged**: $8.1M (65%) | **Open**: $4.4M\n- **3M forward rate**: ₹${(LV.inrRate + 0.65).toFixed(2)} (forward points: +65 paise)\n- **AED/SAR**: Pegged to USD — no FX risk\n\n### Downside Scenarios\n- **1% INR depreciation** → ₹3.7 Cr loss on unhedged leg\n- **2% INR depreciation** (to ₹86) → ₹7.4 Cr impact\n- **INR to ₹88** (stress) → ₹16.1 Cr total exposure\n\n### Drivers to Watch\n- **DXY** at 104.2 — high USD index = pressure on EM currencies\n- **RBI intervention**: Defending ₹84.50 ceiling actively\n- **Forex reserves**: $645 Bn (14 months import cover) — strong buffer`,
          action: "**Immediate (this week)**\n- Increase USD hedge ratio from 65% → 80% — covers $1.9M additional exposure\n- Use 3-month rolling forwards at current rate ₹${(LV.inrRate + 0.65).toFixed(2)}\n\n**Short-term (30 days)**\n- Review AED/SAR — no hedging needed given peg stability\n- Natural hedge: match USD receivable timing with USD payables to reduce gross exposure\n- Set DXY > 105 as an accelerated hedging trigger",
          regional: `India: RBI forex reserves $645 Bn. INR 1Y implied vol 4.2%. UAE/SA: USD peg rock solid, no devaluation risk. Global: DXY at 104.2, EUR/USD 1.087, GBP/USD 1.265.`,
          sources: SOURCES_FX,
        };
      }

      case "crude":
      case "commodity": {
        const whatIfCrude = q.match(/\$(\d+(\.\d+)?)/);
        if (s.whatif > 0 && whatIfCrude) {
          const newCrude = parseFloat(whatIfCrude[1]);
          const delta = newCrude - LV.crude;
          const impact = (180 * 0.25 * (delta / LV.crude)).toFixed(2);
          return {
            query_type: "commodity", confidence: 84,
            impact: `## Crude Scenario: Brent at $${newCrude}/bbl\n\nMove of ${delta > 0 ? "+" : ""}$${delta.toFixed(1)} from current $${LV.crude}/bbl.\n\n### COGS Impact\n- **Petroleum COGS change**: ₹${Math.abs(parseFloat(impact)).toFixed(2)} Cr ${delta > 0 ? "increase" : "decrease"} (petroleum = 30% of ₹180 Cr COGS)\n- **Freight surcharges**: ${delta > 0 ? "+" : ""}₹${(Math.abs(delta) * 0.08).toFixed(2)} Cr (logistics cost escalation)\n- **Gross margin compression**: ${(Math.abs(parseFloat(impact)) / 180 * 100).toFixed(1)} bps\n- **Annualised total impact**: ₹${(Math.abs(parseFloat(impact)) * 4).toFixed(1)} Cr\n\n### Risk Level\nAt $${newCrude}/bbl: **${newCrude > 100 ? "🔴 Severe — activate procurement contingency plan" : newCrude > 90 ? "🟡 Elevated — accelerate forward buying" : "🟢 Manageable — standard procurement applies"}**`,
            action: delta > 0
              ? `**Protect COGS now:**\n- Forward-buy 40% of Q${new Date().getMonth() < 3 ? 1 : new Date().getMonth() < 6 ? 2 : new Date().getMonth() < 9 ? 3 : 4} petroleum requirement now\n- Renegotiate freight contracts with fuel surcharge cap\n- Pass through 50–60% of cost increase via product pricing`
              : "**Capture cost reduction:**\n- Opportunity to build inventory at lower cost\n- Lock 6-month supply contracts at spot rates\n- Defer commodity hedges to benefit from lower spot prices",
            regional: `India: Domestic fuel prices adjusted quarterly. PPAC formula-linked. WPI energy component at 6.8%. OPEC+ production cut 2.2 Mbpd through Q2 2026. UAE/SA: GCC producers benefit; no cost impact.`,
            sources: SOURCES_CRUDE,
          };
        }
        const isWPI = q.includes("wpi") || q.includes("inflation") || q.includes("cpi");
        return {
          query_type: "commodity", confidence: 82,
          impact: isWPI
            ? `## WPI Inflation & Input Cost Impact\n\nWPI stands at **${LV.wpi}%** YoY as of Feb 2026 — compounding input cost pressure across your COGS base.\n\n### Key Commodity Movements\n- **Manufacturing WPI**: 4.8% — directly hits your input costs\n- **Steel**: ₹58,000/MT (+3% MoM) — 20% of COGS (₹36 Cr)\n- **Petroleum products**: ₹${(LV.crude * 7.2).toFixed(0)}/MT equivalent — 30% of COGS (₹54 Cr)\n- **Electronics components**: +2.1% — 15% of COGS (₹27 Cr)\n- **Freight index**: +12% QoQ on India-GCC routes\n\n### Total COGS Headwind\n- WPI 5.1% vs 3.5% budget → **+₹2.9 Cr** incremental cost\n- Cumulative COGS overrun on ₹180 Cr base: **~₹8.4 Cr**\n\n### Macro Watch\nCPI at 4.85% — below RBI's 6% upper band but above 4% midpoint, **limiting near-term rate cut room**.`
            : `## Commodity & COGS Exposure\n\nBrent crude is at **$${LV.crude}/bbl**, up 4% MoM. WPI inflation at **${LV.wpi}%** is compounding input cost pressure.\n\n### COGS Breakdown (₹180 Cr base)\n- **Petroleum products** (30% = ₹54 Cr): Each **$10/bbl move** = ₹4.5 Cr annual COGS change\n- **Steel** (20% = ₹36 Cr): ₹58,000/MT, up 3% MoM\n- **Freight/logistics** (10% = ₹18 Cr): Mumbai–Dubai corridor +12% QoQ\n- **Electronics** (15% = ₹27 Cr): USD/INR sensitive\n\n### Total Macro COGS Headwind (FY26 vs Budget)\n- Crude at $${LV.crude} vs $80 budget → **+₹3.9 Cr**\n- WPI 5.1% vs 3.5% budget → **+₹2.9 Cr**\n- Freight escalation → **+₹1.6 Cr**\n- **Total COGS overrun**: ~₹8.4 Cr\n\n### Crude Outlook\nOPEC+ maintaining **2.2 Mbpd cuts** through Q2 2026. Base case: **$85–95/bbl** range. Upside risk: Middle East escalation could spike to **$110+**.`,
          action: "**Immediate (this week)**\n- Lock 40% of Q1 petroleum requirement via forward contracts\n- Set crude **$95 alert** as procurement trigger\n\n**Short-term (30 days)**\n- Negotiate 6-month fixed-price agreements with top 3 steel vendors\n- Build 45-day inventory buffer (currently 30 days)\n- Add commodity price escalation clauses in customer contracts > ₹5 Cr",
          regional: `India: WPI ${LV.wpi}%, CPI 4.85%. Steel ₹58,000/MT. PPAC domestic price formula. UAE/SA: Gulf producers insulated; refining margins healthy. Global: Baltic Dry Index 1,420 (+8% WoW). OPEC+ compliance 97%.`,
          sources: SOURCES_CRUDE,
        };
      }

      case "gsec": {
        const whatIfYield = q.match(/(\d+(\.\d+)?)\s*(%|percent)/);
        if (s.whatif > 0 && whatIfYield) {
          const newYield = parseFloat(whatIfYield[1]);
          const yieldDelta = newYield - LV.gSecYield;
          const mtmImpact = (60 * 4.2 * (yieldDelta / 100)).toFixed(2);
          return {
            query_type: "interest_rate", confidence: 86,
            impact: `## G-Sec Scenario: 10Y Yield at ${newYield}%\n\nMove of ${yieldDelta > 0 ? "+" : ""}${yieldDelta.toFixed(2)}% from current ${LV.gSecYield}%.\n\n### Portfolio Impact (₹60 Cr)\n- **MTM impact**: ₹${Math.abs(parseFloat(mtmImpact)).toFixed(2)} Cr ${yieldDelta > 0 ? "unrealised loss" : "unrealised gain"}\n- **Modified duration**: 4.2 years | **DV01**: ₹2.52 Lakh per bps\n- **Price change**: ${(4.2 * yieldDelta).toFixed(2)}% (duration × yield delta)\n- **Annual coupon income**: ₹${(60 * LV.gSecYield / 100).toFixed(2)} Cr — unchanged\n\n### Classification Matters\n**HTM** (Held-to-Maturity) shields P&L from MTM volatility — only **AFS/HFT** bonds take the accounting hit.`,
            action: yieldDelta > 0
              ? "**Rising yield — protect P&L:**\n- Reclassify bonds to HTM if not already done — eliminates MTM P&L hit\n- Avoid fresh long-duration bond purchases\n- Consider short-duration FRBs for new cash deployment"
              : "**Falling yield — capture gains:**\n- Book MTM gains by selling AFS bonds at premium\n- Reinvest in shorter-duration paper\n- Laddering strategy recommended (3Y/5Y/10Y in 40:30:30)",
            regional: `10Y G-Sec: ${LV.gSecYield}%. 5Y: 6.95%. 2Y: 6.78%. RBI OMO: buying ₹20,000 Cr/week to maintain liquidity. SDL spreads: 35–45 bps over benchmark.`,
            sources: SOURCES_GSEC,
          };
        }
        return {
          query_type: "interest_rate", confidence: 83,
          impact: `## G-Sec Portfolio Analysis\n\nG-Secs are sovereign bonds issued by the Government of India. Your current portfolio:\n\n### Holdings\n- **Portfolio**: ₹60 Cr in 10Y G-Sec bonds\n- **Current yield**: ${LV.gSecYield}% (stable, flat curve)\n- **Modified duration**: 4.2 years → 1% yield move = 4.2% price change\n- **Annual coupon income**: ₹${(60 * LV.gSecYield / 100).toFixed(2)} Cr\n- **MTM at current prices**: Approximately at par (yield ≈ coupon)\n- **DV01**: ₹2.52 Lakh per basis point\n\n### Opportunity\nWith RBI in hold-then-cut mode, yields could drift **15–20 bps lower** in H2 FY26 → creating a **₹3.8–5.0 Cr MTM gain** opportunity for AFS-classified bonds.`,
          action: "**Portfolio structuring:**\n- Classify ₹40 Cr in AFS — captures yield-drop upside\n- Classify ₹20 Cr in HTM — provides P&L stability\n- Ladder maturities: 3Y/5Y/10Y in 40:30:30 ratio\n- Target 15–20 bps yield pickup by shifting some holdings to SDLs (State Development Loans)",
          regional: `India: 10Y G-Sec ${LV.gSecYield}%. 10Y US Treasury 4.35%. India-US spread 285 bps. RBI OMO active. FPI holding in G-Sec: $25 Bn (10% of FPI limit utilised).`,
          sources: SOURCES_GSEC,
        };
      }

      case "fed":
        return {
          query_type: "combined", confidence: 79,
          impact: `The US Federal Reserve held Fed Funds Rate at 5.25–5.50% (Mar 2026 FOMC). Key implications for India and your business:\n\n• **India rate differential**: India 6.50% vs US 5.38% = 112 bps spread (tight by historical standards)\n• **USD/INR pressure**: Higher-for-longer US rates support USD → INR depreciation pressure. Each +25 bps Fed hike adds ~₹0.40–0.60 INR depreciation on average\n• **FII flows**: Tight spread reduces attractiveness of India debt for foreign investors → potential outflow of ₹15,000–25,000 Cr\n• **Your FX impact**: If INR depreciates 2% on Fed hawkishness → ₹7.4 Cr additional cost on unhedged USD book\n• **G-Sec yields**: India yields typically rise 15–25 bps in sympathy with US yields\n\nFed's dot plot signals 2 cuts in 2026 (total 50 bps). Markets pricing 1.8 cuts. First cut expected Sep 2026.`,
          action: "Increase USD hedge ratio ahead of FOMC meetings (Mar, Jun, Sep). Monitor DXY above 105 as a trigger for accelerated INR hedging. Consider USD-denominated short-term deposits to earn carry while maintaining FX cover.",
          regional: "US: Fed funds 5.25–5.50%, PCE 2.6%. ECB: 3.75% (cutting). BoJ: 0.5% (hiking slowly). DXY 104.2. EM basket -1.8% YTD. India FII: Net buyer ₹8,200 Cr MTD.",
          sources: [
            { name: "US Federal Reserve FOMC Statement", detail: "March 2026 decision — hold at 5.25–5.50%", category: "official" },
            { name: "Bloomberg Rates Monitor", detail: "Fed futures, dot plot, market pricing", category: "market" },
          ],
        };

      case "gdp":
        return {
          query_type: "combined", confidence: 80,
          impact: `India GDP growth at 7.2% for FY26 (Q3 advance estimate) — fastest major economy globally. Business implications:\n\n• **Domestic demand**: Strong consumer spending supports revenue visibility for India-focused segments\n• **Credit growth**: 14.2% YoY bank credit growth → easier refinancing conditions for your ₹250 Cr debt\n• **Capex cycle**: Government capex ₹11.1L Cr in FY26 (3.4% of GDP) — boosts infrastructure, manufacturing orders\n• **Wage inflation**: Tight labour market pushing up wage costs 8–10% in manufacturing\n• **GST collections**: ₹1.89L Cr/month average — fiscal headroom for RBI coordination\n\nSlowdown risk: US recession scenario (-1% US GDP) could reduce India growth to 6.2%, impacting export-oriented revenues by 8–12% and triggering INR depreciation to ₹86–88.`,
          action: "Leverage strong GDP growth to lock in long-tenor debt at current rates (before rate cycle turns). Negotiate customer contracts with annual price escalation clauses linked to WPI. Explore export revenue diversification to benefit from weak INR.",
          regional: "India: 7.2% FY26E, 7.0% FY27F. UAE: 4.1% (oil-driven). SA: 2.8%. China: 4.8%. US: 2.4%. Global: 3.2% (IMF Apr 2026).",
          sources: SOURCES_MACRO,
        };

      case "margin":
        return {
          query_type: "combined", confidence: 84,
          impact: `## Combined Macro Impact — FY26 Snapshot\n\nYour total macro cost headwind for FY26 stands at **₹14.2 Cr** vs ₹8.2 Cr budgeted.\n\n### P&L Impact Breakdown\n| Driver | Impact | vs Budget | Status |\n|---|---|---|---|\n| FX (INR depreciation) | ₹7.2 Cr | +₹4.8 Cr | 🔴 High |\n| Commodity inflation | ₹8.4 Cr | +₹4.9 Cr | 🟡 Elevated |\n| Interest rates | ₹0.0 Cr | Flat | 🟢 Neutral |\n| G-Sec MTM | ₹0.0 Cr | Flat | 🟢 Neutral |\n\n### Margin Impact\n- **EBITDA compression**: ~65 bps vs budget\n- **Probability of >2% margin impact**: 61%\n\n### Key Risk Scenario\nIf crude hits **$100** and INR reaches **₹87**, combined headwind rises to **₹22 Cr** — EBITDA compression of **200+ bps**. Activate contingency hedges at these levels.`,
          action: "**Immediate (this week)**\n- Accelerate FX hedge to 80% — eliminates ₹3 Cr of avoidable drag\n- Set crude $95 and INR ₹86 as combined alert trigger\n\n**Short-term (30 days)**\n- Implement dynamic pricing model with quarterly reviews\n- Negotiate commodity-linked price escalators in B2B contracts\n- Target ₹3–4 Cr logistics cost reduction via route optimisation",
          regional: "India sector margins under pressure from input inflation. Manufacturing EBITDA margins avg 14.2% (FY26E vs 15.1% FY25A). GCC operations benefit from stable costs.",
          sources: SOURCES_MACRO,
        };

      case "risk":
        return {
          query_type: "combined", confidence: 86,
          impact: `## MacroPulse Risk Assessment\n\nCurrent macro exposure across your business profile:\n\n### Tier 1 — High Impact, High Probability\n- **FX Depreciation**: INR to ₹86–88 (+70% probability in 12M) → **₹13.4 Cr exposure**\n- **Crude spike to $100+**: 45% probability → **₹11.3 Cr COGS impact**\n\n### Tier 2 — Medium Impact\n- **RBI rate hike (+25 bps)**: 15% probability → ₹1.6 Cr interest cost\n- **WPI above 7%**: 30% probability → ₹5.4 Cr material cost\n\n### Tier 3 — Tail Risk\n- **Geopolitical crude shock to $120**: ₹29 Cr worst-case COGS\n- **INR to ₹90** (stress): ₹28 Cr FX + working capital impact\n\n### Portfolio Summary\n- **1-Year VaR (95% confidence)**: ₹18.4 Cr\n- **Expected macro cost (base case)**: ₹14.2 Cr net headwind`,
          action: "**Immediate (this week)**\n- Prioritise FX hedge expansion — highest Return on Hedge Effectiveness\n- Set crude **$95** as procurement trigger\n\n**Short-term (30 days)**\n- Maintain ₹25 Cr liquidity buffer for macro contingencies\n- Run quarterly stress tests across FX + crude scenarios\n- Recommend board risk policy review before FY27 budget",
          regional: "India tail risks: El Niño impact on food inflation, US slowdown contagion, China demand weakness. GCC: Oil revenue cycle, geopolitical spillover from Middle East.",
          sources: [...SOURCES_RBI, ...SOURCES_FX],
        };

      case "workingcap":
        return {
          query_type: "combined", confidence: 78,
          impact: `Working capital is significantly impacted by current macro conditions:\n\n• **Receivables** (DSO 45 days on ₹400 Cr revenue = ₹49 Cr): USD/INR movement creates FX translation risk on USD receivables. At ₹84.20, $6M receivable = ₹50.5 Cr. A 2% INR move changes this by ₹1 Cr.\n• **Payables** (DPO 60 days): USD payables rise with INR depreciation. Current USD payable: ~₹58 Cr equivalent.\n• **Inventory** (30-day buffer = ₹14.8 Cr at COGS/365): Commodity inflation inflates inventory carrying cost. Steel/petroleum at elevated prices.\n• **Cash conversion cycle**: 45 + 30 - 60 = 15 days. Efficient, but commodity inflation shortening effective runway.\n\nNet working capital gap: ~₹43 Cr. Interest cost of funding at 9.5%: ~₹4.1 Cr annually.`,
          action: "Extend supplier payment terms to 75 days for commodity inputs (saves ₹1.2 Cr financing cost). Accelerate customer collections on USD invoices to reduce FX exposure period. Consider invoice discounting for ₹15–20 Cr of receivables at 7.5% to improve cash conversion.",
          regional: "India: Average manufacturing DSO 52 days, DPO 48 days. GCC: DSO typically 30–35 days. Factoring/discounting market in India growing at 18% YoY.",
          sources: SOURCES_MACRO,
        };

      case "cfo":
        return {
          query_type: "combined", confidence: 88,
          impact: `## CFO Executive Brief — MacroPulse Weekly\n### ${new Date().toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}\n\n### Top 3 Macro Risks This Week\n\n**1. FX 🔴 High**\nUSD/INR at ₹84.20, testing RBI's corridor ceiling. Unhedged $4.4M carries ₹7.4 Cr downside if INR breaches ₹86. Hedge ratio at 65% — below recommended 80%. **Action required.**\n\n**2. Commodity 🟡 Elevated**\nBrent at $87.5, OPEC+ discipline holding. WPI at 5.1% compounding COGS pressure. Net quarterly impact ₹3.8 Cr above budget. Monitor $90 trigger.\n\n**3. Rates 🟢 Neutral**\nRBI held at 6.50%. No near-term hike risk. Rate cut in H2 FY26 could unlock ₹2 Cr saving. No action needed this week.\n\n### P&L Summary\n| Metric | Value |\n|---|---|\n| Macro headwind YTD | ₹14.2 Cr |\n| Budget | ₹8.2 Cr |\n| Overrun | ₹6.0 Cr |\n| EBITDA compression | ~65 bps |`,
          action: "**Board presentation points:**\n- Propose FX hedge policy upgrade 65% → 80% — NPV saving ₹4.2 Cr over 12M\n- Commodity procurement strategy review in next treasury meeting\n- G-Sec portfolio at par — no MTM action needed this quarter\n- Set combined alert: crude > $95 AND INR > ₹86 → contingency activation",
          regional: "India macro: Stable, 7.2% growth. GCC: Supportive. Global: Fed on hold, DXY softening. Next key event: RBI MPC (June 2026), US NFP (this Friday).",
          sources: [...SOURCES_RBI, ...SOURCES_FX, ...SOURCES_CRUDE[0] ? [SOURCES_CRUDE[0]] : []],
        };

      case "explain": {
        // Concept explanations
        const concept =
          q.includes("repo rate") || q.includes("what is repo") ? "repo_rate" :
          q.includes("wpi") ? "wpi" :
          q.includes("g-sec") || q.includes("gsec") || q.includes("government bond") ? "gsec_concept" :
          q.includes("mtm") || q.includes("mark to market") ? "mtm" :
          q.includes("forward contract") || q.includes("forward contract") ? "forward" :
          q.includes("hedge") || q.includes("hedging") ? "hedging_concept" :
          q.includes("ebitda") ? "ebitda" :
          q.includes("cogs") ? "cogs" :
          q.includes("duration") ? "duration" :
          q.includes("dxy") ? "dxy" :
          q.includes("opec") ? "opec" : "general";

        const concepts: Record<string, { text: string; action: string }> = {
          repo_rate: { text: "The **Repo Rate** (Repurchase Agreement Rate) is the interest rate at which the Reserve Bank of India (RBI) lends short-term funds to commercial banks against government securities. It's the primary monetary policy tool.\n\nHow it works: Banks pledge G-Secs to RBI → RBI lends overnight at repo rate → Banks repay next day.\n\nCurrent repo: 6.50%. When RBI raises repo → borrowing costs rise → credit tightens → inflation cools. When RBI cuts → credit becomes cheaper → investment increases.\n\nFor your business: Your floating rate loans are typically benchmarked to MCLR or repo-linked (RLLR). Current RLLR = Repo (6.50%) + Spread (~250 bps) = ~9.00%. A 25 bps repo cut → RLLR drops to 8.75% → ₹1 Cr saving per ₹40 Cr of floating debt.", action: "Monitor MPC dates. Next MPC: June 2026. Track CPI — if it falls below 4.5% for 2 consecutive quarters, rate cut becomes probable." },
          wpi: { text: "**WPI (Wholesale Price Index)** measures the average price change of goods at the wholesale/manufacturer level — before they reach consumers. In India, it covers 697 commodities across 3 groups: Primary Articles (22%), Fuel & Power (13%), and Manufactured Products (65%).\n\nCurrent WPI: 5.1% YoY. Manufacturing WPI (most relevant for your COGS): 4.8%. Key contributors: Metals (+6.2%), Chemicals (+4.1%), Petroleum (+8.3%).\n\nDifference from CPI: WPI measures production-level prices; CPI measures consumer prices. WPI leads CPI by ~3–6 months — rising WPI signals future retail inflation.\n\nBusiness impact: Every 1% rise in Manufacturing WPI adds ~₹1.6 Cr to your ₹180 Cr COGS base.", action: "Use WPI trend as an early warning for COGS planning. If WPI exceeds 6%, accelerate raw material procurement. Link customer pricing contracts to WPI index for inflation pass-through." },
          gsec_concept: { text: "**G-Secs (Government Securities)** are debt instruments issued by the Government of India to borrow from the market. Types: Treasury Bills (91/182/364-day, zero coupon), Dated G-Secs (2–40 year fixed coupon bonds), Floating Rate Bonds, SDLs (State Development Loans).\n\nYour ₹60 Cr portfolio: 10Y dated G-Secs at 7.20% yield. Coupon income: ₹4.32 Cr/year. Price inversely moves with yield — a 1% yield rise = ~4.2% price fall (modified duration = 4.2 years).\n\nClassification matters: HTM (Held-to-Maturity) = no MTM; AFS (Available-for-Sale) = MTM through OCI; HFT = MTM through P&L.", action: "Reclassify bonds strategically before RBI rate cut cycle — move to AFS to capture MTM gains when yields fall. Ladder maturities to manage rollover risk." },
          mtm: { text: "**MTM (Mark-to-Market)** is the practice of revaluing assets at their current market price, not the original cost.\n\nFor your G-Sec portfolio: If you bought a 10Y bond at ₹100 (yield 7.20%) and yields rise to 7.70%, the price falls to ~₹97.9 — a ₹2.1 Cr MTM loss on ₹60 Cr holdings.\n\nFormula: Price change ≈ -Modified Duration × Yield Change × Price\n= -4.2 × 0.5% × 100 = -2.1%\n\nMTM only affects P&L if bonds are in AFS/HFT category. HTM bonds are immune to MTM volatility but surrender potential gains.", action: "Current MTM: Near zero (yield close to coupon). Rate cut scenario: 50 bps yield drop → +₹2.52 Cr MTM gain on AFS portfolio. Timing AFS reclassification before the rate cut cycle is a treasury alpha opportunity." },
          forward: { text: "A **Forward Contract** is a private agreement to buy or sell a currency at a predetermined rate on a future date. Unlike options, forwards are obligations (not rights).\n\nExample: You have $1M payable in 3 months. USD/INR today = ₹84.20. 3M forward rate = ₹84.85 (forward points = 65 paise). You lock today at ₹84.85 → even if USD/INR hits ₹86, you pay only ₹84.85 Cr.\n\nCost: Forward points = Interest rate differential between India (6.50%) and US (5.38%) ≈ 77 paise/$/year (0.92%). Forward contracts have no upfront premium but carry mark-to-market risk if the position moves against you.\n\nYour current hedge: 65% of $12.5M = $8.1M hedged via forwards at avg rate ₹84.50.", action: "Roll forwards quarterly. Current 3M forward rate: ₹84.85. Recommend hedging an additional $1.9M to reach 80% cover. Cost: ~₹14.6 Lakh additional hedging premium annualised." },
          hedging_concept: { text: "**Hedging** is a risk management strategy that uses financial instruments to offset potential losses from adverse price movements. Types relevant to your business:\n\n1. **FX Hedging**: Forward contracts, options, cross-currency swaps to protect against INR depreciation on USD payables\n2. **Interest Rate Hedging**: Interest Rate Swaps (IRS) — pay fixed, receive floating — to lock borrowing costs\n3. **Commodity Hedging**: Crude oil futures/swaps to fix input costs for petroleum products\n4. **Natural Hedging**: Match USD revenues with USD costs — no financial instrument needed\n\nHedge effectiveness = (Change in hedging instrument P&L) / (Change in underlying exposure P&L). A perfect hedge = 100%.", action: "Current hedge ratio: FX 65%, commodity 0%, IR 0%. Recommended: FX 80%, commodity 35%, IR 30%. Priority: FX hedge is cheapest insurance given current market conditions." },
          ebitda: { text: "**EBITDA** = Earnings Before Interest, Tax, Depreciation and Amortisation. It measures operating profitability, stripping out capital structure and accounting decisions.\n\nFormula: Revenue − COGS − Operating Expenses = EBITDA\nYour business (estimated FY26): Revenue ₹400 Cr, COGS ₹180 Cr, OpEx ₹140 Cr → EBITDA ~₹80 Cr (20% margin).\n\nMacro drivers of your EBITDA:\n• COGS inflation (WPI/crude) → directly compresses gross margin\n• FX depreciation → inflates USD-denominated COGS and payables\n• Interest rates → below EBITDA line but affects PAT and cash\n\nCurrent macro headwind: -₹15.6 Cr on EBITDA vs budget (₹80 Cr → ~₹64.4 Cr if unmitigated).", action: "Target 75–80 bps EBITDA recovery via: FX hedge (saves ₹3 Cr), commodity procurement strategy (saves ₹4 Cr), pricing escalators (recovers ₹5 Cr). Net: recover 70% of macro drag." },
          cogs: { text: "**COGS (Cost of Goods Sold)** is the direct cost of producing goods sold — raw materials, direct labour, manufacturing overhead. Your COGS breakdown (₹180 Cr base):\n\n• Petroleum products: 30% = ₹54 Cr | Sensitive to Brent crude\n• Steel: 20% = ₹36 Cr | Sensitive to global steel prices and WPI metals\n• Electronics/components: 15% = ₹27 Cr | Sensitive to USD/INR and global supply chains\n• Freight/logistics: 10% = ₹18 Cr | Sensitive to fuel prices and shipping rates\n• Other: 25% = ₹45 Cr\n\nMacro COGS sensitivity (FY26 vs budget):\n• Crude $87.5 vs $80 budget: +₹3.9 Cr\n• WPI 5.1% vs 3.5% budget: +₹2.9 Cr\n• FX ₹84.20 vs ₹82 budget: +₹1.6 Cr (electronics)\n\nTotal COGS overshoot: ₹8.4 Cr vs budget.", action: "Review COGS structure quarterly using MacroPulse Simulation Impact page. Link vendor contracts to commodity indices for fair sharing of macro risk." },
          duration: { text: "**Modified Duration** measures a bond's price sensitivity to interest rate changes. Formula: % price change ≈ -Modified Duration × Yield Change.\n\nYour 10Y G-Sec (Modified Duration 4.2 years):\n• +100 bps yield rise → -4.2% price fall → -₹2.52 Cr on ₹60 Cr portfolio\n• -50 bps yield fall → +2.1% price rise → +₹1.26 Cr MTM gain\n\nDV01 (Dollar Value of 01 bps) = 4.2 × ₹60 Cr × 0.01% = ₹2.52 Lakh per bps\n\nLonger duration = higher sensitivity = more risk AND more reward in a rate-cut environment.", action: "With rate cuts expected in H2 FY26, maintaining 4.2Y duration is beneficial — each 25 bps RBI cut generates ~₹63 Lakh MTM gain. Consider extending to 5Y duration if cut cycle is confirmed." },
          dxy: { text: "**DXY (US Dollar Index)** measures the USD against a basket of 6 major currencies (EUR 57.6%, JPY 13.6%, GBP 11.9%, CAD 9.1%, SEK 4.2%, CHF 3.6%). Current DXY: 104.2.\n\nRelevance to India/your business:\n• High DXY (>104) → USD strong globally → INR under pressure → your USD payables get more expensive\n• DXY above 105 historically triggers RBI intervention above ₹84.50\n• DXY driven by: Fed policy (hawkish = higher DXY), US growth data, geopolitical risk\n\nDXY at 104 = moderate USD strength. Peak was 114 (Oct 2022). Fair value estimate: 98–100.", action: "Monitor DXY above 105 as FX hedge trigger. If DXY falls below 102 (dollar weakening), USD/INR could improve to ₹82–83 — opportunity to reduce hedge cost by not rolling forwards." },
          opec: { text: "**OPEC+** (Organization of Petroleum Exporting Countries + Russia/others) controls ~40% of global oil supply. Current stance: 2.2 Mbpd voluntary production cuts through Q2 2026.\n\nKey producers: Saudi Arabia (largest cut: -1 Mbpd unilateral), Russia, UAE, Iraq. Compliance rate: 97%.\n\nImpact on your business:\n• OPEC+ supply cuts = Brent floor at ~$80/bbl (OPEC defends this)\n• Upside risk: Geopolitical disruption (Iran/Israel, Red Sea) could spike to $100\n• Downside risk: China demand weakness or OPEC+ collapse could drop to $65\n\nBase case (OPEC+ holds): Brent $85–95 range through CY2026.", action: "Use $85 as procurement budget assumption, $95 as stress scenario. Build 45-day petroleum buffer to weather OPEC+ surprise decisions. Review hedge ratios quarterly aligned with OPEC+ meeting calendar (next: June 2026)." },
          general: { text: "I can explain a wide range of financial and macroeconomic concepts. Some topics I cover in depth:\n\n**Monetary Policy**: Repo rate, SDF, MSF, CRR, SLR, OMO, LAF corridor, MCLR, RLLR\n**FX & Hedging**: Forward contracts, options, swaps, cross-currency swaps, DXY, carry trade, real effective exchange rate (REER)\n**Debt Markets**: G-Sec, T-bills, SDL, corporate bonds, duration, convexity, YTM, DV01, MTM\n**Commodities**: Brent crude, WPI, CPI, futures, commodity swaps, supply chain cost modelling\n**Business Finance**: EBITDA, COGS, working capital, cash conversion cycle, leverage ratios\n\nJust ask: \"What is [concept]?\" or \"Explain [topic]\" — I'll give you a detailed explanation tied to your business context.", action: "Ask any question — macro, finance, treasury, or risk." },
        };

        const c = concepts[concept] ?? concepts["general"];
        return {
          query_type: "overview", confidence: 95,
          impact: c.text,
          action: c.action,
          regional: "",
          sources: concept !== "general" ? [
            { name: "Investopedia Finance Reference", detail: "Concept definitions and examples", category: "official" },
            { name: "RBI Learning Resources", detail: "Official explanations of Indian monetary instruments", category: "official" },
          ] : [],
        };
      }

      default:
        return {
          query_type: "combined", confidence: 75,
          impact: `## Macro Overview — Current Environment\n\nLive macro snapshot: RBI repo **${LV.repoRate}%** | USD/INR **₹${LV.inrRate}** | Brent **$${LV.crude}/bbl** | WPI **${LV.wpi}%** | G-Sec **${LV.gSecYield}%**\n\n### Your Combined Exposure — FY26\n- **FX**: INR at ₹84.20 vs ₹82 budget → **₹7.2 Cr** drag on USD-denominated costs\n- **Commodities**: Brent elevated + WPI at 5.1% → **₹8.4 Cr** COGS inflation\n- **Interest rates**: Flat at 6.50% — **no immediate headwind**\n\n### Total Macro Headwind\n**₹14.2 Cr** net cost overrun vs ₹8.2 Cr budgeted — EBITDA compression of ~65 bps.\n\nFor deeper analysis, ask about FX impact, repo rate scenarios, crude oil sensitivity, G-Sec portfolio, working capital, or request a CFO brief.`,
          action: "**Try these next:**\n- What if INR hits ₹87?\n- Explain how crude oil affects our margins\n- Generate a CFO brief for this week\n- What's our G-Sec MTM exposure?",
          regional: "India: Macro stable. GCC: Supportive. Global: Moderate uncertainty.",
          sources: [...SOURCES_RBI.slice(0, 1), ...SOURCES_FX.slice(0, 1), ...SOURCES_CRUDE.slice(0, 1)],
        };
    }
  })();

  return {
    query_type: reply.query_type,
    impact: reply.impact,
    confidence: reply.confidence,
    publish_status: reply.confidence >= 88 ? "publish" : reply.confidence >= 78 ? "review" : "hitl_queue",
    recommended_action: reply.action,
    regional_context: reply.regional,
    sources: reply.sources,
    scenario_output: {},
    analytics: {},
  };
}

export async function queryMacroPulseAgent(
  text: string,
  tenantId?: string,
  region?: "India" | "UAE" | "Saudi Arabia",
  history: ConversationTurn[] = []
): Promise<MacroPulseAgentQueryResponse> {
  try {
    const { data } = await api.post<MacroPulseAgentQueryResponse>(`${BASE}/agent/query`, {
      text,
      tenant_id: tenantId ?? null,
      region: region ?? null,
    });
    return data;
  } catch {
    return buildMockAgentResponse(text, history);
  }
}

// ── Day 5 service calls ──────────────────────────────────────────────────────

export async function runCFOBriefPipeline(params: {
  tenant_id?: string;
  upload_to_s3?: boolean;
  notify?: boolean;
  dry_run?: boolean;
}): Promise<CFOBriefPipelineResult> {
  const query = new URLSearchParams({
    tenant_id: params.tenant_id ?? "tenant-india-001",
    upload_to_s3: String(params.upload_to_s3 ?? false),
    notify: String(params.notify ?? false),
    dry_run: String(params.dry_run ?? true),
  });
  const { data } = await api.post<CFOBriefPipelineResult>(`${BASE}/cfo-brief/pipeline?${query}`);
  return data;
}

export async function getCostRoutingStatus(): Promise<CostRoutingStatus> {
  const { data } = await api.get<CostRoutingStatus>(`${BASE}/cost-routing/status`);
  return data;
}

export async function getEventLog(): Promise<EventLogEntry[]> {
  const { data } = await api.get<{ events: EventLogEntry[] }>(`${BASE}/events/log`);
  return data.events ?? [];
}

export async function getEventSchemas(): Promise<Record<string, unknown>> {
  const { data } = await api.get<Record<string, unknown>>(`${BASE}/events/schemas`);
  return data;
}

export async function getAgentMetrics(): Promise<AgentMetrics> {
  const { data } = await api.get<AgentMetrics>(`${BASE}/metrics`);
  return data;
}

export async function classifyAlert(
  tenantId: string,
  agentOutput: Record<string, unknown>
): Promise<AlertResponse | null> {
  const { data } = await api.post<AlertResponse | null>(`${BASE_API}/alerts/classify`, {
    tenant_id: tenantId,
    agent_output: agentOutput,
  });
  return data;
}
