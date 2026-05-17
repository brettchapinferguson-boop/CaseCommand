const SOLUTIONS = [
  {
    title: 'AI Acceptable Use Policies',
    copy: 'Plain-English policies tailored to your business, your industry, and the AI tools your team actually uses.',
  },
  {
    title: 'Employee AI Training',
    copy: 'Live and on-demand training that turns policies into day-to-day habits across every department.',
  },
  {
    title: 'Approved AI Tool Lists',
    copy: 'A curated, documented list of vetted AI tools your team is cleared to use — and which ones to avoid.',
  },
  {
    title: 'Vendor Approval Workflows',
    copy: 'A repeatable process for evaluating, approving, and documenting any new AI tool before it touches company data.',
  },
  {
    title: 'Prompt & Data Handling Rules',
    copy: 'Clear standards for what data is allowed in prompts, what must be redacted, and what should never leave the building.',
  },
  {
    title: 'Human Review Procedures',
    copy: 'Defined checkpoints for review, approval, and sign-off on AI-assisted client work, marketing, and decisions.',
  },
  {
    title: 'AI Incident Response Procedures',
    copy: 'A documented playbook for what to do when an AI tool leaks data, fabricates content, or behaves unexpectedly.',
  },
  {
    title: 'Governance Dashboards',
    copy: 'Lightweight dashboards that give leadership visibility into AI usage, policy compliance, and open risks.',
  },
  {
    title: 'Custom AI Workflow Automations',
    copy: 'Where AI makes sense, Anchor designs controlled workflows that capture the upside without giving up oversight.',
  },
  {
    title: 'Ongoing AI Compliance Monitoring',
    copy: 'Quarterly check-ins, policy refreshes, and continued discovery as new AI tools and regulations emerge.',
  },
];

export default function SolutionsSection() {
  return (
    <section id="solutions" className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">From Findings To Fixes</span>
          <h2 className="section-title mt-4">
            From Audit Findings To Practical Solutions
          </h2>
          <p className="section-intro">
            Anchor does not just identify problems. It helps you fix them, with
            governance systems, policies, training, and workflow controls that
            fit how your business actually operates.
          </p>
        </div>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {SOLUTIONS.map((item) => (
            <div
              key={item.title}
              className="group flex h-full flex-col rounded-xl border border-navy-100 bg-white p-6 transition-all duration-300 hover:-translate-y-1 hover:border-gold-300 hover:shadow-cardHover"
            >
              <div className="flex items-center gap-3">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-navy-900 text-gold-300">
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
                    <polyline points="20 6 9 17 4 12" />
                  </svg>
                </span>
                <h3 className="font-serif text-lg font-bold text-navy-900">
                  {item.title}
                </h3>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-charcoal-600 sm:text-[0.95rem]">
                {item.copy}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
