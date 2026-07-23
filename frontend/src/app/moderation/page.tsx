import Link from "next/link";
import { Logo } from "@/components/ui/Logo";
import { Button } from "@/components/ui/Button";
import { ModerationQueue } from "@/features/moderation/ModerationQueue";

export const metadata = {
  title: "Moderation queue — GovGuide",
};

/**
 * Admin review screen for auto-gathered knowledge (B4 / FR-7).
 *
 * NOTE: the backend moderation endpoints carry no authentication, so this page is
 * reachable by anyone who can reach the app. Put it behind auth before exposing
 * the deployment publicly.
 */
export default function ModerationPage() {
  return (
    <div className="gg-screen min-h-screen bg-slate-100">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-slate-50/90 px-5 py-3 backdrop-blur">
        <Logo size={28} />
        <Link href="/">
          <Button variant="secondary">Back to GovGuide</Button>
        </Link>
      </header>
      <main>
        <ModerationQueue />
      </main>
    </div>
  );
}
