import { Hero } from "@/features/home/Hero";

export default function HomePage() {
  return (
    <div className="gg-screen relative flex min-h-screen flex-col overflow-hidden bg-surface">
      <div className="gg-blob -bottom-[260px] -left-[200px] h-[760px] w-[760px] bg-blob-blue opacity-60" />
      <div className="gg-blob -top-[160px] -right-[220px] h-[620px] w-[620px] bg-blob-amber opacity-50" />

      <header className="gg-chrome relative z-10 border-b border-line bg-white shadow-header backdrop-blur-md">
        <div className="relative mx-auto flex w-full max-w-[1200px] items-center justify-between gap-4 px-6 py-4">
          <a href="#" className="flex-shrink-0 text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Quick Guide
          </a>
          <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap text-[18px] font-bold tracking-tight text-ink-900">
            GovGuide
          </span>
          <div className="flex flex-shrink-0 items-center gap-5">
            <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
              Contact
            </a>
            <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
              About
            </a>
          </div>
        </div>
      </header>

      <main className="relative z-[2] flex flex-1 flex-col items-center justify-center px-5 py-12 text-center sm:px-8">
        <Hero />
      </main>

      <footer className="gg-chrome relative z-[2] flex flex-col items-center gap-3 border-t border-line bg-white px-6 py-5 shadow-[0_-4px_20px_oklch(0.3_0.02_255/0.08)] sm:flex-row sm:justify-between sm:px-12">
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          <span className="text-[13px] text-ink-600">© 2026 GovGuide</span>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Terms
          </a>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Privacy
          </a>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Accessibility
          </a>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2">
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Ministries
          </a>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Help Center
          </a>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            Status
          </a>
          <a href="#" className="text-[13px] text-ink-600 transition-colors hover:text-ink-900">
            API
          </a>
        </div>
      </footer>
    </div>
  );
}
