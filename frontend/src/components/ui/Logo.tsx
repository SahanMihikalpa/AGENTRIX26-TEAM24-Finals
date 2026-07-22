import { cn } from "@/lib/cn";

export function Logo({ size = 32, withWordmark = true }: { size?: number; withWordmark?: boolean }) {
  const icon = Math.round(size * 0.56);
  return (
    <div className="inline-flex items-center gap-2.5">
      <div
        className="flex items-center justify-center rounded-[9px] bg-brand"
        style={{ width: size, height: size }}
      >
        <svg width={icon} height={icon} viewBox="0 0 24 24" fill="none">
          <path d="M20 6L9 17l-5-5" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </div>
      {withWordmark && (
        <span className={cn("font-bold tracking-tight")} style={{ fontSize: size * 0.6 }}>
          GovGuide
        </span>
      )}
    </div>
  );
}
