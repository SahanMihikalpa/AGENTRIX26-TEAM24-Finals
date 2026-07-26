import { cn } from "@/lib/cn";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "ghost";

const variants: Record<Variant, string> = {
  primary: "bg-brand text-white hover:bg-brand-hover border-transparent",
  secondary: "bg-paper-raised text-ink-soft border-paper-border hover:border-[#cfc9bb]",
  ghost: "bg-transparent text-ink-muted border-transparent hover:text-ink",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
}

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[11px] border px-4 py-2.5 text-sm font-semibold transition-colors disabled:cursor-not-allowed disabled:bg-paper-line disabled:text-ink-faint",
        variants[variant],
        className,
      )}
    />
  );
}
