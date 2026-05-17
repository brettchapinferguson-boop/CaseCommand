type LogoProps = {
  className?: string;
  variant?: 'light' | 'dark';
};

export default function Logo({ className = '', variant = 'dark' }: LogoProps) {
  const stroke = variant === 'light' ? '#ffffff' : '#0f1b35';
  const accent = '#cea84a';
  const wordPrimary = variant === 'light' ? 'text-white' : 'text-navy-900';
  const wordAccent = variant === 'light' ? 'text-gold-300' : 'text-gold-600';

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <svg
        viewBox="0 0 64 64"
        aria-hidden="true"
        className="h-9 w-9 shrink-0"
        fill="none"
      >
        <rect
          width="64"
          height="64"
          rx="10"
          fill={variant === 'light' ? 'rgba(255,255,255,0.06)' : '#f6eed7'}
        />
        <g
          stroke={stroke}
          strokeWidth="3.2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <circle cx="32" cy="18" r="4.5" />
          <line x1="32" y1="22.5" x2="32" y2="50" />
          <path d="M16 40 C16 48 24 52 32 52 C40 52 48 48 48 40" />
          <line x1="22" y1="28" x2="42" y2="28" stroke={accent} />
        </g>
      </svg>
      <div className="flex flex-col leading-tight">
        <span className={`font-serif text-lg font-bold tracking-tight ${wordPrimary}`}>
          Anchor AI Solutions
        </span>
        <span className={`text-[0.66rem] font-semibold uppercase tracking-[0.22em] ${wordAccent}`}>
          Audits · Governance · Bespoke AI
        </span>
      </div>
    </div>
  );
}
