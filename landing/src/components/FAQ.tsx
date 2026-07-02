import { useState } from 'react';

const FAQS = [
  {
    q: 'What’s the difference between Audits and Solutions?',
    a: 'Audits is our governance and compliance practice: visibility into AI use, documented policies, risk scoring, and a defensible record as regulation arrives. Solutions is our build practice: efficiency reviews, agents, automations, integrations, and lightweight SaaS designed for your workflow. The same team runs both, and most engagements eventually touch both.',
  },
  {
    q: 'Do I need an audit before you build anything?',
    a: 'No. Some clients start with a Solutions efficiency review and build first. Others start with an audit because they have a governance gap they want closed before deploying more AI. We scope to the goal, not the order.',
  },
  {
    q: 'Do small businesses really need AI governance?',
    a: 'Yes. Small teams often have the least oversight and the fastest informal adoption. Light regulation today does not equal light regulation tomorrow — and a documented governance record now is the cheapest version of one you will ever produce.',
  },
  {
    q: 'What kind of AI systems do you actually build?',
    a: 'Custom agents (intake, drafting, research, scheduling), workflow automations across the tools you already use, integrations between systems that don’t talk to each other, and lightweight SaaS — internal dashboards, search interfaces, client portals, deadline calculators, and the like. We focus on systems that ship in weeks and stay in daily use.',
  },
  {
    q: 'Can Anchor really replace tools like Harvey or Relativity?',
    a: 'For many firms, yes — particularly small and mid-sized firms paying enterprise prices for generic features. The honest answer is that it depends on what the firm actually uses. Our efficiency review is built to answer exactly that question with a build-vs-buy recommendation.',
  },
  {
    q: 'Do you provide legal advice?',
    a: 'Anchor provides AI governance, compliance, audit, and operational consulting. Legal services, if applicable, are provided only through a separate attorney-client engagement.',
  },
  {
    q: 'What happens after an audit?',
    a: 'You receive a risk report, practical recommendations, policy templates, and a roadmap. From there you can implement internally, engage Anchor for Managed AI Governance, or move into a Solutions engagement to build the workflow improvements the audit surfaced.',
  },
  {
    q: 'What does pricing look like?',
    a: 'Pricing is project-based and scoped to your firm size and the work. We quote after a discovery call. Audit packages start at a fixed scope; Solutions builds are scoped to the system being delivered, with optional ongoing support.',
  },
];

export default function FAQ() {
  const [open, setOpen] = useState<number | null>(0);

  return (
    <section id="faq" className="section-pad bg-navy-50/60">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-4">
            <span className="eyebrow">Frequently Asked</span>
            <h2 className="section-title mt-4">Questions From Leadership</h2>
            <p className="section-intro">
              The most common questions executives and owners ask before
              scoping a first engagement.
            </p>
          </div>

          <div className="lg:col-span-8">
            <ul role="list" className="divide-y divide-navy-100 rounded-2xl border border-navy-100 bg-white shadow-card">
              {FAQS.map((faq, index) => {
                const isOpen = open === index;
                return (
                  <li key={faq.q}>
                    <button
                      type="button"
                      onClick={() => setOpen(isOpen ? null : index)}
                      aria-expanded={isOpen}
                      aria-controls={`faq-panel-${index}`}
                      className="flex w-full items-start justify-between gap-6 px-6 py-5 text-left transition-colors hover:bg-navy-50/60 sm:px-7 sm:py-6"
                    >
                      <span className="font-serif text-base font-bold text-navy-900 sm:text-lg">
                        {faq.q}
                      </span>
                      <span
                        className={`mt-1 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full border transition-all duration-200 ${
                          isOpen
                            ? 'rotate-45 border-navy-900 bg-navy-900 text-white'
                            : 'border-navy-200 text-navy-900'
                        }`}
                        aria-hidden="true"
                      >
                        <svg
                          className="h-3.5 w-3.5"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                        >
                          <line x1="12" y1="5" x2="12" y2="19" />
                          <line x1="5" y1="12" x2="19" y2="12" />
                        </svg>
                      </span>
                    </button>
                    {isOpen && (
                      <div
                        id={`faq-panel-${index}`}
                        className="px-6 pb-6 sm:px-7"
                      >
                        <p className="max-w-3xl text-sm leading-relaxed text-charcoal-600 sm:text-base">
                          {faq.a}
                        </p>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
