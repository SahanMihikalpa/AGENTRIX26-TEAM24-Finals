/**
 * Action Pack — the structured, cited output of agent A6.
 * Aligned to the as-built backend entity `backend/app/domain/entities.py::ActionPack`
 * (docs/agents/a6 + docs/05). These are the *view models* (camelCase); the snake_case
 * wire DTOs live in src/infra/dto.ts and are translated by src/infra/mappers.ts.
 */
export type Verification = "verified" | "newly_gathered_pending_verification";

export interface Citation {
  /** Links a fact to its evidence (Source.id on the backend). */
  sourceId?: number;
  title: string;
  url?: string;
  /** ISO date string, e.g. "2026-06-20" */
  lastVerified: string;
}

export interface DocumentItem {
  name: string;
  mandatory: boolean;
  note?: string;
  /** → a Citation.sourceId for provenance */
  sourceId?: number;
}

export interface FeeLine {
  label: string;
  amountLkr: number;
  note?: string;
  sourceId?: number;
}

export interface ActionPackOffice {
  name: string;
  address: string;
  hours?: string;
  contact?: string;
  district?: string;
}

export interface ActionPack {
  serviceLabel: string;
  /** UI-only convenience (the pinned variant, e.g. "Inheritance"); may be absent. */
  caseSummary?: string;
  district?: string;
  documents: DocumentItem[];
  fees: FeeLine[];
  office?: ActionPackOffice;
  steps: string[];
  estimatedCostLkr: number;
  verification: Verification;
  citations: Citation[];
  /** Confidence-gate fallback (AD-8): when true, render the fallback message, not a pack. */
  fallback?: boolean;
  fallbackMessage?: string;
}
