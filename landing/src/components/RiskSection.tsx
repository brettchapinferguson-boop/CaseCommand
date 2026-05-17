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
    copy: 'Employees may paste client data, financials, medical records, or privileged information into public AI tools. Once submitted, that data may be stored, logged, or used for training.',
    icon: (
      <Icon>
        <rect x="3" y="11" width="18" height="11" rx="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </Icon>
    ),
  },
  {
    title: 'Employment & HR Risk',
    copy: 'AI used for hiring, performance reviews, scheduling, or discipline can introduce bias and create exposure under federal and state employment law if it is undocumented or unsupervised.',
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
    title: 'Consumer Protection Risk',
    copy: 'AI-generated marketing, advice, quotes, or customer communications can create deceptive practice exposure when claims are inaccurate, unverified, or sent without human review.',
    icon: (
      <Icon>
        <path d="M3 7h18M3 12h18M3 17h12" />
      </Icon>
    ),
  },
  {
    title: 'Cybersecurity Risk',
    copy: 'Unapproved AI tools, browser extensions, and agents create new attack surfaces. They can exfiltrate data, bypass DLP controls, or quietly persist inside employee workflows.',
    icon: (
      <Icon>
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      </Icon>
    ),
  },
  {
    title: 'Vendor & Third-Party Risk',
    copy: 'Most AI vendors push terms that allow broad data use. Without a vendor review process, your business may already be bound to terms that conflict with client contracts and regulatory duties.',
    icon: (
      <Icon>
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
      </Icon>
    ),
  },
  {
    title: 'Intellectual Property Risk',
    copy: 'Generative AI can produce content that mirrors copyrighted material or surrenders rights in your own work product. Without rules, ownership and licensing get blurry fast.',
    icon: (
      <Icon>
        <circle cx="12" cy="12" r="9" />
        <path d="M8 12h8M12 8v8" />
      </Icon>
    ),
  },
  {
    title: 'Hallucination & Accuracy Risk',
    copy: 'AI fabricates citations, statistics, facts, and legal conclusions with full confidence. Without human review procedures, those errors land in client deliverables and public statements.',
    icon: (
      <Icon>
        <path d="M12 2L2 7l10 5 10-5-10-5z" />
        <path d="M2 17l10 5 10-5" />
        <path d="M2 12l10 5 10-5" />
      </Icon>
    ),
  },
  {
    title: 'Regulatory & Audit Readiness Risk',
    copy: 'New AI rules are arriving at the federal, state, and industry level. Without documentation, inventory, and a governance framework, regulators and auditors have no record to review — and neither do you.',
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
          <span className="eyebrow">Risk Landscape</span>
          <h2 className="section-title mt-4">
            Unmanaged AI Creates Invisible Liability.
          </h2>
          <p className="section-intro">
            Eight categories of exposure where most small and mid-sized
            businesses are operating today without governance, documentation, or
            controls.
          </p>
        </div>

        <ul
          role="list"
          className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
        >
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
