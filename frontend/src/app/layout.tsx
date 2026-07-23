import type { Metadata } from "next";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "GovGuide — Government services made clear",
  description:
    "Describe what you need in plain language. GovGuide finds the right Sri Lankan government service and gives you an exact, printable checklist — with the official source for every step.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="font-sans text-slate-900 antialiased">{children}</body>
    </html>
  );
}
