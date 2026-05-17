const TRACKS = [
  {
    label: 'Audits Track',
    accent: 'text-gold-300',
    steps: [
      { t: 'Discovery Call', d: 'A short conversation to understand the business, current AI footprint, and what success looks like.' },
      { t: 'Leadership & Employee Intake', d: 'Structured interviews and an anonymized employee survey to map actual usage.' },
      { t: 'AI Inventory & Mapping', d: 'Every tool, agent, integration, and automation is documented and tied to data and workflows.' },
      { t: 'Risk & Regulatory Review', d: 'Findings are evaluated against current and emerging regulatory expectations.' },
      { t: 'Executive Report + Roadmap', d: 'You receive a leadership-ready report, a risk scorecard, and a prioritized governance plan.' },
    ],
  },
  {
    label: 'Solutions Track',
    accent: 'text-emerald-300',
    steps: [
      { t: 'Discovery Call', d: 'A working conversation about the workflow problem you actually want solved.' },
      { t: 'Efficiency Review', d: 'A short engagement that maps the workflow, identifies bottlenecks, and prioritizes AI opportunities.' },
      { t: 'Design & Scope', d: 'A concrete build plan: what gets shipped, on what timeline, and what success looks like.' },
      { t: 'Build & Iterate', d: 'A working prototype in weeks, refined against real use with your team — no year-long implementations.' },
      { t: 'Deploy, Train, Support', d: 'Rollout, training, and ongoing support so the system stays in daily use and keeps improving.' },
    ],
  },
];

export default function ProcessSection() {
  return (
    <section className="section-pad bg-navy-950 text-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow text-gold-300 before:bg-gold-400">
            How We Work
          </span>
          <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.6rem] lg:leading-tight">
            Two Tracks. Five Practical Steps Each.
          </h2>
          <p className="mt-5 max-w-3xl text-base leading-relaxed text-navy-100/80 sm:text-lg">
            Built for executives, owners, and operations leaders who need
            answers and working systems — not theater.
          </p>
        </div>

        <div className="mt-14 space-y-12">
          {TRACKS.map((track) => (
            <div key={track.label}>
              <h3
                className={`text-xs font-semibold uppercase tracking-[0.2em] ${track.accent}`}
              >
                {track.label}
              </h3>
              <ol role="list" className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-5">
                {track.steps.map((step, i) => (
                  <li
                    key={step.t}
                    className="relative flex flex-col rounded-xl border border-white/10 bg-white/[0.03] p-6 transition-colors hover:border-gold-400/40 hover:bg-white/[0.06]"
                  >
                    <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gold-400/40 bg-gold-400/10 font-serif text-base font-bold text-gold-300">
                      {i + 1}
                    </span>
                    <h4 className="mt-4 font-serif text-base font-bold text-white">
                      {step.t}
                    </h4>
                    <p className="mt-2 text-sm leading-relaxed text-navy-100/75">
                      {step.d}
                    </p>
                  </li>
                ))}
              </ol>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
