import { Logo } from "@/components/ui/Logo";

export function SiteFooter() {
  return (
    <footer className="mx-auto max-w-[1120px] px-7 pb-14 pt-11">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <Logo size={26} />
        <div className="max-w-[520px] text-right text-[12.5px] leading-snug text-ink-muted">
          An independent guide to Sri Lankan government services. GovGuide points you to official
          sources but is not a government agency.
        </div>
      </div>
    </footer>
  );
}
