const PILLARS = [
  {
    title: 'Visibility',
    copy: 'Know exactly what AI is being used, by whom, on what data, and in which workflows. No more guessing — and no more surprises.',
    icon: (
      <>
        <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
  },
  {
    title: 'Control',
    copy: 'Policies, approval workflows, review checkpoints, and approved-tool lists that put leadership back in the driver’s seat.',
    icon: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.6a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9c.36.15.68.39.93.69" />
      </>
    ),
  },
  {
    title: 'Defensibility',
    copy: 'A documented record that proves your business identified, evaluated, and managed its AI risk — for clients, auditors, insurers, and regulators.',
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
    <section className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Why Anchor</span>
          <h2 className="section-title mt-4">Practical Governance. Not AI Theater.</h2>
          <p className="section-intro">
            Anchor AI Audits &amp; Solutions is built for businesses that want
            the upside of AI without losing control of their operations, data,
            reputation, or legal exposure. The goal is simple: make AI usage
            visible, documented, policy-driven, and defensible.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-6 lg:grid-cols-3">
          {PILLARS.map((pillar) => (
            <li
              key={pillar.title}
              className="group flex flex-col rounded-2xl border border-navy-100 bg-white p-8 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover"
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
              <p className="mt-3 text-base leading-relaxed text-charcoal-600">
                {pillar.copy}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
