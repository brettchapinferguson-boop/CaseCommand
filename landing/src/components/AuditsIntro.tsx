const REASONS = [
  {
    title: 'A Documented Inventory',
    copy:
      'Most leaders have a rough idea of what AI their team uses — few have a written record. The audit produces a living inventory of tools, accounts, agents, and integrations, tied to the data each one touches and the people who use it.',
  },
  {
    title: 'Ongoing Tracking, Not A One-Time Snapshot',
    copy:
      'AI usage changes every quarter. New extensions show up, vendors push new features, and employees adopt new tools faster than IT can review them. Anchor sets up a process to keep the inventory current — not a binder that goes stale in 90 days.',
  },
  {
    title: 'Visibility Across Departments',
    copy:
      'Operations may know one set of tools, marketing another, and the partners a third. The audit surfaces all of it in one view so leadership can make decisions with the full picture.',
  },
  {
    title: 'Forward-Looking Governance',
    copy:
      'Regulation is patchy today and accelerating fast. A defensible governance record — policies, approvals, training, incident response — is the difference between adapting on your terms or scrambling on someone else’s.',
  },
];

export default function AuditsIntro() {
  return (
    <section id="audits" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Track One · Audits</span>
          <h2 className="section-title mt-4">
            Why An AI Audit Is Worth Doing — Even If You Think You Already Know
          </h2>
          <p className="section-intro">
            Audits aren’t just about catching what’s hidden. The
            highest-value outcome is a clear, documented, ongoing picture of
            how AI is being used in your business — and a governance system
            that scales with it.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2">
          {REASONS.map((reason, index) => (
            <article
              key={reason.title}
              className="group flex h-full flex-col rounded-xl border border-navy-100 bg-white p-7 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-gold-300 bg-gold-50 font-serif text-sm font-bold text-gold-700">
                  {String(index + 1).padStart(2, '0')}
                </span>
                <h3 className="font-serif text-lg font-bold text-navy-900">
                  {reason.title}
                </h3>
              </div>
              <p className="mt-3 text-base leading-relaxed text-charcoal-700">
                {reason.copy}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
