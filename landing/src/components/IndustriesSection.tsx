const INDUSTRIES = [
  {
    name: 'Law Firms',
    note: 'Privileged data, ethics rules, court orders on AI use.',
  },
  {
    name: 'Medical Practices',
    note: 'HIPAA, patient communications, scribe and intake tools.',
  },
  {
    name: 'HR & Staffing Firms',
    note: 'Hiring, screening, employee data, EEOC exposure.',
  },
  {
    name: 'Financial Services',
    note: 'Client data, advice generation, recordkeeping rules.',
  },
  {
    name: 'Real Estate Brokerages',
    note: 'Disclosures, listings, contract drafting, fair housing.',
  },
  {
    name: 'Marketing Agencies',
    note: 'Client data, content claims, IP, and brand exposure.',
  },
  {
    name: 'Professional Services',
    note: 'Confidentiality, client deliverables, billing accuracy.',
  },
  {
    name: 'Consumer-Facing Businesses',
    note: 'Customer communications, advertising claims, reviews.',
  },
];

export default function IndustriesSection() {
  return (
    <section id="industries" className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Industries Served</span>
          <h2 className="section-title mt-4">
            Built For Businesses Where Risk Matters
          </h2>
          <p className="section-intro">
            Anchor works with regulated and reputation-sensitive businesses —
            the ones where an unmanaged AI mistake is more than an
            inconvenience.
          </p>
        </div>

        <ul
          role="list"
          className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4"
        >
          {INDUSTRIES.map((industry) => (
            <li
              key={industry.name}
              className="group rounded-xl border border-navy-100 bg-navy-50/50 p-5 transition-all duration-300 hover:border-gold-300 hover:bg-white hover:shadow-card"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-9 w-9 items-center justify-center rounded-md bg-navy-900 text-gold-300">
                  <svg
                    className="h-4 w-4"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M3 21h18" />
                    <path d="M5 21V7l8-4v18" />
                    <path d="M19 21V11l-6-4" />
                  </svg>
                </span>
                <h3 className="font-serif text-base font-bold text-navy-900">
                  {industry.name}
                </h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-charcoal-600">
                {industry.note}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
