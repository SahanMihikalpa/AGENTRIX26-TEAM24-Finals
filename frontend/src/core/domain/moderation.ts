/** Admin moderation queue item — pending `auto_gathered` knowledge (B4 / FR-7). */

/** Source-level trust state (backend VerificationStatus enum). Distinct from the
 *  ActionPack-level `Verification` label. */
export type SourceVerificationStatus = "verified" | "auto_gathered" | "pending";

export interface ModerationItem {
  sourceId: number;
  title: string;
  url?: string;
  serviceName: string;
  retrievedDate: string;
  confidence: number;
  verificationStatus: SourceVerificationStatus;
}

/** Experience report submitted from the Action Pack feedback bar (FR-6). */
export type ReportOutcome = "matched" | "extra_doc" | "wrong_office" | "other";

export interface ExperienceReportInput {
  sessionId: string;
  serviceId?: number;
  outcome: ReportOutcome;
  text?: string;
}
