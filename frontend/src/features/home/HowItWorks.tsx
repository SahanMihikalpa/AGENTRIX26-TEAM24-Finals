const STEPS = [
  {
    n: "01",
    title: "Describe it in your own words",
    body: "No forms or jargon. Say what you need the way you'd tell a friend.",
  },
  {
    n: "02",
    title: "Answer a couple of quick questions",
    body: "Only what we truly need to get your case exactly right — nothing more.",
  },
  {
    n: "03",
    title: "Get your exact checklist, costs & offices",
    body: "A printable Action Pack — with the official source behind every line.",
  },
];

export function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-[1120px] px-7 pt-[clamp(48px,7vw,84px)]">
      <div className="mb-10 max-w-[560px]">
        <div className="mb-3 text-[11.5px] font-bold uppercase tracking-[.14em] text-brand">
          How it works
        </div>
        <h2 className="m-0 font-serif text-[clamp(24px,4vw,34px)] font-semibold leading-tight tracking-[-0.02em]">
          Three calm steps, and you&rsquo;re done.
        </h2>
      </div>
      <div className="grid border-t border-paper-border [grid-template-columns:repeat(auto-fit,minmax(250px,1fr))]">
        {STEPS.map((s, i) => (
          <div
            key={s.n}
            className={
              "py-7 " +
              (i === 0
                ? "border-paper-border pr-6 md:border-r"
                : i === STEPS.length - 1
                  ? "pl-0 md:pl-6"
                  : "border-paper-border px-6 md:border-r")
            }
          >
            <div className="mb-4 font-serif text-[34px] font-semibold leading-none text-[#c9c2b2]">
              {s.n}
            </div>
            <h3 className="m-0 mb-2 text-[17px] font-bold tracking-[-0.01em]">{s.title}</h3>
            <p className="m-0 text-pretty text-sm leading-relaxed text-ink-muted">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
