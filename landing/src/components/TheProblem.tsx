import { useReveal } from '../hooks/useReveal';

const SYMPTOMS = [
  {
    title: 'A subscription, not a workflow',
    copy: 'Most firms have licenses to two or three AI products and use them as glorified chatbots — never integrated into how the work actually happens.',
  },
  {
    title: 'Promise vs. result',
    copy: 'Vendors sold transformation. Teams got autocomplete. The gap between the pitch and the daily operational gain is the real problem.',
  },
  {
    title: 'Tool fatigue',
    copy: 'New AI products land every week. Without a framework, picking what to adopt — and what to ignore — turns into a permanent open browser tab.',
  },
  {
    title: 'Invisible governance gaps',
    copy: 'Employees adopt tools faster than leadership can review them. The risk is rarely dramatic; it’s slow, quiet, and untracked.',
  },
];

export default function TheProblem() {
  const { ref, shown } = useReveal<HTMLDivElement>();
  return (
    <section id="problem" className="section-pad bg-white">
      <div className="container-page">
        <div
          ref={ref}
          className={`grid gap-12 lg:grid-cols-12 lg:gap-16 reveal ${shown ? 'in-view' : ''}`}
        >
          <div className="lg:col-span-5">
            <span className="eyebrow">The Problem</span>
            <h2 className="section-title mt-4 text-balance">
              AI Is A Solution Looking For A Problem.
            </h2>
            <p className="section-intro text-pretty">
              That’s how most businesses are using AI right now. They heard
              the promises. They bought the tools. They’re still waiting for
              the results. The issue isn’t the technology — it’s the fit
              between the technology and the actual work.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-charcoal-700">
              Anchor turns that equation around. We start with the work, find
              the real problems, and then design the AI — or the governance —
              that fits.
            </p>
          </div>

          <ul role="list" className="lg:col-span-7 grid gap-4 sm:grid-cols-2">
            {SYMPTOMS.map((symptom, i) => (
              <li
                key={symptom.title}
                className={`reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''} group flex flex-col rounded-xl border border-navy-100 bg-navy-50/40 p-6 transition-all duration-300 hover:-translate-y-0.5 hover:border-gold-300 hover:bg-white hover:shadow-card`}
              >
                <span
                  aria-hidden="true"
                  className="font-serif text-2xl font-bold text-gold-600"
                >
                  ·{(i + 1).toString().padStart(2, '0')}
                </span>
                <h3 className="mt-3 font-serif text-lg font-bold text-navy-900">
                  {symptom.title}
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-charcoal-700 sm:text-[0.95rem]">
                  {symptom.copy}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
