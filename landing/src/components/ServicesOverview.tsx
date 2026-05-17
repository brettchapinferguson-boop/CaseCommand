export default function ServicesOverview() {
  return (
    <section id="services" className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Two Service Tracks</span>
          <h2 className="section-title mt-4">
            One Firm. Two Distinct Practices.
          </h2>
          <p className="section-intro">
            Anchor AI Solutions operates as an AI firm, not a single-product
            consultancy. We offer two service tracks. Many clients use both;
            most start with one.
          </p>
        </div>

        <div className="mt-12 grid gap-6 lg:grid-cols-2">
          <PillarCard
            label="Track One"
            title="Audits"
            subtitle="Governance &amp; Compliance"
            description="For businesses that want visibility into how AI is being used, a documented inventory of tools and data flows, policy systems that scale, and a defensible record as regulations arrive."
            bullets={[
              'AI usage inventory &amp; ongoing tracking',
              'Acceptable use policies, vendor approval workflows',
              'Regulatory readiness across jurisdictions',
              'Executive audit report &amp; remediation roadmap',
            ]}
            href="#audits"
            cta="See Audit Services"
            tone="navy"
          />
          <PillarCard
            label="Track Two"
            title="Solutions"
            subtitle="Bespoke AI Builds &amp; Efficiency"
            description="For businesses tired of being sold the promise of AI without the operational result. We review how AI could actually drive efficiency in your workflows — and build the agents, automations, integrations, and lightweight software that deliver it."
            bullets={[
              'AI efficiency review &amp; workflow mapping',
              'Custom agents, automations, integrations',
              'Bespoke SaaS that replaces legacy software',
              'Implementation, training, and ongoing support',
            ]}
            href="#solutions"
            cta="See Solutions Work"
            tone="gold"
          />
        </div>

        <p className="mx-auto mt-10 max-w-3xl text-center text-sm leading-relaxed text-charcoal-600 sm:text-base">
          A governance engagement often surfaces workflow opportunities. A
          solutions build often surfaces governance gaps. The two practices
          inform each other — but each stands on its own.
        </p>
      </div>
    </section>
  );
}

function PillarCard({
  label,
  title,
  subtitle,
  description,
  bullets,
  href,
  cta,
  tone,
}: {
  label: string;
  title: string;
  subtitle: string;
  description: string;
  bullets: string[];
  href: string;
  cta: string;
  tone: 'navy' | 'gold';
}) {
  const isNavy = tone === 'navy';
  return (
    <article
      className={`group relative flex flex-col overflow-hidden rounded-2xl border p-8 transition-all duration-300 hover:-translate-y-1 hover:shadow-cardHover ${
        isNavy
          ? 'border-navy-900 bg-navy-950 text-white shadow-cardHover'
          : 'border-navy-100 bg-white text-charcoal-900 shadow-card hover:border-gold-300'
      }`}
    >
      <span
        aria-hidden="true"
        className={`absolute right-0 top-0 h-32 w-32 -translate-y-12 translate-x-12 rounded-full blur-3xl ${
          isNavy ? 'bg-gold-400/15' : 'bg-navy-500/10'
        }`}
      />

      <p
        className={`text-xs font-semibold uppercase tracking-[0.18em] ${
          isNavy ? 'text-gold-300' : 'text-gold-600'
        }`}
      >
        {label}
      </p>
      <h3
        className={`mt-3 font-serif text-3xl font-bold tracking-tight sm:text-4xl ${
          isNavy ? 'text-white' : 'text-navy-900'
        }`}
      >
        {title}
      </h3>
      <p
        className={`mt-1 text-sm font-medium ${
          isNavy ? 'text-navy-100/80' : 'text-charcoal-600'
        }`}
        dangerouslySetInnerHTML={{ __html: subtitle }}
      />

      <p
        className={`mt-5 text-base leading-relaxed ${
          isNavy ? 'text-navy-100/85' : 'text-charcoal-700'
        }`}
      >
        {description}
      </p>

      <ul role="list" className="mt-6 space-y-2.5">
        {bullets.map((bullet) => (
          <li key={bullet} className="flex items-start gap-3">
            <svg
              className={`mt-0.5 h-4 w-4 shrink-0 ${
                isNavy ? 'text-gold-300' : 'text-navy-700'
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
              className={`text-sm ${isNavy ? 'text-white' : 'text-charcoal-800'}`}
              dangerouslySetInnerHTML={{ __html: bullet }}
            />
          </li>
        ))}
      </ul>

      <div className="mt-8">
        <a
          href={href}
          className={`inline-flex items-center gap-2 text-sm font-semibold transition-colors ${
            isNavy ? 'text-gold-300 hover:text-gold-200' : 'text-navy-900 hover:text-navy-700'
          }`}
        >
          {cta}
          <svg
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </a>
      </div>
    </article>
  );
}
