import Logo from './Logo';

const SERVICES = [
  { label: 'Our Approach', href: '#approach' },
  { label: 'The Audit Foundation', href: '#audit' },
  { label: 'What We Build', href: '#build' },
  { label: 'Engagement Options', href: '#packages' },
];

const COMPANY = [
  { label: 'The Team', href: '#team' },
  { label: 'Industries', href: '#industries' },
  { label: 'FAQ', href: '#faq' },
  { label: 'Book a Consultation', href: '#consult' },
];

export default function Footer() {
  const year = new Date().getFullYear();
  return (
    <footer className="bg-navy-950 text-navy-100">
      <div className="container-page py-16">
        <div className="grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <Logo variant="light" />
            <p className="mt-5 max-w-md text-sm leading-relaxed text-navy-100/75">
              An AI firm for businesses that want both governance and real
              operational results. Built on the foundation of Ferguson Legal
              Tech Consulting.
            </p>
            <a
              href="#consult"
              className="mt-6 inline-flex items-center gap-2 rounded-md bg-gold-500 px-5 py-2.5 text-sm font-semibold text-navy-950 transition-colors hover:bg-gold-400"
            >
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
          </div>

          <div className="lg:col-span-3">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Services
            </h3>
            <ul role="list" className="mt-4 space-y-2.5">
              {SERVICES.map((item) => (
                <li key={item.label}>
                  <a
                    href={item.href}
                    className="text-sm text-navy-100/80 transition-colors hover:text-white"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-2">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Company
            </h3>
            <ul role="list" className="mt-4 space-y-2.5">
              {COMPANY.map((item) => (
                <li key={item.label}>
                  <a
                    href={item.href}
                    className="text-sm text-navy-100/80 transition-colors hover:text-white"
                  >
                    {item.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          <div className="lg:col-span-2">
            <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-gold-300">
              Contact
            </h3>
            <ul role="list" className="mt-4 space-y-2.5 text-sm text-navy-100/80">
              <li>
                <a
                  href="mailto:hello@anchoraisolutions.com"
                  className="transition-colors hover:text-white"
                >
                  hello@anchoraisolutions.com
                </a>
              </li>
              <li>By appointment only</li>
            </ul>
          </div>
        </div>

        <div className="mt-14 border-t border-white/10 pt-6">
          <div className="flex flex-col items-start justify-between gap-4 text-xs text-navy-100/60 sm:flex-row sm:items-center">
            <p>
              &copy; {year} Anchor AI Solutions. All rights reserved.
            </p>
            <p className="max-w-2xl sm:text-right">
              Anchor provides AI governance, compliance, audit, and operational
              consulting. Legal services, if applicable, are provided only
              through a separate attorney-client engagement.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}
