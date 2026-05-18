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
          <span className="eyebrow justify-center text-gold-300 before:bg-gold-400">
            Take The Next Step
          </span>
          <h2 className="mt-4 font-serif text-3xl font-bold tracking-tight text-white sm:text-4xl lg:text-[2.8rem] lg:leading-tight">
            Stop Buying The Promise Of AI. Start Using It.
          </h2>
          <p className="mt-5 text-base leading-relaxed text-navy-100/85 sm:text-lg">
            Whether the right first step is an audit, an efficiency review, or
            a build — we’ll help you scope it on a 30-minute call.
          </p>
          <div className="mt-9 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <a href="#consult" className="btn-primary">
              Schedule a Consultation
            </a>
            <a href="#services" className="btn-secondary">
              See Our Two Service Tracks
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
