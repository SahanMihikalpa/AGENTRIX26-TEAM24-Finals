/**
 * Wire DTOs — the snake_case JSON shapes the FastAPI backend emits, matching
 * `backend/app/domain/entities.py`. Used only by the real SSE adapter (Stage S4)
 * and the mappers; UI/feature code never sees these.
 *
 * `amount_lkr` / `estimated_cost_lkr` arrive as string|number (Pydantic serializes
 * Decimal as a string by default) — mappers normalize to number.
 */
export interface CitationDTO {
  title: string;
  url: string | null;
  last_verified: string;
  source_id: number | null;
}

export interface DocumentItemDTO {
  name: string;
  mandatory: boolean;
  source_id: number | null;
  notes: string;
}

export interface FeeLineDTO {
  label: string;
  amount_lkr: string | number;
  source_id: number | null;
  notes: string;
}

export interface ActionPackOfficeDTO {
  name: string;
  address: string;
  hours: string;
  contact: string;
  district: string;
}

export interface ActionPackDTO {
  service_label: string;
  district: string | null;
  documents: DocumentItemDTO[];
  fees: FeeLineDTO[];
  office: ActionPackOfficeDTO | null;
  steps: string[];
  estimated_cost_lkr: string | number;
  verification: "verified" | "newly_gathered_pending_verification";
  citations: CitationDTO[];
  fallback: boolean;
  fallback_message: string | null;
}

/** Acknowledgement from `POST /api/experience-reports` (FR-6). */
export interface ExperienceReportResponseDTO {
  id: number;
  status: string;
}

/** One row of `GET /api/moderation/queue` (B4 / FR-7). */
export interface ModerationItemDTO {
  source_id: number;
  title: string;
  url: string | null;
  source_type: string;
  confidence: number;
  verification_status: string;
  retrieved_date: string;
  published_date: string | null;
  is_official?: boolean;
}

/** Result of `POST /api/moderation/{id}/promote|reject`. */
export interface ModerationActionDTO {
  ok: boolean;
}
