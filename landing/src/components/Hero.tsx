import { useScrollY } from '../hooks/useScroll';

export default function Hero() {
  const y = useScrollY();
  // Parallax factors — background drifts slower than scroll for depth
  const blobA = `translate3d(0, ${y * 0.18}px, 0)`;
  const blobB = `translate3d(0, ${y * -0.12}px, 0)`;
  const grid = `translate3d(0, ${y * 0.05}px, 0)`;

  return (
    <section
      id="top"
      className="relative isolate overflow-hidden bg-navy-950 pt-32 text-white sm:pt-40 lg:pt-44"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.06] [background-image:linear-gradient(rgba(255,255,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:48px_48px]"
        style={{ transform: grid }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 right-[-10%] -z-10 h-[520px] w-[520px] rounded-full bg-gold-500/10 blur-3xl"
        style={{ transform: blobA }}
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -bottom-40 left-[-10%] -z-10 h-[520px] w-[520px] rounded-full bg-navy-700/40 blur-3xl"
        style={{ transform: blobB }}
      />

      <div className="container-page grid items-center gap-14 pb-24 lg:grid-cols-12 lg:gap-12 lg:pb-32">
        <div className="lg:col-span-7">
          <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.04] px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-gold-400" />
            An AI Firm. Built For This Moment.
          </div>

          <h1 className="mt-6 font-serif text-4xl font-bold leading-[1.1] tracking-tight text-white sm:text-5xl lg:text-[3.4rem]">
            AI Was Sold As The Answer.
            <span className="block text-gold-300">
              We Help You Find The Right Question.
            </span>
          </h1>

          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-navy-100/90">
            Anchor AI Solutions helps businesses wade through an overwhelming
            sea of AI products and noise to identify their real problems —
            and then designs the specific tools, workflows, and governance
            that produce real outcomes. Every engagement starts with an
            audit. Every audit ends in a customized solution.
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
            <a href="#approach" className="btn-secondary">
              See How We Work
            </a>
          </div>

          <p className="mt-8 max-w-xl text-sm leading-relaxed text-navy-100/70">
            For law firms, medical practices, financial advisors, agencies,
            and professional service businesses that want more from AI than a
            chatbot — and want it done without taking on hidden liability.
          </p>
        </div>

        <div className="lg:col-span-5">
          <HeroVisual />
        </div>
      </div>
    </section>
  );
}

function HeroVisual() {
  return (
    <div className="relative animate-fadeUp">
      <div
        aria-hidden="true"
        className="absolute -inset-3 rounded-[1.5rem] bg-gradient-to-br from-gold-400/20 via-transparent to-navy-700/30 blur-2xl"
      />
      <div className="relative aspect-square overflow-hidden rounded-2xl border border-white/10 bg-navy-900/80 backdrop-blur">
        <svg
          viewBox="0 0 400 400"
          aria-hidden="true"
          className="absolute inset-0 h-full w-full"
        >
          <defs>
            <radialGradient id="ringGlow" cx="50%" cy="50%" r="55%">
              <stop offset="0" stopColor="#cea84a" stopOpacity="0.18" />
              <stop offset="1" stopColor="#0f1b35" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="ringStroke" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0" stopColor="#dfc070" />
              <stop offset="1" stopColor="#cea84a" stopOpacity="0.4" />
            </linearGradient>
          </defs>

          <rect width="400" height="400" fill="url(#ringGlow)" />

          {/* concentric "anchor" rings */}
          {[160, 130, 100, 70].map((r, i) => (
            <circle
              key={r}
              cx="200"
              cy="200"
              r={r}
              fill="none"
              stroke="url(#ringStroke)"
              strokeWidth={i === 0 ? 1 : 0.6}
              strokeDasharray={i % 2 === 0 ? '2 6' : '4 4'}
              opacity={0.55 - i * 0.08}
            />
          ))}

          {/* anchor mark */}
          <g
            stroke="#dfc070"
            strokeWidth="3.2"
            strokeLinecap="round"
            strokeLinejoin="round"
            fill="none"
            transform="translate(200 200)"
          >
            <circle cx="0" cy="-44" r="9" />
            <line x1="0" y1="-35" x2="0" y2="58" />
            <path d="M-46 30 C-46 60 -22 76 0 76 C22 76 46 60 46 30" />
            <line x1="-26" y1="-14" x2="26" y2="-14" />
          </g>

          {/* satellite nodes — represent listen / audit / build / refine */}
          {[
            { x: 200, y: 50, label: 'Listen' },
            { x: 350, y: 200, label: 'Audit' },
            { x: 200, y: 350, label: 'Build' },
            { x: 50, y: 200, label: 'Refine' },
          ].map((node) => (
            <g key={node.label}>
              <circle cx={node.x} cy={node.y} r="6" fill="#cea84a" />
              <circle cx={node.x} cy={node.y} r="14" fill="none" stroke="#cea84a" strokeOpacity="0.35" />
              <text
                x={node.x}
                y={node.y - 22}
                fill="#dfc070"
                fontSize="11"
                fontWeight="600"
                textAnchor="middle"
                fontFamily="Inter, sans-serif"
                letterSpacing="2"
              >
                {node.label.toUpperCase()}
              </text>
            </g>
          ))}
        </svg>

        <div className="absolute inset-x-0 bottom-0 border-t border-white/10 bg-navy-950/70 px-6 py-3 text-[11px] uppercase tracking-[0.18em] text-navy-100/60">
          Listen · Audit · Build · Refine
        </div>
      </div>
    </div>
  );
}
