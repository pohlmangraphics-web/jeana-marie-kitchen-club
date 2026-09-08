import { Link } from "react-router-dom";

export const DISCLAIMER = "Jeana Marie's Kitchen Club provides family cooking activities and supplemental educational enrichment. It is not a school, accredited educational program or provider of academic credit. Parents and guardians are responsible for selecting, supervising and documenting activities according to their family's homeschool requirements.";

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-terracotta/10 bg-cream">
      <div className="max-w-7xl mx-auto px-6 py-12 grid md:grid-cols-3 gap-10 text-sm text-muted2">
        <div>
          <p className="script text-3xl text-terracotta">Jeana Marie's</p>
          <p className="serif text-lg text-espresso font-bold -mt-1">Kitchen Club</p>
          <p className="mt-3 italic">Cooking and learning activities for homeschool families.</p>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-sage font-bold">Explore</p>
          <ul className="mt-3 space-y-2">
            <li><Link to="/faq" data-testid="footer-faq" className="hover:text-terracotta">FAQ</Link></li>
            <li><Link to="/terms" data-testid="footer-terms" className="hover:text-terracotta">Terms</Link></li>
            <li><Link to="/privacy" data-testid="footer-privacy" className="hover:text-terracotta">Privacy</Link></li>
            <li><Link to="/gift" data-testid="footer-gift" className="hover:text-terracotta">Gift a Membership</Link></li>
            <li><Link to="/redeem" className="hover:text-terracotta">Redeem a code</Link></li>
          </ul>
        </div>
        <div>
          <p className="text-xs uppercase tracking-widest text-sage font-bold">Important</p>
          <p data-testid="footer-disclaimer" className="mt-3 text-xs leading-relaxed">{DISCLAIMER}</p>
        </div>
      </div>
      <div className="text-center text-xs text-muted2 pb-6">© {new Date().getFullYear()} Jeana Marie's Kitchen Club. Made with love for homeschool families.</div>
    </footer>
  );
}
