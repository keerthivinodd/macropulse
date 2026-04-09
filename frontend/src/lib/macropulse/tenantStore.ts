import "server-only";

import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

import type { SensitivityResponse, TenantProfile } from "@/types/macropulse";

const STORE_DIR = path.join(process.cwd(), ".data");
const STORE_PATH = path.join(STORE_DIR, "macropulse-tenant-profiles.json");

type TenantStore = Record<string, TenantProfile>;

const DEFAULT_FX_RATES = {
  usd_inr: 84.2,
  aed_inr: 22.93,
  sar_inr: 22.45,
};

const DEFAULT_BRENT_USD = 87.5;

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

function sanitizeProfile(input: TenantProfile, tenantId?: string): TenantProfile {
  const resolvedTenantId = tenantId ?? input.tenant_id;
  const cogsTotal =
    input.cogs.steel_pct +
    input.cogs.petroleum_pct +
    input.cogs.electronics_pct +
    input.cogs.freight_pct +
    input.cogs.other_pct;

  if (!resolvedTenantId?.trim()) {
    throw new Error("Tenant ID is required.");
  }

  if (Math.abs(cogsTotal - 100) > 0.01) {
    throw new Error("COGS percentages must sum to 100.");
  }

  return {
    ...input,
    tenant_id: resolvedTenantId.trim(),
    company_name: input.company_name.trim(),
    logistics: {
      ...input.logistics,
      primary_routes: input.logistics.primary_routes.filter(Boolean),
    },
    notification_config: {
      ...input.notification_config,
      channels: [...new Set(input.notification_config.channels)],
    },
  };
}

async function ensureStoreDir() {
  await mkdir(STORE_DIR, { recursive: true });
}

async function readStore(): Promise<TenantStore> {
  try {
    const raw = await readFile(STORE_PATH, "utf8");
    return JSON.parse(raw) as TenantStore;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return {};
    }
    throw error;
  }
}

async function writeStore(store: TenantStore) {
  await ensureStoreDir();
  await writeFile(STORE_PATH, JSON.stringify(store, null, 2), "utf8");
}

export async function getTenantProfileFromStore(tenantId: string): Promise<TenantProfile | null> {
  const store = await readStore();
  return store[tenantId] ?? null;
}

export async function upsertTenantProfileInStore(profile: TenantProfile): Promise<TenantProfile> {
  const store = await readStore();
  const existing = store[profile.tenant_id];
  const now = new Date().toISOString();
  const sanitized = sanitizeProfile(profile);
  const saved: TenantProfile = {
    ...sanitized,
    created_at: existing?.created_at ?? sanitized.created_at ?? now,
    updated_at: now,
  };

  store[saved.tenant_id] = saved;
  await writeStore(store);
  return saved;
}

export async function updateTenantProfileInStore(
  tenantId: string,
  profile: TenantProfile
): Promise<TenantProfile | null> {
  const store = await readStore();
  const existing = store[tenantId];
  if (!existing) {
    return null;
  }

  const now = new Date().toISOString();
  const sanitized = sanitizeProfile(profile, tenantId);
  const saved: TenantProfile = {
    ...sanitized,
    tenant_id: tenantId,
    created_at: existing.created_at ?? now,
    updated_at: now,
  };

  store[tenantId] = saved;
  await writeStore(store);
  return saved;
}

export async function deleteTenantProfileFromStore(tenantId: string): Promise<boolean> {
  const store = await readStore();
  if (!store[tenantId]) {
    return false;
  }

  delete store[tenantId];
  await writeStore(store);
  return true;
}

export function calculateTenantSensitivity(profile: TenantProfile): SensitivityResponse {
  const floatingLoanCr =
    profile.debt.total_loan_amount_cr * (profile.debt.floating_proportion_pct / 100);
  const repoImpact = Number((floatingLoanCr * 0.0025).toFixed(4));

  const netUnhedgedUsdM =
    profile.fx.net_usd_exposure_m * (1 - profile.fx.hedge_ratio_pct / 100);
  const netUnhedgedInrCr = (netUnhedgedUsdM * DEFAULT_FX_RATES.usd_inr) / 100;
  const fxImpact = Number((Math.abs(netUnhedgedInrCr) * 0.01).toFixed(2));

  const petroleumCogsCr = profile.cogs.total_cogs_cr * (profile.cogs.petroleum_pct / 100);
  const crudeImpact = Number((petroleumCogsCr * (10 / DEFAULT_BRENT_USD)).toFixed(2));

  const materialPct =
    profile.cogs.steel_pct + profile.cogs.petroleum_pct + profile.cogs.electronics_pct;
  const wpiImpact = Number((profile.cogs.total_cogs_cr * (materialPct / 100) * 0.01).toFixed(2));

  const gsecImpact = Number(
    (profile.portfolio.modified_duration * 0.005 * profile.portfolio.gsec_holdings_cr).toFixed(2)
  );

  return {
    source: "calculated",
    data: {
      REPO_RATE: {
        impact_cr: repoImpact,
        label: `Rs ${repoImpact} Cr extra interest per 0.25% repo rate hike`,
      },
      FX_USD_INR: {
        impact_cr: fxImpact,
        label: `Rs ${fxImpact} Cr P&L impact per 1% USD/INR move on unhedged exposure`,
      },
      WPI_INFLATION: {
        impact_cr: wpiImpact,
        label: `Rs ${wpiImpact} Cr COGS increase per 1% WPI rise`,
      },
      CRUDE_OIL: {
        impact_cr: crudeImpact,
        label: `Rs ${crudeImpact} Cr COGS increase per $10/bbl Brent rise`,
      },
      GSEC_YIELD: {
        impact_cr: gsecImpact,
        label: `Rs ${gsecImpact} Cr MTM loss per 0.5% G-Sec yield rise`,
      },
    },
  };
}
