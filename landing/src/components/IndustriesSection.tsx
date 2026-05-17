const INDUSTRIES = [
  { name: 'Law Firms', note: 'Privileged data, ethics opinions on AI, document &amp; intake automation.' },
  { name: 'Medical Practices', note: 'HIPAA, AI scribes, intake, patient communications.' },
  { name: 'HR & Staffing', note: 'Hiring, screening, employment-decision tools, audit trail.' },
  { name: 'Financial Services', note: 'Client data, advice generation, FINRA/SEC recordkeeping.' },
  { name: 'Real Estate', note: 'Disclosures, listings, contract drafting, fair-housing risk.' },
  { name: 'Marketing Agencies', note: 'Client data, content claims, IP, and brand exposure.' },
  { name: 'Professional Services', note: 'Confidentiality, deliverables, billing accuracy, IP.' },
  { name: 'Consumer-Facing Businesses', note: 'Customer communications, advertising claims, reviews.' },
];

export default function IndustriesSection() {
  return (
    <section className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Industries Served</span>
          <h2 className="section-title mt-4">
            Built For Firms Where Both Risk And Workflow Matter
          </h2>
          <p className="section-intro">
            Regulated and reputation-sensitive businesses — where an
            unmanaged AI mistake is more than an inconvenience, and where AI
            done right can be a meaningful operational advantage.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {INDUSTRIES.map((industry) => (
            <li
              key={industry.name}
              className="group rounded-xl border border-navy-100 bg-white p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-gold-300 hover:shadow-card"
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
              <p
                className="mt-3 text-sm leading-relaxed text-charcoal-600"
                dangerouslySetInnerHTML={{ __html: industry.note }}
              />
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
