type Risk = { title: string; copy: string; icon: JSX.Element };

const Icon = ({ children }: { children: React.ReactNode }) => (
  <svg
    className="h-6 w-6"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="1.8"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {children}
  </svg>
);

const RISKS: Risk[] = [
  {
    title: 'Data Privacy & Confidentiality',
    copy: 'Client data, financials, medical records, or privileged information may flow into AI tools that store, log, or train on it. Governance defines what data is allowed in which tools — on purpose, in writing.',
    icon: (
      <Icon>
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </Icon>
    ),
  },
  {
    title: 'Employment & HR',
    copy: 'AI used for hiring, performance reviews, scheduling, or discipline raises bias and disparate-impact questions. Documentation and review checkpoints are how you stay defensible.',
    icon: (
      <Icon>
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </Icon>
    ),
  },
  {
    title: 'Consumer & Marketing Claims',
    copy: 'AI-generated marketing copy, advice, quotes, or customer communications can create deceptive-practice exposure when claims are inaccurate or sent without human review.',
    icon: (
      <Icon>
        <path d="M3 7h18M3 12h18M3 17h12" />
      </Icon>
    ),
  },
  {
    title: 'Cybersecurity & Tooling',
    copy: 'Unapproved AI tools, browser extensions, and agents expand the attack surface. An approved-tool list and a vendor review process is the simplest way to close that loop.',
    icon: (
      <Icon>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </Icon>
    ),
  },
  {
    title: 'Vendor & Third-Party Terms',
    copy: 'Most AI vendor terms allow broad data use by default. Reviewing those terms early prevents conflicts with client contracts, NDAs, and regulatory duties downstream.',
    icon: (
      <Icon>
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </Icon>
    ),
  },
  {
    title: 'Intellectual Property',
    copy: 'Generative AI can produce content that mirrors copyrighted material or muddy rights in your own work product. Policies set clear rules on ownership, licensing, and disclosure.',
    icon: (
      <Icon>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 12h8M12 8v8" />
      </Icon>
    ),
  },
  {
    title: 'Accuracy & Reliance',
    copy: 'AI can fabricate citations, statistics, and conclusions with confidence. Human-review procedures define what gets checked, by whom, before it leaves the building.',
    icon: (
      <Icon>
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </Icon>
    ),
  },
  {
    title: 'Audit & Insurance Readiness',
    copy: 'Insurers, clients, and regulators are starting to ask for documented AI governance. A proper record now is faster, cheaper, and more credible than reconstructing one later.',
    icon: (
      <Icon>
        <path d="M9 11l3 3L22 4" />
        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
      </Icon>
    ),
  },
];

export default function RiskSection() {
  return (
    <section className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Where Liability Quietly Builds</span>
          <h2 className="section-title mt-4">
            Eight Categories We Cover In Every Audit.
          </h2>
          <p className="section-intro">
            Each one is manageable on its own. The risk comes from running a
            business in all eight without documentation. The audit gives you a
            scored view of where you stand and a roadmap for what to address
            first.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {RISKS.map((risk) => (
            <li key={risk.title} className="card flex flex-col">
              <span className="inline-flex h-11 w-11 items-center justify-center rounded-lg bg-navy-900 text-gold-300">
                {risk.icon}
              </span>
              <h3 className="mt-5 font-serif text-lg font-bold text-navy-900">
                {risk.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-charcoal-600">
                {risk.copy}
              </p>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
