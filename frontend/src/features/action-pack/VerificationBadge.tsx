import type { Verification } from "@/core/domain";
import { cn } from "@/lib/cn";

const isVerified = (v: Verification) => v === "verified";

/** Full badge for the pack header. */
export function VerificationBadge({ verification }: { verification: Verification }) {
  const verified = isVerified(verification);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-[12.5px] font-semibold",
        verified ? "border-verified-border bg-verified-bg text-verified-text" : "border-pending-border bg-pending-bg text-pending-text",
      )}
    >
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
        <circle cx="12" cy="12" r="10" fill={verified ? "#16a34a" : "#d97706"} />
        {verified ? (
          <path d="M17 9l-6 6-3-3" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <path d="M12 7v5l3 2" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        )}
      </svg>
      {verified ? "Verified" : "Newly gathered — pending verification"}
    </span>
  );
}

/** Compact badge for citation cards. */
export function VerificationDot({ verification }: { verification: Verification }) {
  const verified = isVerified(verification);
  return (
    <span
      className={cn(
        "inline-flex flex-none items-center gap-[5px] rounded-full px-[9px] py-1 text-[11.5px] font-semibold",
        verified ? "bg-verified-bg text-verified-text" : "bg-pending-bg text-pending-text",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", verified ? "bg-verified-dot" : "bg-pending-dot")} />
      {verified ? "Verified" : "Pending"}
    </span>
  );
}
