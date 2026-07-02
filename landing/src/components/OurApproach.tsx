import { useReveal } from '../hooks/useReveal';

const STEPS = [
  {
    title: 'Listen',
    copy: 'A working conversation with leadership. We learn the business, the workflows that matter, the AI already in play, and what success would actually look like.',
  },
  {
    title: 'Audit',
    copy: 'Every engagement starts with an audit — efficiency, governance, or both. We document what’s in use, what’s working, what’s exposed, and where the real opportunities sit.',
  },
  {
    title: 'Design',
    copy: 'We translate findings into a concrete plan: what to fix, what to govern, what to build. No theater, no buzzword roadmaps — a plan you can read and decide on in one sitting.',
  },
  {
    title: 'Build',
    copy: 'Where the right answer is a solution, we build it: agents, automations, integrations, bespoke SaaS, and the policies and training to support them. Working software in weeks, not quarters.',
  },
  {
    title: 'Refine',
    copy: 'Systems get used. Regulations change. We keep iterating with your team so the audit stays current and the solutions stay sharp.',
  },
];

export default function OurApproach() {
  const { ref, shown } = useReveal<HTMLDivElement>();

  return (
    <section id="approach" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div
          ref={ref}
          className={`max-w-3xl reveal ${shown ? 'in-view' : ''}`}
        >
          <span className="eyebrow">Our Approach</span>
          <h2 className="section-title mt-4 text-balance">
            One Practice. One Process. Customized To Every Client.
          </h2>
          <p className="section-intro text-pretty">
            Every business is different, so the foundation of what we do
            starts with an audit — either an efficiency audit of how AI is
            being used (or failing to be used), or a governance audit of
            risk and policy gaps, or both. From there we design the
            customized solution that actually fits.
          </p>
        </div>

        <ol
          role="list"
          className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-5"
        >
          {STEPS.map((step, i) => (
            <li
              key={step.title}
              className={`reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''} relative flex flex-col rounded-2xl border border-navy-100 bg-white p-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-navy-900 font-serif text-base font-bold text-gold-300">
                  {i + 1}
                </span>
                {i < STEPS.length - 1 && (
                  <span
                    aria-hidden="true"
                    className="hidden h-px flex-1 bg-navy-100 lg:block"
                  />
                )}
              </div>
              <h3 className="mt-5 font-serif text-lg font-bold text-navy-900">
                {step.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-charcoal-700">
                {step.copy}
              </p>
            </li>
          ))}
        </ol>

        <div
          className={`mt-12 grid gap-6 reveal ${shown ? 'in-view' : ''} sm:grid-cols-2`}
        >
          <article className="flex flex-col rounded-2xl border border-navy-900 bg-navy-950 p-7 text-white">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Entry Point One
            </p>
            <h3 className="mt-3 font-serif text-2xl font-bold text-white">
              Efficiency Audit
            </h3>
            <p className="mt-3 text-base leading-relaxed text-navy-100/85">
              For firms that have bought into AI but aren’t seeing results.
              We map the workflows, identify the bottlenecks, separate the
              AI hype from the AI fit, and produce a clear, prioritized list
              of where to act — including build-vs-buy recommendations.
            </p>
          </article>
          <article className="flex flex-col rounded-2xl border border-navy-100 bg-white p-7 shadow-card">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-600">
              Entry Point Two
            </p>
            <h3 className="mt-3 font-serif text-2xl font-bold text-navy-900">
              Governance Audit
            </h3>
            <p className="mt-3 text-base leading-relaxed text-charcoal-700">
              For firms that need visibility, a documented inventory, real
              policies, and a defensible record. We map AI usage and the data
              it touches, score the risk, and deliver a governance plan you
              can implement and maintain.
            </p>
          </article>
        </div>
      </div>
    </section>
  );
}
