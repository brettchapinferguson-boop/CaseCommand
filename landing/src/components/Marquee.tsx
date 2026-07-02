const TERMS = [
  'Agents',
  'Workflow Automations',
  'Bespoke SaaS',
  'Document Pipelines',
  'Internal Knowledge Search',
  'API Integrations',
  'Intake & Triage',
  'Drafting & Review',
  'Governance Programs',
  'Policy Systems',
  'Vendor Reviews',
  'Efficiency Audits',
  'Compliance Audits',
  'Training & Rollout',
];

export default function Marquee() {
  // duplicate the list once so the loop is seamless when the track shifts -50%
  const items = [...TERMS, ...TERMS];
  return (
    <section
      aria-label="What Anchor builds"
      className="marquee-pause border-y border-navy-100 bg-white py-7"
    >
      <div className="relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 left-0 z-10 w-16 bg-gradient-to-r from-white to-transparent sm:w-24"
        />
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-y-0 right-0 z-10 w-16 bg-gradient-to-l from-white to-transparent sm:w-24"
        />
        <div className="marquee-track">
          {items.map((term, i) => (
            <span
              key={`${term}-${i}`}
              className="inline-flex items-center gap-3 whitespace-nowrap font-serif text-xl font-bold text-navy-900 sm:text-2xl"
            >
              {term}
              <svg
                className="h-3 w-3 text-gold-500"
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <circle cx="12" cy="12" r="6" />
              </svg>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}
