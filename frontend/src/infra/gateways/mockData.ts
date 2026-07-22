import type { ActionPack } from "@/core/domain";

/** Seeded "verified" service — the SUFFICIENT happy path (Scenario A). */
export const LAND_PACK: ActionPack = {
  serviceLabel: "Land Deed Transfer",
  caseSummary: "Inheritance",
  verification: "verified",
  documents: [
    { name: "Original title deed of the property", mandatory: true, sourceId: 1 },
    { name: "Death certificate of the previous owner", mandatory: true, note: "A certified copy from the Registrar General is fine.", sourceId: 1 },
    { name: "Grant of probate or letters of administration", mandatory: true, note: "If there was a will, bring the probate. If not, bring letters of administration from the District Court.", sourceId: 1 },
    { name: "Certified extract from the Land Registry", mandatory: true, sourceId: 1 },
    { name: "Your National Identity Card (NIC)", mandatory: true },
    { name: "Surveyor's plan / survey diagram", mandatory: false, note: "Only if the registry asks to confirm boundaries." },
  ],
  fees: [
    { label: "Stamp duty (inheritance)", amountLkr: 4000, sourceId: 2 },
    { label: "Notary attestation fee", amountLkr: 5000, note: "Typical range; set by your notary." },
    { label: "Land Registry registration", amountLkr: 1050, sourceId: 1 },
    { label: "Certified extract", amountLkr: 500, sourceId: 1 },
  ],
  estimatedCostLkr: 10550,
  office: {
    name: "Divisional Secretariat — Land Registry",
    address: "Your divisional secretariat office",
    hours: "Mon–Fri, 9:00–15:00",
  },
  steps: [
    "Collect the documents in the checklist below.",
    "Have the transfer deed drafted and attested by a notary.",
    "Submit at the Land Registry and pay the registration fee.",
  ],
  citations: [
    { sourceId: 1, title: "Registrar General's Department — Land registration", url: "https://www.rgd.gov.lk", lastVerified: "2026-06-20" },
    { sourceId: 2, title: "Inland Revenue — Stamp duty schedule", url: "https://www.ird.gov.lk", lastVerified: "2026-06-20" },
  ],
};

/** Unseen service — the live gap-fill path (Scenario B), served pending verification. */
export const BUSINESS_PACK: ActionPack = {
  serviceLabel: "Business Name Registration",
  caseSummary: "Sole proprietorship",
  verification: "newly_gathered_pending_verification",
  documents: [
    { name: "Completed Form 1 (Business Name registration)", mandatory: true, sourceId: 3 },
    { name: "Your National Identity Card (NIC)", mandatory: true },
    { name: "Proof of business address", mandatory: true, note: "A recent utility bill or your lease agreement.", sourceId: 3 },
    { name: "Two passport-size photographs", mandatory: false },
    { name: "Approval for a restricted name", mandatory: false, note: 'Only if your name includes a controlled word (e.g. "National", "Bank").' },
  ],
  fees: [
    { label: "Registration fee", amountLkr: 2000, sourceId: 3 },
    { label: "Name search / reservation", amountLkr: 250 },
    { label: "Certified copy of certificate", amountLkr: 300 },
  ],
  estimatedCostLkr: 2550,
  office: {
    name: "Provincial Registrar of Business Names",
    address: "Your provincial council office",
    hours: "Mon–Fri, 9:00–16:00",
  },
  steps: [
    "Reserve your business name.",
    "Complete Form 1 and attach the documents below.",
    "Submit and pay the registration fee to collect your certificate.",
  ],
  citations: [
    { sourceId: 3, title: "Provincial Registrar of Business Names", url: "https://www.gov.lk", lastVerified: "2026-06-20" },
  ],
};
