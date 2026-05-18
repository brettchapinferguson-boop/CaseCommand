const PAIN_POINTS = [
  'Five-figure annual contracts you can’t easily exit',
  'Generic features that don’t match how your team actually works',
  'Sluggish vendor roadmaps that lag a year behind the AI you actually want',
  'Per-seat pricing that punishes growth and discourages adoption',
  'Black-box AI features bolted onto products that pre-date them',
  'Lock-in via proprietary data formats and migration friction',
];

const REPLACEMENTS = [
  {
    label: 'Legal research &amp; drafting',
    legacy: 'Harvey, Co-Counsel, premium add-ons',
    anchor: 'Domain-tuned drafting agents that pull from your firm’s own work product, with cited output.',
  },
  {
    label: 'Document review &amp; eDiscovery',
    legacy: 'Relativity-style platforms',
    anchor: 'Bespoke review pipelines built for the matter size you actually handle, without the enterprise tax.',
  },
  {
    label: 'Intake &amp; client communication',
    legacy: 'Generic CRMs with chatbot bolt-ons',
    anchor: '24/7 intake agents that screen, qualify, schedule, and route — written in your firm’s voice.',
  },
  {
    label: 'Knowledge management',
    legacy: 'SharePoint, legacy DMS search',
    anchor: 'Internal AI search across your matters, contracts, briefs, and SOPs — answers, not link lists.',
  },
  {
    label: 'Calendaring &amp; deadlines',
    legacy: 'Standalone deadline calculators',
    anchor: 'Agents that compute jurisdiction-aware deadlines and sync directly to Outlook, Google, and your CRM.',
  },
  {
    label: 'Reporting &amp; ops dashboards',
    legacy: 'BI suites with steep learning curves',
    anchor: 'Lightweight dashboards built for the two or three numbers leadership actually checks.',
  },
];

export default function LegacySoftware() {
  return (
    <section className="section-pad bg-white">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <span className="eyebrow">Replacing Legacy Software</span>
            <h2 className="section-title mt-4">
              You Don’t Need A Bigger Enterprise Contract. You Need The Right Tool.
            </h2>
            <p className="section-intro">
              Anchor was built on the same conviction as our predecessor
              practice, Ferguson Legal Tech Consulting: that professional
              firms are overpaying for legacy software that doesn’t fit their
              workflow, and underusing AI that could replace it for a
              fraction of the price.
            </p>

            <ul role="list" className="mt-8 space-y-3">
              {PAIN_POINTS.map((point) => (
                <li key={point} className="flex items-start gap-3">
                  <svg
                    className="mt-1 h-4 w-4 shrink-0 text-rose-500"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                  <span className="text-sm leading-relaxed text-charcoal-700 sm:text-base">
                    {point}
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-7">
            <div className="overflow-hidden rounded-2xl border border-navy-100 shadow-card">
              <div className="grid grid-cols-3 border-b border-navy-100 bg-navy-50 text-[11px] font-semibold uppercase tracking-[0.16em] text-charcoal-600">
                <div className="px-4 py-3 sm:px-5">Function</div>
                <div className="px-4 py-3 sm:px-5">Legacy Approach</div>
                <div className="px-4 py-3 sm:px-5 text-gold-700">Anchor Build</div>
              </div>
              <ul role="list">
                {REPLACEMENTS.map((row, i) => (
                  <li
                    key={row.label}
                    className={`grid grid-cols-3 text-sm transition-colors hover:bg-navy-50/50 ${
                      i % 2 === 1 ? 'bg-navy-50/30' : 'bg-white'
                    }`}
                  >
                    <div
                      className="px-4 py-4 font-medium text-navy-900 sm:px-5"
                      dangerouslySetInnerHTML={{ __html: row.label }}
                    />
                    <div
                      className="px-4 py-4 text-charcoal-600 sm:px-5"
                      dangerouslySetInnerHTML={{ __html: row.legacy }}
                    />
                    <div className="px-4 py-4 text-charcoal-800 sm:px-5">
                      {row.anchor}
                    </div>
                  </li>
                ))}
              </ul>
            </div>

            <p className="mt-4 text-xs text-charcoal-500">
              Product and platform names are referenced for comparison
              purposes only and are trademarks of their respective owners.
              Anchor is not affiliated with or endorsed by any vendor named.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
