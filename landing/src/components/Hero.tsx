export default function Hero() {
  return (
    <section
      id="top"
      className="relative isolate overflow-hidden bg-navy-950 pt-32 text-white sm:pt-40 lg:pt-44"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.06] [background-image:linear-gradient(rgba(255,255,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:48px_48px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 right-[-10%] -z-10 h-[520px] w-[520px] rounded-full bg-gold-500/10 blur-3xl"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-40 left-[-10%] -z-10 h-[520px] w-[520px] rounded-full bg-navy-700/40 blur-3xl"
      />

      <div className="container-page grid items-center gap-14 pb-24 lg:grid-cols-12 lg:gap-12 lg:pb-32">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-gold-400" />
            An AI Firm — Audits &amp; Bespoke Solutions
          </div>

          <h1 className="mt-6 font-serif text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
            Most Businesses Are Buying AI.
            <span className="block text-gold-300">
              Few Are Actually Using It.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-navy-100/90">
            Anchor AI Solutions does two things. We help businesses
            <em className="not-italic font-medium text-white"> govern </em>
            the AI already inside their workflows — and we
            <em className="not-italic font-medium text-white"> build </em>
            the agents, automations, and bespoke software that turn AI from a
            chatbot into operational leverage.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="#consult" className="btn-primary">
              Schedule a Consultation
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
            <a href="#services" className="btn-secondary">
              See Our Two Service Tracks
            </a>
          </div>

          <p className="mt-8 max-w-xl text-sm leading-relaxed text-navy-100/70">
            For law firms, medical practices, financial advisors, agencies, and
            professional service businesses that want AI to do more than
            answer prompts.
          </p>
        </div>

        <div className="lg:col-span-5">
          <DualPanel />
        </div>
      </div>
    </section>
  );
}

function DualPanel() {
  const audits = [
    { label: 'AI Tools In Use', value: '14 inventoried' },
    { label: 'Acceptable Use Policy', value: 'In place · v1.2' },
    { label: 'Vendor Approval Workflow', value: 'Active' },
    { label: 'Quarterly Governance Review', value: 'Next: Jun 14' },
  ];
  const solutions = [
    { label: 'Client Intake Agent', value: '312 inquiries · 24/7' },
    { label: 'Document Drafting Pipeline', value: '4.2 hrs saved / matter' },
    { label: 'Deadline &amp; Calendar Agent', value: 'Synced · Outlook + CRM' },
    { label: 'Internal Knowledge Search', value: 'Indexed · 18k docs' },
  ];

  return (
    <div className="relative animate-fadeUp">
      <div
        aria-hidden="true"
        className="absolute -inset-3 rounded-[1.5rem] bg-gradient-to-br from-gold-400/20 via-transparent to-navy-700/30 blur-2xl"
      />
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-navy-900/80 backdrop-blur">
        <Panel
          eyebrow="Audits"
          title="Governance &amp; Compliance Snapshot"
          rows={audits}
          accent="text-gold-300"
        />
        <div className="h-px bg-white/10" />
        <Panel
          eyebrow="Solutions"
          title="Active AI Systems Built For Client"
          rows={solutions}
          accent="text-emerald-300"
        />
        <div className="border-t border-white/10 bg-navy-950/60 px-6 py-3 text-[11px] uppercase tracking-[0.18em] text-navy-100/50">
          Illustrative dashboard — not a real client
        </div>
      </div>
    </div>
  );
}

function Panel({
  eyebrow,
  title,
  rows,
  accent,
}: {
  eyebrow: string;
  title: string;
  rows: { label: string; value: string }[];
  accent: string;
}) {
  return (
    <div className="px-6 py-5">
      <div className="flex items-center justify-between">
        <p className={`text-xs font-semibold uppercase tracking-[0.18em] ${accent}`}>
          {eyebrow}
        </p>
      </div>
      <p
        className="mt-1 text-sm font-medium text-white"
        dangerouslySetInnerHTML={{ __html: title }}
      />
      <ul className="mt-4 space-y-2.5">
        {rows.map((row) => (
          <li
            key={row.label}
            className="flex items-center justify-between gap-4 text-sm"
          >
            <span className="text-navy-100/80">{row.label}</span>
            <span
              className="font-medium text-white"
              dangerouslySetInnerHTML={{ __html: row.value }}
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
