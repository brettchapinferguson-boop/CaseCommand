import { useReveal } from '../hooks/useReveal';

const VALUES = [
  {
    title: 'A documented picture',
    copy: 'Most leaders have a rough idea of what AI their team uses. The audit produces a written record — tools, accounts, agents, integrations — tied to the data each one touches.',
  },
  {
    title: 'Ongoing, not one-shot',
    copy: 'AI usage changes every quarter. Anchor sets up a process to keep the picture current so the inventory doesn’t turn into a binder that ages out in 90 days.',
  },
  {
    title: 'Where to act first',
    copy: 'The audit produces a prioritized list: efficiency wins to capture, governance gaps to close, and what can safely wait until next quarter.',
  },
  {
    title: 'Forward-looking',
    copy: 'AI regulation today is patchy. It won’t stay that way. A defensible record now is the cheapest version of one you’ll ever produce.',
  },
];

export default function AuditsIntro() {
  const { ref, shown } = useReveal<HTMLDivElement>();
  return (
    <section id="audit" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div
          ref={ref}
          className={`max-w-3xl reveal ${shown ? 'in-view' : ''}`}
        >
          <span className="eyebrow">The Audit Foundation</span>
          <h2 className="section-title mt-4 text-balance">
            Every Engagement Starts Here.
          </h2>
          <p className="section-intro text-pretty">
            The audit is the foundation of what we do. It can focus on
            efficiency (where AI could actually help), on governance (where
            risk is quietly building), or both. Either way, you walk away
            with a clear picture and a prioritized plan.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-5 sm:grid-cols-2">
          {VALUES.map((reason, i) => (
            <li
              key={reason.title}
              className={`reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''} group flex h-full flex-col rounded-xl border border-navy-100 bg-white p-7 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover`}
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gold-300 bg-gold-50 font-serif text-sm font-bold text-gold-700">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="font-serif text-lg font-bold text-navy-900">
                  {reason.title}
                </h3>
              </div>
              <p className="mt-3 text-base leading-relaxed text-charcoal-700">
                {reason.copy}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
