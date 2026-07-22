const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-06-20" → "20 Jun 2026" */
export function fmtDate(iso: string): string {
  const p = String(iso).split("-");
  if (p.length !== 3) return iso;
  return `${+p[2]} ${MONTHS[+p[1] - 1]} ${p[0]}`;
}

/** 10550 → "LKR 10,550" */
export function fmtMoney(n: number): string {
  return "LKR " + Number(n).toLocaleString("en-US");
}
