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
            AI Governance &amp; Compliance Advisory
          </div>

          <h1 className="mt-6 font-serif text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
            Your Employees Are Already Using AI.
            <span className="block text-gold-300">
              The Question Is Whether Your Business Is Protected.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-navy-100/90">
            Anchor AI Audits &amp; Solutions helps businesses identify hidden AI
            usage, reduce compliance risk, create governance policies, and build
            controlled AI workflows before invisible problems become expensive
            ones.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
            <a href="#consult" className="btn-primary">
              Schedule an AI Compliance Consultation
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
            <a href="#consult" className="btn-secondary">
              Download the AI Risk Checklist
            </a>
          </div>

          <p className="mt-8 max-w-xl text-sm leading-relaxed text-navy-100/70">
            AI governance, compliance audits, policy systems, and workflow
            controls for modern businesses.
          </p>
        </div>

        <div className="lg:col-span-5">
          <Scorecard />
        </div>
      </div>
    </section>
  );
}

function Scorecard() {
  const rows: { label: string; status: 'high' | 'med' | 'low'; note: string }[] = [
    { label: 'Shadow AI Discovery', status: 'high', note: '14 tools detected' },
    { label: 'Acceptable Use Policy', status: 'high', note: 'Missing' },
    { label: 'Data Handling Rules', status: 'med', note: 'Partial' },
    { label: 'Vendor Approval Workflow', status: 'high', note: 'None' },
    { label: 'Incident Response Plan', status: 'high', note: 'None' },
    { label: 'Employee Training', status: 'med', note: 'Informal' },
    { label: 'Human Review of AI Output', status: 'med', note: 'Inconsistent' },
    { label: 'Audit Trail / Logging', status: 'low', note: 'Documented' },
  ];

  const dot = {
    high: 'bg-rose-400',
    med: 'bg-amber-300',
    low: 'bg-emerald-400',
  } as const;

  const pill = {
    high: 'bg-rose-500/15 text-rose-200',
    med: 'bg-amber-400/15 text-amber-200',
    low: 'bg-emerald-500/15 text-emerald-200',
  } as const;

  const pillLabel = {
    high: 'High',
    med: 'Medium',
    low: 'Low',
  } as const;

  return (
    <div className="relative animate-fadeUp">
      <div
        aria-hidden="true"
        className="absolute -inset-3 rounded-[1.5rem] bg-gradient-to-br from-gold-400/20 via-transparent to-navy-700/30 blur-2xl"
      />
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-navy-900/80 backdrop-blur">
        <div className="flex items-center justify-between border-b border-white/10 px-6 py-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Sample Risk Scorecard
            </p>
            <p className="mt-1 text-sm text-navy-100/80">
              Acme Professional Services, LLC
            </p>
          </div>
          <div className="text-right">
            <div className="font-serif text-3xl font-bold text-white">68</div>
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-rose-200">
              Elevated Risk
            </div>
          </div>
        </div>

        <ul className="divide-y divide-white/5">
          {rows.map((row) => (
            <li
              key={row.label}
              className="flex items-center justify-between px-6 py-3.5"
            >
              <div className="flex items-center gap-3">
                <span
                  aria-hidden="true"
                  className={`h-2 w-2 shrink-0 rounded-full ${dot[row.status]}`}
                />
                <div>
                  <p className="text-sm font-medium text-white">{row.label}</p>
                  <p className="text-xs text-navy-100/60">{row.note}</p>
                </div>
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${pill[row.status]}`}
              >
                {pillLabel[row.status]}
              </span>
            </li>
          ))}
        </ul>

        <div className="border-t border-white/10 bg-navy-950/60 px-6 py-3 text-[11px] uppercase tracking-[0.18em] text-navy-100/50">
          Illustrative example — not a real client
        </div>
      </div>
    </div>
  );
}
