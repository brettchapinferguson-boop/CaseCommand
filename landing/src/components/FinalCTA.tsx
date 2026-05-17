export default function FinalCTA() {
  return (
    <section className="relative isolate overflow-hidden bg-navy-950 py-20 text-white sm:py-24">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 -z-10 opacity-[0.06] [background-image:linear-gradient(rgba(255,255,255,0.7)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.7)_1px,transparent_1px)] [background-size:48px_48px]"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -top-32 left-1/2 -z-10 h-[420px] w-[420px] -translate-x-1/2 rounded-full bg-gold-500/15 blur-3xl"
      />

      <div className="container-page">
        <div className="mx-auto max-w-3xl text-center">
          <span className="eyebrow text-gold-300 before:bg-gold-400 justify-center">
            Take The Next Step
          </span>
          <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.8rem] lg:leading-tight">
            Bring Your AI Usage Out Of The Shadows.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-navy-100/85 sm:text-lg">
            Get a clear picture of how AI is being used inside your business —
            and what needs to be fixed before it becomes a legal, operational,
            or reputational problem.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href="#consult" className="btn-primary">
              Schedule an AI Compliance Consultation
            </a>
            <a href="#consult" className="btn-secondary">
              Download the AI Risk Checklist
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
