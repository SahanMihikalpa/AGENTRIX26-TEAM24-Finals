import { Logo } from "@/components/ui/Logo";
import { Hero } from "@/features/home/Hero";

export default function HomePage() {
  return (
    <div className="gg-screen flex min-h-screen flex-col bg-slate-50">
      <header className="px-6 py-5">
        <Logo />
      </header>
      <main className="flex flex-1 flex-col items-center justify-center px-5 pb-24 pt-4">
        <Hero />
      </main>
    </div>
  );
}
