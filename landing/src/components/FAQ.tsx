import { useState } from 'react';

const FAQS = [
  {
    q: 'Do small businesses really need AI governance?',
    a: 'Yes. Small teams often have the least oversight and the fastest informal adoption. That makes hidden AI risk more likely, not less.',
  },
  {
    q: 'Is this only for companies already using advanced AI?',
    a: 'No. If employees use ChatGPT, Claude, Gemini, Copilot, AI note takers, automations, or browser extensions, the business already has AI governance issues to address.',
  },
  {
    q: 'Do you provide legal advice?',
    a: 'Anchor provides AI governance, compliance, audit, and operational consulting. Legal services, if applicable, are provided only through a separate attorney-client engagement.',
  },
  {
    q: 'What happens after the audit?',
    a: 'The business receives a risk report, practical recommendations, policy templates, and a roadmap for implementing controls.',
  },
  {
    q: 'Can Anchor help implement solutions?',
    a: 'Yes. Anchor can help create policies, employee training, governance workflows, dashboards, and AI automation systems aligned with the audit findings.',
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
              The most common questions executives ask before scoping an AI
              compliance engagement.
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
