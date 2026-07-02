# Anchor AI Audits & Solutions — Landing Page

Production-ready landing page for Anchor AI Audits & Solutions. Built with
React, TypeScript, Vite, and Tailwind CSS.

## Run locally

```bash
cd landing
npm install
npm run dev
```

Then open http://localhost:5173.

## Build for production

```bash
npm run build      # outputs to landing/dist
npm run preview    # serve the built site locally
```

## Type-check

```bash
npm run lint       # tsc -b across project references
```

## Structure

```
landing/
├── index.html
├── public/
│   ├── favicon.svg
│   └── og-image.svg
├── src/
│   ├── App.tsx
│   ├── main.tsx
│   ├── index.css
│   └── components/
│       ├── FAQ.tsx
│       ├── FinalCTA.tsx
│       ├── Footer.tsx
│       ├── Header.tsx
│       ├── Hero.tsx
│       ├── IndustriesSection.tsx
│       ├── LeadForm.tsx
│       ├── Logo.tsx
│       ├── PackagesSection.tsx
│       ├── ProblemSection.tsx
│       ├── ProcessSection.tsx
│       ├── RiskSection.tsx
│       ├── ServiceSection.tsx
│       ├── SolutionsSection.tsx
│       └── WhyAnchor.tsx
├── tailwind.config.js
├── postcss.config.js
├── vite.config.ts
├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
└── package.json
```

The lead form is fully client-side: validation runs on submit, and on success
the form swaps to a confirmation panel. Wire it to a real backend by replacing
the success-state branch in `src/components/LeadForm.tsx` with a `fetch` call.
