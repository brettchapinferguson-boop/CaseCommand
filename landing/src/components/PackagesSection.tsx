import { useReveal } from '../hooks/useReveal';

type Package = {
  name: string;
  tagline: string;
  description: string;
  bullets: string[];
  featured?: boolean;
  cta: string;
};

const PACKAGES: Package[] = [
  {
    name: 'Discovery Engagement',
    tagline: 'A fast, fixed-scope first step.',
    description:
      'A short engagement to understand the business, look at how AI is being used today, and produce a focused snapshot of where to act.',
    bullets: [
      'Leadership intake interview',
      'Light-touch tool &amp; workflow review',
      'Snapshot findings document',
      'Recommended next engagement scope',
    ],
    cta: 'Start with Discovery',
  },
  {
    name: 'Anchor Audit',
    tagline: 'The full audit — efficiency, governance, or both.',
    description:
      'The flagship audit. Choose efficiency focus, governance focus, or a combined scope. Produces a documented inventory, a risk &amp; opportunity scorecard, and a prioritized action plan.',
    bullets: [
      'Confidential employee usage survey',
      'AI tool, agent, and automation inventory',
      'Risk &amp; opportunity scorecard',
      'Policy gap review (governance)',
      'Workflow &amp; bottleneck map (efficiency)',
      'Executive report &amp; prioritized action plan',
    ],
    featured: true,
    cta: 'Scope the Audit',
  },
  {
    name: 'Anchor Build',
    tagline: 'Customized solutions, designed and shipped.',
    description:
      'Design and build the systems the audit pointed to: agents, workflow automations, integrations, bespoke SaaS, or governance programs. Working software in weeks, with you, not at you.',
    bullets: [
      'Design &amp; scope from audit findings',
      'Working prototype in weeks',
      'Iteration with your team',
      'Deployment, training, documentation',
      'Optional ongoing support &amp; iteration',
    ],
    cta: 'Scope a Build',
  },
];

export default function PackagesSection() {
  const { ref, shown } = useReveal<HTMLDivElement>();
  return (
    <section id="packages" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div
          ref={ref}
          className={`max-w-3xl reveal ${shown ? 'in-view' : ''}`}
        >
          <span className="eyebrow">Engagement Options</span>
          <h2 className="section-title mt-4 text-balance">
            Three Ways To Start.
          </h2>
          <p className="section-intro text-pretty">
            Most clients enter at one of three points. Every engagement is
            scoped to your business size, industry, and goals. Pricing is
            project-based and quoted after a discovery call.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-3">
          {PACKAGES.map((pkg, i) => (
            <article
              key={pkg.name}
              className={[
                `reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''}`,
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

              <h3
                className={`font-serif text-2xl font-bold ${
                  pkg.featured ? 'text-white' : 'text-navy-900'
                }`}
              >
                {pkg.name}
              </h3>
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
                dangerouslySetInnerHTML={{ __html: pkg.description }}
              />

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
                  Project-based, scoped after a discovery call.
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

        <div className="mt-10 rounded-2xl border border-navy-100 bg-white p-6 text-center shadow-card sm:p-8">
          <p className="text-base text-charcoal-700 sm:text-lg">
            <span className="font-semibold text-navy-900">
              Need ongoing support?
            </span>{' '}
            Anchor also engages on retainer — quarterly audits, continued
            build capacity, and a standing partner relationship for firms
            ready to make AI an operational practice, not a one-time project.
          </p>
        </div>
      </div>
    </section>
  );
}
