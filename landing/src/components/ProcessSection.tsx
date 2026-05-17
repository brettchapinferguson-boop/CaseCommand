const STEPS = [
  {
    title: 'Discovery Call',
    copy: 'A short conversation with leadership to understand the business, current AI exposure, and what success looks like for governance.',
  },
  {
    title: 'Leadership & Employee Intake',
    copy: 'Structured interviews and a confidential employee survey to surface how AI is actually being used across teams and workflows.',
  },
  {
    title: 'AI Usage Mapping',
    copy: 'Every tool, agent, integration, and automation is mapped to the data it touches, the people who use it, and the workflows it supports.',
  },
  {
    title: 'Risk & Compliance Assessment',
    copy: 'Findings are evaluated against confidentiality, employment, consumer, cybersecurity, IP, and regulatory readiness standards.',
  },
  {
    title: 'Executive Report + Governance Roadmap',
    copy: 'You receive a leadership-ready report, a risk scorecard, prioritized recommendations, and a roadmap to implement controls.',
  },
];

export default function ProcessSection() {
  return (
    <section className="section-pad bg-navy-950 text-white">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute"
      />
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow text-gold-300 before:bg-gold-400">
            How It Works
          </span>
          <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.6rem] lg:leading-tight">
            A Clear Path From Hidden AI Use To Documented Governance
          </h2>
          <p className="mt-5 max-w-3xl text-base leading-relaxed text-navy-100/80 sm:text-lg">
            Five practical steps. Built for executives, owners, and operations
            leaders who need answers, not theater.
          </p>
        </div>

        <ol role="list" className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
          {STEPS.map((step, index) => (
            <li
              key={step.title}
              className="relative flex flex-col rounded-xl border border-white/10 bg-white/[0.03] p-6 transition-colors hover:border-gold-400/40 hover:bg-white/[0.06]"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gold-400/40 bg-gold-400/10 font-serif text-base font-bold text-gold-300">
                  {index + 1}
                </span>
                {index < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="hidden h-px flex-1 bg-white/15 lg:block"
                  />
                )}
              </div>
              <h3 className="mt-5 font-serif text-lg font-bold text-white">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-navy-100/75">
                {step.copy}
              </p>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
