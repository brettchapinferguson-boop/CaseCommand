const PILLARS = [
  {
    title: 'Visibility',
    copy:
      'Know exactly what AI is being used, by whom, on what data, and in which workflows. The audit produces a documented, ongoing inventory — not a one-time guess.',
    icon: (
      <>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
  {
    title: 'Leverage',
    copy:
      'Audits are step one, not the destination. The same team that maps your AI usage can design and build the agents and systems that turn AI into real operational leverage.',
    icon: (
      <>
        <path d="M3 21v-6h6" />
        <path d="M21 3v6h-6" />
        <path d="M21 3l-7 7" />
        <path d="M3 21l7-7" />
      </>
    ),
  },
  {
    title: 'Defensibility',
    copy:
      'A documented record — policies, training, approvals, audit trails — proves your business identified, evaluated, and managed its AI risk for clients, auditors, insurers, and regulators.',
    icon: (
      <>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        <path d="M9 12l2 2 4-4" />
      </>
    ),
  },
];

export default function WhyAnchor() {
  return (
    <section className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Why Anchor</span>
          <h2 className="section-title mt-4">
            Visibility. Leverage. Defensibility.
          </h2>
          <p className="section-intro">
            Anchor AI Solutions exists for businesses that want the upside of
            AI without losing control of their operations, data, reputation,
            or legal exposure. The goal is simple: make AI visible,
            documented, useful, and defensible.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-6 lg:grid-cols-3">
          {PILLARS.map((pillar) => (
            <li
              key={pillar.title}
              className="group flex flex-col rounded-2xl border border-navy-100 bg-navy-50/40 p-8 transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:bg-white hover:shadow-cardHover"
            >
              <span className="inline-flex h-12 w-12 items-center justify-center rounded-lg bg-navy-900 text-gold-300">
                <svg
                  className="h-6 w-6"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  {pillar.icon}
                </svg>
              </span>
              <h3 className="mt-6 font-serif text-2xl font-bold text-navy-900">
                {pillar.title}
              </h3>
              <p className="mt-3 text-base leading-relaxed text-charcoal-700">
                {pillar.copy}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
