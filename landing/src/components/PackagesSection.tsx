type Package = {
  name: string;
  tagline: string;
  description: string;
  bullets: string[];
  featured?: boolean;
  cta: string;
};

type Track = {
  label: string;
  tagline: string;
  packages: Package[];
};

const TRACKS: Track[] = [
  {
    label: 'Audit Engagements',
    tagline: 'Visibility, governance, and a defensible record.',
    packages: [
      {
        name: 'AI Risk Scan',
        tagline: 'A fast snapshot of AI exposure.',
        description:
          'For businesses that want to understand where they stand before committing to a full audit.',
        bullets: [
          'Leadership questionnaire &amp; interview',
          'Basic risk scorecard',
          'Summary findings document',
        ],
        cta: 'Start with a Risk Scan',
      },
      {
        name: 'AI Compliance Audit',
        tagline: 'Full visibility, governance, and a roadmap.',
        description:
          'The flagship audit for businesses that need a documented inventory, real policies, and a clear path forward.',
        bullets: [
          'Anonymized employee AI usage survey',
          'AI tool, agent, and automation inventory',
          'Risk &amp; regulatory analysis',
          'Policy gap review',
          'Executive audit report &amp; remediation plan',
        ],
        featured: true,
        cta: 'Scope the Audit',
      },
      {
        name: 'Managed AI Governance',
        tagline: 'Ongoing governance support.',
        description:
          'For firms that want governance to keep pace with new tools, new hires, and new regulations.',
        bullets: [
          'Quarterly audits &amp; policy refreshes',
          'Employee training cycles',
          'Vendor &amp; tool review',
          'Governance meetings with leadership',
          'Incident response support',
        ],
        cta: 'Talk About Ongoing Support',
      },
    ],
  },
  {
    label: 'Solutions Engagements',
    tagline: 'AI that actually ships and stays in daily use.',
    packages: [
      {
        name: 'AI Efficiency Review',
        tagline: 'See where AI can actually move the needle.',
        description:
          'A focused engagement to map the workflow, find real opportunities, and produce a build-or-buy recommendation.',
        bullets: [
          'Workflow &amp; bottleneck mapping',
          'Tool consolidation recommendations',
          'Prioritized opportunity list',
          'Build-vs-buy analysis with rough sizing',
        ],
        cta: 'Start with a Review',
      },
      {
        name: 'Bespoke AI Build',
        tagline: 'Working software in weeks, not quarters.',
        description:
          'The flagship build engagement: an agent, automation, integration, or lightweight SaaS designed for your workflow and shipped iteratively.',
        bullets: [
          'Discovery &amp; design',
          'Working prototype in weeks',
          'Iterative refinement with your team',
          'Deployment, training, documentation',
          'Optional ongoing support &amp; iteration',
        ],
        featured: true,
        cta: 'Scope a Build',
      },
      {
        name: 'AI Platform Partner',
        tagline: 'Ongoing AI engineering on retainer.',
        description:
          'For firms ready to use AI across the operation, with a partner who keeps building, integrating, and improving.',
        bullets: [
          'Monthly build capacity for new agents &amp; automations',
          'Maintenance &amp; iteration on existing systems',
          'Integration with new tools as they arrive',
          'Quarterly strategy &amp; roadmap reviews',
          'Coordinated with the Audits track',
        ],
        cta: 'Talk About a Retainer',
      },
    ],
  },
];

export default function PackagesSection() {
  return (
    <section id="packages" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Engagement Options</span>
          <h2 className="section-title mt-4">
            Three Ways To Engage On Each Track
          </h2>
          <p className="section-intro">
            Each engagement is scoped to your firm size, industry, and the
            volume of AI activity already in place. Pricing is project-based
            and quoted after a discovery call.
          </p>
        </div>

        <div className="mt-12 space-y-14">
          {TRACKS.map((track) => (
            <div key={track.label}>
              <div className="flex flex-col items-start justify-between gap-2 sm:flex-row sm:items-end">
                <div>
                  <h3 className="font-serif text-2xl font-bold text-navy-900 sm:text-3xl">
                    {track.label}
                  </h3>
                  <p className="mt-1 text-sm text-charcoal-600 sm:text-base">
                    {track.tagline}
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-6 lg:grid-cols-3">
                {track.packages.map((pkg) => (
                  <article
                    key={pkg.name}
                    className={[
                      'relative flex flex-col rounded-2xl border p-7 transition-all duration-300 hover:-translate-y-1',
                      pkg.featured
                        ? 'border-navy-900 bg-navy-950 text-white shadow-cardHover'
                        : 'border-navy-100 bg-white shadow-card hover:border-gold-300 hover:shadow-cardHover',
                    ].join(' ')}
                  >
                    {pkg.featured && (
                      <span className="absolute -top-3 left-7 inline-flex items-center rounded-full bg-gold-400 px-3 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-navy-950">
                        Most Common
                      </span>
                    )}

                    <h4
                      className={`font-serif text-xl font-bold ${
                        pkg.featured ? 'text-white' : 'text-navy-900'
                      }`}
                    >
                      {pkg.name}
                    </h4>
                    <p
                      className={`mt-1.5 text-sm font-medium ${
                        pkg.featured ? 'text-gold-300' : 'text-gold-600'
                      }`}
                    >
                      {pkg.tagline}
                    </p>
                    <p
                      className={`mt-4 text-sm leading-relaxed sm:text-[0.95rem] ${
                        pkg.featured ? 'text-navy-100/85' : 'text-charcoal-600'
                      }`}
                    >
                      {pkg.description}
                    </p>

                    <ul role="list" className="mt-6 space-y-2.5">
                      {pkg.bullets.map((bullet) => (
                        <li key={bullet} className="flex items-start gap-3">
                          <svg
                            className={`mt-0.5 h-4 w-4 shrink-0 ${
                              pkg.featured ? 'text-gold-300' : 'text-navy-700'
                            }`}
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <polyline points="20 6 9 17 4 12" />
                          </svg>
                          <span
                            className={`text-sm ${
                              pkg.featured ? 'text-white' : 'text-charcoal-800'
                            }`}
                            dangerouslySetInnerHTML={{ __html: bullet }}
                          />
                        </li>
                      ))}
                    </ul>

                    <div
                      className={`mt-7 border-t pt-5 ${
                        pkg.featured ? 'border-white/10' : 'border-navy-100'
                      }`}
                    >
                      <p
                        className={`text-xs font-semibold uppercase tracking-[0.18em] ${
                          pkg.featured ? 'text-gold-300' : 'text-gold-600'
                        }`}
                      >
                        Investment
                      </p>
                      <p
                        className={`mt-1 text-sm ${
                          pkg.featured ? 'text-navy-100/85' : 'text-charcoal-600'
                        }`}
                      >
                        Custom pricing based on business size and scope.
                      </p>
                    </div>

                    <a
                      href="#consult"
                      className={`mt-7 inline-flex items-center justify-center gap-2 rounded-md px-5 py-3 text-sm font-semibold transition-all duration-200 ${
                        pkg.featured
                          ? 'bg-gold-400 text-navy-950 hover:bg-gold-300'
                          : 'border border-navy-900 text-navy-900 hover:bg-navy-900 hover:text-white'
                      }`}
                    >
                      {pkg.cta}
                    </a>
                  </article>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
