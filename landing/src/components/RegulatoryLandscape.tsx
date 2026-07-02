const TODAY = [
  {
    label: 'United States — Federal',
    items: [
      'FTC enforcement under Section 5 against deceptive AI claims and unfair practices',
      'EEOC guidance on AI-assisted employment decisions',
      'NIST AI Risk Management Framework (voluntary, but increasingly referenced)',
      'Federal agency AI guidance (HHS, SEC, CFPB, DOJ)',
    ],
  },
  {
    label: 'United States — State',
    items: [
      'Colorado AI Act (effective 2026) — first comprehensive state AI law',
      'California, Texas, New York, Illinois consumer privacy and AI-specific rules',
      'NYC Local Law 144 — automated employment decision tools',
      'State bar opinions on attorney use of generative AI (CA, FL, NY, others)',
    ],
  },
  {
    label: 'Industry',
    items: [
      'HIPAA implications for AI scribes, intake, and patient communications',
      'FINRA and SEC guidance on AI in financial advice and recordkeeping',
      'Fair Housing and ECOA implications for AI in real estate and lending',
      'Professional malpractice exposure tied to AI-generated work product',
    ],
  },
];

const COMING = [
  'Comprehensive state AI laws modeled on Colorado',
  'Federal action on high-risk AI use cases',
  'Sector regulators issuing binding AI rules (not just guidance)',
  'Court rulings on AI authorship, liability, and reliance',
  'Insurance carriers requiring documented AI governance for coverage',
  'Client procurement requiring AI risk attestations',
];

export default function RegulatoryLandscape() {
  return (
    <section className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">The Regulatory Landscape</span>
          <h2 className="section-title mt-4">
            Light Regulation Today. A Wave Coming Tomorrow.
          </h2>
          <p className="section-intro">
            AI regulation today is a patchwork of agency guidance, state laws,
            and sector rules. That patchwork is expanding quickly. Governance
            is forward-looking work — the businesses that document, train, and
            control AI now will adapt faster than the ones that wait.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {TODAY.map((bucket) => (
            <div
              key={bucket.label}
              className="flex flex-col rounded-2xl border border-navy-100 bg-navy-50/50 p-6"
            >
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-600">
                Today
              </p>
              <h3 className="mt-1.5 font-serif text-lg font-bold text-navy-900">
                {bucket.label}
              </h3>
              <ul role="list" className="mt-4 space-y-2.5">
                {bucket.items.map((item) => (
                  <li
                    key={item}
                    className="flex items-start gap-2.5 text-sm leading-relaxed text-charcoal-700"
                  >
                    <span
                      aria-hidden="true"
                      className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-navy-700"
                    />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 grid gap-6 rounded-2xl border border-navy-900 bg-navy-950 p-7 text-white lg:grid-cols-12 sm:p-9">
          <div className="lg:col-span-5">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              On The Horizon
            </p>
            <h3 className="mt-3 font-serif text-2xl font-bold text-white sm:text-3xl">
              What’s Coming In The Next 24 Months
            </h3>
            <p className="mt-4 text-base leading-relaxed text-navy-100/85">
              The path of AI regulation is predictable in direction even when
              the specifics aren’t. Documentation, policies, and audit trails
              will move from “nice to have” to “the price of doing business” —
              required by insurers, clients, and regulators.
            </p>
          </div>
          <ul role="list" className="lg:col-span-7 grid gap-3 sm:grid-cols-2">
            {COMING.map((item) => (
              <li
                key={item}
                className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-4"
              >
                <svg
                  className="mt-0.5 h-4 w-4 shrink-0 text-gold-300"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <polyline points="9 18 15 12 9 6" />
                </svg>
                <span className="text-sm leading-relaxed text-navy-100/90">
                  {item}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <p className="mx-auto mt-6 max-w-3xl text-center text-xs text-charcoal-500">
          Anchor provides AI governance, compliance, audit, and operational
          consulting. The information above is general and is not legal
          advice. Legal services, if applicable, are provided only through a
          separate attorney-client engagement.
        </p>
      </div>
    </section>
  );
}
