import { useActiveSection } from '../hooks/useScroll';

const SECTIONS = [
  { id: 'problem', label: 'The Problem' },
  { id: 'approach', label: 'Our Approach' },
  { id: 'audit', label: 'The Audit' },
  { id: 'build', label: 'What We Build' },
  { id: 'team', label: 'The Team' },
  { id: 'industries', label: 'Industries' },
  { id: 'packages', label: 'Engagements' },
  { id: 'consult', label: 'Contact' },
];

export default function SideNav() {
  const active = useActiveSection(SECTIONS.map((s) => s.id));

  return (
    <nav
      aria-label="Section navigation"
      className="pointer-events-none fixed left-6 top-1/2 z-40 hidden -translate-y-1/2 xl:block"
    >
      <ul className="pointer-events-auto flex flex-col gap-3.5">
        {SECTIONS.map((section) => {
          const isActive = section.id === active;
          return (
            <li key={section.id}>
              <a
                href={`#${section.id}`}
                className={`group flex items-center gap-3 rounded-full py-1 pl-1 pr-3 text-xs transition-colors ${
                  isActive
                    ? 'side-link-active'
                    : 'text-charcoal-400 hover:text-navy-900'
                }`}
                aria-current={isActive ? 'true' : undefined}
              >
                <span className="side-link-dot" aria-hidden="true" />
                <span className="side-link-label font-medium tracking-wide">
                  {section.label}
                </span>
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
