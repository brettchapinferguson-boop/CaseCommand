const CAPABILITIES = [
  {
    title: 'AI Agents',
    copy: 'Purpose-built agents that handle intake, triage, drafting, research, summarization, scheduling, and follow-up — operating inside guardrails you define.',
    examples: 'Client intake · Document drafting · Research assistants',
  },
  {
    title: 'Workflow Automations',
    copy: 'End-to-end automations that connect the tools you already use — email, calendar, CRM, document management, billing — and remove the swivel-chair work in between.',
    examples: 'Matter opening · Status updates · Engagement letters',
  },
  {
    title: 'Integrations',
    copy: 'Glue code and API integrations that let your existing systems share data cleanly, so AI can act across them instead of in isolation.',
    examples: 'Clio · NetDocuments · HubSpot · Outlook · QuickBooks',
  },
  {
    title: 'Lightweight SaaS',
    copy: 'Internal tools and small SaaS products built for your firm: dashboards, search interfaces, intake portals, deadline calculators, knowledge libraries.',
    examples: 'Internal search · Client portals · Ops dashboards',
  },
  {
    title: 'Document Pipelines',
    copy: 'Repeatable pipelines for drafting, redlining, summarizing, comparing, and producing client-ready output with human checkpoints baked in.',
    examples: 'Contract review · Brief drafting · Demand letters',
  },
  {
    title: 'Knowledge & Search',
    copy: 'Internal search and retrieval systems indexed on your matters, contracts, briefs, and SOPs — so your team’s answers come from your own work, not the open web.',
    examples: 'Firm-wide knowledge search · Precedent retrieval',
  },
];

export default function SolutionsSection() {
  return (
    <section className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">What We Build</span>
          <h2 className="section-title mt-4">
            From Workflow Map To Working Software
          </h2>
          <p className="section-intro">
            A solutions engagement starts with an efficiency review and ends
            with something deployed. Below is the catalog of what we build —
            each one tailored to the firm, not a one-size-fits-all product.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {CAPABILITIES.map((cap) => (
            <article
              key={cap.title}
              className="group flex h-full flex-col rounded-xl border border-navy-100 bg-white p-6 shadow-card transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover"
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
                    <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                  </svg>
                </span>
                <h3 className="font-serif text-lg font-bold text-navy-900">
                  {cap.title}
                </h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-charcoal-700 sm:text-[0.95rem]">
                {cap.copy}
              </p>
              <p className="mt-4 border-t border-navy-100 pt-3 text-xs font-medium uppercase tracking-[0.14em] text-gold-700">
                Examples
              </p>
              <p className="mt-1 text-xs text-charcoal-500 sm:text-sm">
                {cap.examples}
              </p>
            </article>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start gap-4 rounded-2xl border border-navy-900 bg-navy-950 p-6 text-white sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <p className="max-w-2xl text-base font-medium text-white sm:text-lg">
            Anchor builds in cycles: a short review, a working prototype, then
            iteration with your team until the system is in daily use. No
            year-long implementations.
          </p>
          <a
            href="#consult"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-gold-400 px-5 py-3 text-sm font-semibold text-navy-950 transition-colors hover:bg-gold-300"
          >
            Scope a Build
          </a>
        </div>
      </div>
    </section>
  );
}
