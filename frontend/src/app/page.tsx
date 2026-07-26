import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Hero } from "@/features/home/Hero";
import { HowItWorks } from "@/features/home/HowItWorks";
import { TrustBand } from "@/features/home/TrustBand";
import { SiteFooter } from "@/features/home/SiteFooter";

export default function HomePage() {
  return (
    <div className="gg-screen min-h-screen overflow-hidden bg-paper">
      <header className="sticky top-0 z-10 w-full border-b border-paper-border bg-[rgba(244,242,236,.86)] backdrop-blur">
        <div className="mx-auto flex max-w-[1120px] items-center justify-between px-7 py-[15px]">
          <Logo />
          <Link
            href="#how-it-works"
            className="rounded-[10px] border border-paper-border bg-paper-raised px-[15px] py-2 text-[13.5px] font-semibold text-ink-soft transition-colors hover:border-[#cfc9bb] hover:text-ink"
          >
            How it works
          </Link>
        </div>
      </header>

      <main>
        <section className="mx-auto max-w-[1120px] px-7 pb-10 pt-[clamp(36px,6vw,76px)]">
          <Hero />
        </section>
        <HowItWorks />
        <TrustBand />
        <SiteFooter />
      </main>
    </div>
  );
}
