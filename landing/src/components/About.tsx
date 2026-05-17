type Member = {
  name: string;
  role: string;
  bio: string;
  highlights: string[];
};

const TEAM: Member[] = [
  {
    name: 'Brett Ferguson',
    role: 'Founder &amp; Principal',
    bio: 'Brett founded Anchor AI Solutions on the same foundation as Ferguson Legal Tech Consulting: that professional firms deserve AI tooling built around how they actually work, and a governance framework that lets them adopt it without taking on hidden liability. He leads audits, governance work, and the strategy side of every solutions engagement.',
    highlights: [
      'Background bridging law, operations, and applied AI',
      'Led the original Ferguson Legal Tech Consulting practice',
      'Focus on practical AI adoption in regulated professional firms',
    ],
  },
  {
    name: 'Senior Software Designer',
    role: 'Engineering &amp; Build Lead',
    bio: 'A seasoned software designer with experience shipping production systems for professional service firms. Leads the build side of Solutions engagements — from architecture and prototyping to deployment, integration, and ongoing support.',
    highlights: [
      'Architecture and design of agent-based AI systems',
      'Integration with legal, medical, and financial tooling stacks',
      'Production deployment, monitoring, and iteration',
    ],
  },
];

export default function About() {
  return (
    <section id="about" className="section-pad bg-white">
      <div className="container-page">
        <div className="grid gap-12 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <span className="eyebrow">About Anchor</span>
            <h2 className="section-title mt-4">
              A Small Team. Built On Practical Experience.
            </h2>
            <p className="section-intro">
              Anchor AI Solutions is small on purpose. The two service tracks
              are run by people who understand both the regulatory side and
              the build side — because the same people doing the governance
              work are doing the implementation work.
            </p>
            <p className="mt-4 max-w-3xl text-base leading-relaxed text-charcoal-700">
              The firm grew out of Ferguson Legal Tech Consulting, which
              focused on bringing real AI tooling — agents, automations, and
              integrations — to legal practitioners who were tired of paying
              for legacy software and getting marketing slides in return.
            </p>
          </div>

          <div className="lg:col-span-7">
            <ul role="list" className="grid gap-6">
              {TEAM.map((member) => (
                <li
                  key={member.name}
                  className="flex flex-col gap-5 rounded-2xl border border-navy-100 bg-navy-50/50 p-6 transition-all duration-300 hover:border-gold-300 hover:bg-white hover:shadow-card sm:flex-row sm:p-7"
                >
                  <div
                    aria-hidden="true"
                    className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-navy-900 font-serif text-2xl font-bold text-gold-300"
                  >
                    {member.name
                      .split(' ')
                      .filter((part) => /^[A-Z]/.test(part))
                      .slice(0, 2)
                      .map((part) => part[0])
                      .join('')}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-serif text-xl font-bold text-navy-900">
                      {member.name}
                    </h3>
                    <p
                      className="mt-0.5 text-sm font-medium text-gold-700"
                      dangerouslySetInnerHTML={{ __html: member.role }}
                    />
                    <p className="mt-3 text-sm leading-relaxed text-charcoal-700">
                      {member.bio}
                    </p>
                    <ul role="list" className="mt-4 space-y-1.5">
                      {member.highlights.map((highlight) => (
                        <li
                          key={highlight}
                          className="flex items-start gap-2.5 text-xs text-charcoal-600 sm:text-sm"
                        >
                          <span
                            aria-hidden="true"
                            className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-gold-500"
                          />
                          <span>{highlight}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                </li>
              ))}
            </ul>

            <p className="mt-4 text-xs text-charcoal-500">
              Bios reflect the current team composition. Names and titles will
              be updated as the team expands.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
