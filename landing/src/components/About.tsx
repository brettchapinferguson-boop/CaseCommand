import { useReveal } from '../hooks/useReveal';

type Member = {
  name: string;
  role: string;
  initials: string;
  bio: string[];
  highlights: string[];
};

const TEAM: Member[] = [
  {
    name: 'Brett Ferguson',
    role: 'Founder &amp; Principal',
    initials: 'BF',
    bio: [
      'Brett brings 15 years of litigation experience to Anchor and currently practices inside firms that describe themselves as AI-native but, in his experience, are barely using the tools. That gap — between the AI a firm thinks it has and the AI it actually uses — is the founding insight behind Anchor.',
      'He founded Anchor AI Solutions on the same conviction that drove Ferguson Legal Tech Consulting: that professional firms deserve AI that fits how they actually work, and a governance framework that lets them adopt it without taking on hidden liability. Brett leads audits, governance work, and the strategy side of every solutions engagement.',
    ],
    highlights: [
      '15 years of active litigation practice',
      'Working day-to-day inside self-described AI-native firms',
      'Founder of the predecessor practice, Ferguson Legal Tech Consulting',
      'Leads governance, audits, and engagement strategy',
    ],
  },
  {
    name: 'Jon Kass',
    role: 'Partner · Engineering &amp; Build Lead',
    initials: 'JK',
    bio: [
      'Jon is a software designer with 30 years of experience building, shipping, and launching company platforms — from architecture through deployment. He has led the design and engineering of full production systems used by real businesses, and brings that depth to every Anchor build.',
      'On Anchor engagements, Jon leads the build side of Solutions work: agent architecture, integration design, prototyping, and the deployment work that turns a recommendation into a system in daily use.',
    ],
    highlights: [
      '30 years designing and shipping software',
      'Built and launched full company platforms',
      'Architecture, prototyping, integration, deployment',
      'Leads the Build &amp; Refine phases of every engagement',
    ],
  },
];

export default function About() {
  const { ref, shown } = useReveal<HTMLDivElement>();

  return (
    <section id="team" className="section-pad bg-white">
      <div className="container-page">
        <div
          ref={ref}
          className={`grid gap-12 lg:grid-cols-12 lg:gap-16 reveal ${shown ? 'in-view' : ''}`}
        >
          <div className="lg:col-span-5">
            <span className="eyebrow">The Team</span>
            <h2 className="section-title mt-4 text-balance">
              Two People. The Exact Pair This Moment Calls For.
            </h2>
            <p className="section-intro text-pretty">
              Anchor is small on purpose. The strategy, governance, and
              build work is led by people who have done it — inside firms,
              not from the outside.
            </p>
            <p className="mt-4 max-w-2xl text-base leading-relaxed text-charcoal-700">
              That combination — an active litigator working inside
              would-be AI-native firms and a 30-year software designer who
              has launched real platforms — is the exact pair this moment
              calls for.
            </p>
          </div>

          <div className="lg:col-span-7">
            <ul role="list" className="grid gap-6">
              {TEAM.map((member, i) => (
                <li
                  key={member.name}
                  className={`reveal reveal-delay-${i + 1} ${shown ? 'in-view' : ''} flex flex-col gap-5 rounded-2xl border border-navy-100 bg-navy-50/50 p-6 transition-all duration-300 hover:border-gold-300 hover:bg-white hover:shadow-card sm:flex-row sm:p-7`}
                >
                  <div
                    aria-hidden="true"
                    className="flex h-20 w-20 shrink-0 items-center justify-center rounded-xl bg-navy-900 font-serif text-2xl font-bold text-gold-300"
                  >
                    {member.initials}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-serif text-xl font-bold text-navy-900">
                      {member.name}
                    </h3>
                    <p
                      className="mt-0.5 text-sm font-medium text-gold-700"
                      dangerouslySetInnerHTML={{ __html: member.role }}
                    />
                    <div className="mt-3 space-y-3 text-sm leading-relaxed text-charcoal-700">
                      {member.bio.map((paragraph) => (
                        <p key={paragraph}>{paragraph}</p>
                      ))}
                    </div>
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
                          <span dangerouslySetInnerHTML={{ __html: highlight }} />
                        </li>
                      ))}
                    </ul>
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
