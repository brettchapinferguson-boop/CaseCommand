import { useReveal } from '../hooks/useReveal';

const PRINCIPLES = [
  {
    title: 'Designed around the work',
    copy: 'We build to the workflow we found in the audit — not a generic feature set the vendor wishes you used.',
  },
  {
    title: 'Working software in weeks',
    copy: 'Anchor ships in cycles: a focused prototype, then iteration with your team until the system is in daily use. No year-long implementations.',
  },
  {
    title: 'Owned by you',
    copy: 'You keep the system, the data, and the documentation. No proprietary lock-in. No mystery infrastructure.',
  },
];

export default function SolutionsIntro() {
  const { ref, shown } = useReveal<HTMLDivElement>();

  return (
    <section id="build" className="section-pad bg-navy-950 text-white">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute"
      />
      <div className="container-page">
        <div
          ref={ref}
          className={`grid gap-12 lg:grid-cols-12 lg:gap-16 reveal ${shown ? 'in-view' : ''}`}
        >
          <div className="lg:col-span-6">
            <span className="eyebrow text-gold-300 before:bg-gold-400">
              From Audit To Build
            </span>
            <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.6rem] lg:leading-tight text-balance">
              You Were Sold AI. You Probably Got A Chatbot.
            </h2>
            <p className="mt-5 max-w-2xl text-base leading-relaxed text-navy-100/85 sm:text-lg text-pretty">
              The audit tells us where AI could actually help. From there we
              design and build the systems that produce results — agents,
              workflow automations, integrations, and bespoke SaaS shaped
              around the way your business actually runs.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-navy-100/80 text-pretty">
              When the right answer is a build, we build. When the right
              answer is an off-the-shelf tool, we’ll tell you that too.
            </p>
          </div>

          <div className="lg:col-span-6">
            <ul role="list" className="grid gap-4 sm:grid-cols-1">
              {PRINCIPLES.map((p, i) => (
                <li
                  key={p.title}
                  className={`reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''} flex gap-5 rounded-xl border border-white/10 bg-white/[0.04] p-6 transition-colors hover:border-gold-400/40 hover:bg-white/[0.07]`}
                >
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-gold-400/15 font-serif text-base font-bold text-gold-300">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <div>
                    <h3 className="font-serif text-lg font-bold text-white">
                      {p.title}
                    </h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-navy-100/80">
                      {p.copy}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
