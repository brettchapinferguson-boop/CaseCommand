import About from './components/About';
import AuditsIntro from './components/AuditsIntro';
import FAQ from './components/FAQ';
import FinalCTA from './components/FinalCTA';
import Footer from './components/Footer';
import Header from './components/Header';
import Hero from './components/Hero';
import IndustriesSection from './components/IndustriesSection';
import LeadForm from './components/LeadForm';
import LegacySoftware from './components/LegacySoftware';
import PackagesSection from './components/PackagesSection';
import ProcessSection from './components/ProcessSection';
import RegulatoryLandscape from './components/RegulatoryLandscape';
import RiskSection from './components/RiskSection';
import ServiceSection from './components/ServiceSection';
import ServicesOverview from './components/ServicesOverview';
import SolutionsIntro from './components/SolutionsIntro';
import SolutionsSection from './components/SolutionsSection';
import WhyAnchor from './components/WhyAnchor';

export default function App() {
  return (
    <>
      <a
        href="#top"
        className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded focus:bg-navy-950 focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white"
      >
        Skip to content
      </a>
      <Header />
      <main>
        <Hero />
        <ServicesOverview />

        {/* ── Audits Track ── */}
        <AuditsIntro />
        <RegulatoryLandscape />
        <RiskSection />
        <ServiceSection />

        {/* ── Solutions Track ── */}
        <SolutionsIntro />
        <LegacySoftware />
        <SolutionsSection />

        <ProcessSection />
        <IndustriesSection />
        <About />
        <WhyAnchor />
        <PackagesSection />
        <LeadForm />
        <FAQ />
        <FinalCTA />
      </main>
      <Footer />
    </>
  );
}
