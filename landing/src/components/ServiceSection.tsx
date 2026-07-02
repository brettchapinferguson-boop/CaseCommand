const DELIVERABLES = [
  {
    title: 'AI Usage Inventory',
    copy: 'A documented list of every AI tool, plugin, agent, and automation in use across the business — including the ones leadership already knows about.',
  },
  {
    title: 'Ongoing Tracking System',
    copy: 'A repeatable process to keep the inventory current as employees adopt new tools and vendors push new features.',
  },
  {
    title: 'Risk Scorecard',
    copy: 'A scored snapshot across confidentiality, accuracy, vendor, employment, IP, and regulatory readiness.',
  },
  {
    title: 'Data Privacy Review',
    copy: 'A review of what data is flowing into AI systems and how it maps to client, employee, and regulatory obligations.',
  },
  {
    title: 'Vendor & Tool Assessment',
    copy: 'Plain-English review of AI vendor terms, data-handling commitments, and security posture.',
  },
  {
    title: 'Policy Gap Analysis',
    copy: 'A line-by-line comparison of existing policies against the policies a modern AI-using business needs in place.',
  },
  {
    title: 'Confidential Employee Survey',
    copy: 'A short, anonymized survey that surfaces how employees are actually using AI in their day-to-day work.',
  },
  {
    title: 'Governance Roadmap',
    copy: 'A practical plan for policies, controls, training, and oversight tailored to your industry and size.',
  },
  {
    title: 'Priority Remediation Plan',
    copy: 'A sequenced list of what to fix first, what can wait, and what needs leadership decisions.',
  },
  {
    title: 'Executive Audit Report',
    copy: 'A board- and leadership-ready report summarizing findings, risks, and recommended next steps.',
  },
];

export default function ServiceSection() {
  return (
    <section className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <span className="eyebrow">Audit Deliverables</span>
          <h2 className="section-title mt-4">What You Get From An Audit</h2>
          <p className="section-intro">
            The audit identifies what AI tools are being used, how, by whom,
            and on what data. It produces a documented inventory, a scored
            view of exposure, and a governance plan you can actually
            implement.
          </p>
        </div>

        <ul role="list" className="mt-12 grid gap-4 sm:grid-cols-2">
          {DELIVERABLES.map((item, index) => (
            <li
              key={item.title}
              className="group flex items-start gap-5 rounded-xl border border-navy-100 bg-white p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-gold-300 hover:shadow-card"
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md border border-gold-300 bg-gold-50 font-serif text-base font-bold text-gold-700">
                {String(index + 1).padStart(2, '0')}
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-navy-900">
                  {item.title}
                </h3>
                <p className="mt-1.5 text-sm leading-relaxed text-charcoal-600 sm:text-[0.95rem]">
                  {item.copy}
                </p>
              </div>
            </li>
          ))}
        </ul>

        <div className="mt-12 flex flex-col items-start gap-4 rounded-2xl border border-navy-100 bg-navy-50/60 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
          <p className="max-w-2xl text-base font-medium text-navy-900 sm:text-lg">
            Most audits complete in 2–4 weeks, sized to your business and the
            volume of AI activity discovered. Findings often flow directly
            into a Solutions engagement.
          </p>
          <a href="#consult" className="btn-outline-navy whitespace-nowrap">
            Scope an Audit
          </a>
        </div>
      </div>
    </section>
  );
}
