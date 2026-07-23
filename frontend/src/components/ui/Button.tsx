import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const variants: Record<Variant, string> = {
  primary: "bg-gradient-to-br from-brand to-brand-dark text-white shadow-brand hover:brightness-105 border-transparent",
  secondary: "bg-white text-ink-700 border-line hover:border-slate-300",
  ghost: "bg-transparent text-ink-500 border-transparent hover:text-ink-900",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[11px] border px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-400",
        variants[variant],
        className,
      )}
    />
  );
}
