export default function SolutionsIntro() {
  return (
    <section id="solutions" className="section-pad bg-navy-950 text-white">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-6">
            <span className="eyebrow text-gold-300 before:bg-gold-400">
              Track Two · Solutions
            </span>
            <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.6rem] lg:leading-tight">
              You Were Sold AI. You Probably Got A Chatbot.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-navy-100/85 sm:text-lg">
              Every vendor is selling AI. Most businesses ended up with a
              subscription, a search box, and a vague sense that something is
              supposed to be happening. We build the systems that actually
              produce results — agents, automations, integrations, and
              lightweight software designed around how your business
              actually runs.
            </p>

            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <Stat label="AI tools bought" value="Many" sub="Subscriptions across the team" tone="navy" />
              <Stat label="AI tools actually integrated" value="Few" sub="Used as a chatbot, not a workflow" tone="navy" />
              <Stat label="Anchor approach" value="Build" sub="Designed around the actual workflow" tone="gold" />
              <Stat label="Anchor approach" value="Measure" sub="Tied to a real operational metric" tone="gold" />
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="grid gap-5 sm:grid-cols-2">
              <Card
                title="AI Efficiency Review"
                copy="A focused review of how your team works today and where AI could actually drive efficiency — not where a vendor wants to sell you a license."
                bullets={[
                  'Workflow and bottleneck mapping',
                  'Tool consolidation recommendations',
                  'Build-vs-buy analysis',
                  'A short, prioritized opportunity list',
                ]}
              />
              <Card
                title="Bespoke AI Builds"
                copy="When the right answer is to build, we build. Agents, automations, integrations, and lightweight SaaS designed for your specific workflow and deployed with you, not at you."
                bullets={[
                  'Custom AI agents and assistants',
                  'Workflow automations &amp; integrations',
                  'Lightweight SaaS &amp; internal tools',
                  'Implementation, training, ongoing support',
                ]}
              />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

function Stat({
  label,
  value,
  sub,
  tone,
}: {
  label: string;
  value: string;
  sub: string;
  tone: 'navy' | 'gold';
}) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.04] p-5">
      <p
        className={`text-[10px] font-semibold uppercase tracking-[0.18em] ${
          tone === 'gold' ? 'text-gold-300' : 'text-navy-100/60'
        }`}
      >
        {label}
      </p>
      <p
        className={`mt-2 font-serif text-2xl font-bold ${
          tone === 'gold' ? 'text-gold-200' : 'text-white'
        }`}
      >
        {value}
      </p>
      <p className="mt-1 text-xs leading-relaxed text-navy-100/70">{sub}</p>
    </div>
  );
}

function Card({
  title,
  copy,
  bullets,
}: {
  title: string;
  copy: string;
  bullets: string[];
}) {
  return (
    <div className="flex flex-col rounded-xl border border-white/10 bg-white/[0.04] p-6 transition-colors hover:border-gold-400/40 hover:bg-white/[0.07]">
      <h3 className="font-serif text-xl font-bold text-white">{title}</h3>
      <p className="mt-2 text-sm leading-relaxed text-navy-100/80">{copy}</p>
      <ul role="list" className="mt-4 space-y-2">
        {bullets.map((bullet) => (
          <li key={bullet} className="flex items-start gap-2.5 text-sm text-navy-100/90">
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
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <span dangerouslySetInnerHTML={{ __html: bullet }} />
          </li>
        ))}
      </ul>
    </div>
  );
}
