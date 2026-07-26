/** Admin moderation queue item — pending `auto_gathered` knowledge (B4 / FR-7). */

/** Source-level trust state (backend VerificationStatus enum). Distinct from the
 *  ActionPack-level `Verification` label. */
export type SourceVerificationStatus =
  | "verified"
  | "auto_gathered"
  | "pending"
  | "rejected";

/** Where a source came from (backend SourceType enum). */
export type SourceType = "gazette" | "circular" | "portal" | "experience";

export interface ModerationItem {
  sourceId: number;
  title: string;
  url?: string;
  /** Provenance of the source. The queue is source-level, so there is no single
   *  service to name — this replaces the speculative `serviceName` that the
   *  backend never had a field for. */
  sourceType: SourceType;
  retrievedDate: string;
  publishedDate?: string;
  confidence: number;
  verificationStatus: SourceVerificationStatus;
  /** False when the source came from outside the official government domains —
   *  the moderator needs to see that before promoting it. */
  isOfficial: boolean;
}

/** Experience report submitted from the Action Pack feedback bar (FR-6). */
export type ReportOutcome = "matched" | "extra_doc" | "wrong_office" | "other";

export interface ExperienceReportInput {
  sessionId: string;
  serviceId?: number;
  outcome: ReportOutcome;
  text?: string;
}
