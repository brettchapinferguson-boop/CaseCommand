const PROBLEMS = [
  'No inventory of AI tools being used',
  'No employee AI usage policy',
  'Confidential data uploaded into public AI systems',
  'AI-generated work sent to customers without review',
  'Unknown agents, automations, or browser extensions',
  'No vendor review or approval process',
  'No incident response plan',
  'No audit trail',
];

export default function ProblemSection() {
  return (
    <section id="problem" className="section-pad bg-white">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <span className="eyebrow">The Reality</span>
            <h2 className="section-title mt-4">
              AI Is Already Inside Your Business — Whether You Approved It Or Not.
            </h2>
            <p className="section-intro">
              Employees may be using public AI tools, browser extensions,
              personal accounts, agents, automations, AI writing tools,
              meeting note takers, and workflow automations — without
              management knowing.
            </p>
            <p className="mt-4 max-w-3xl text-base leading-relaxed text-charcoal-600 sm:text-lg">
              That creates risks involving confidential data, customer
              information, HR decisions, marketing claims, intellectual
              property, cybersecurity, and regulatory exposure. The work has
              already started. The governance has not.
            </p>
          </div>

          <div className="lg:col-span-7">
            <ul
              role="list"
              className="grid gap-3 sm:grid-cols-2"
              aria-label="Common AI governance gaps"
            >
              {PROBLEMS.map((problem) => (
                <li
                  key={problem}
                  className="group flex items-start gap-3 rounded-lg border border-navy-100 bg-navy-50/40 p-4 transition-colors hover:border-gold-300 hover:bg-white"
                >
                  <svg
                    className="mt-0.5 h-5 w-5 shrink-0 text-rose-500"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="8" x2="12" y2="12" />
                    <line x1="12" y1="16" x2="12.01" y2="16" />
                  </svg>
                  <span className="text-sm font-medium leading-snug text-charcoal-800 sm:text-base">
                    {problem}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
