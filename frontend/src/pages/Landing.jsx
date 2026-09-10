import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Nav from "../components/Nav";
import Footer from "../components/Footer";
import Logo from "../components/Logo";
import { api } from "../lib/api";
import { useFlags } from "../lib/flags";
import { ChefHat, BookOpen, Sparkles, Printer, Users, Calendar } from "lucide-react";

const TIERS = [
  { key: "little", name: "Little Chefs", ages: "3–5", emoji: "🧒", desc: "Parent-guided cooking, coloring pages, food identification worksheets." },
  { key: "junior", name: "Junior Cooks", ages: "6–9", emoji: "👦", desc: "Supervised recipes, kitchen skills, blank shopping list worksheets." },
  { key: "teen", name: "Teen Kitchen", ages: "10–15", emoji: "👩‍🍳", desc: "Independent recipes plus meal costing worksheets for real-world math." },
  { key: "adult", name: "Mom & Dad — Quick & Easy", ages: "Grown-ups", emoji: "🍳", desc: "Flagship weeknight meals ready in 20–30 minutes." },
];

export default function Landing() {
  const [samples, setSamples] = useState([]);
  const [pricing, setPricing] = useState([]);
  const { flags } = useFlags();

  useEffect(() => {
    api.get("/recipes/samples").then(r => setSamples(r.data)).catch(() => {});
    api.get("/payments/pricing").then(r => setPricing(r.data)).catch(() => {});
  }, []);

  return (
    <div className="min-h-screen">
      <Nav />

      {/* Hero */}
      <section className="paper-tex relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-6 pt-16 pb-24 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7 animate-fade-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-sage/15 text-sage text-xs uppercase tracking-[0.2em] font-bold">
              <Sparkles className="w-3 h-3"/> A Family Kitchen Learning Membership
            </div>
            <h1 className="mt-6 serif text-5xl sm:text-6xl lg:text-7xl font-black leading-[1.05] text-espresso">
              Cook, learn, and <span className="script text-terracotta font-normal text-6xl sm:text-7xl lg:text-8xl">savor</span> together.
            </h1>
            <p className="mt-2 script text-2xl text-terracotta">Cooking and learning activities for homeschool families</p>
            <p className="mt-6 text-lg text-muted2 max-w-xl leading-relaxed">
              Chef Jeana Marie brings more than 30 years of professional cooking experience to your family's kitchen. Every week, members receive age-appropriate recipes, printable learning activities and practical kitchen lessons that help children build confidence and lifelong skills.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link data-testid="hero-cta-join" to="/pricing" className="btn-pill btn-primary">Join the Kitchen Club</Link>
              <a data-testid="hero-cta-samples" href="#samples" className="btn-pill btn-outline">Get 3 Free Recipes</a>
            </div>
            <div className="mt-10 flex items-center gap-8 text-sm text-muted2">
              <div className="flex items-center gap-2"><Calendar className="w-4 h-4 text-sage"/> New recipes weekly</div>
              <div className="flex items-center gap-2"><Printer className="w-4 h-4 text-sage"/> Printable worksheets</div>
            </div>
          </div>

          <div className="lg:col-span-5 relative">
            <div className="relative rounded-3xl overflow-hidden shadow-2xl rotate-1">
              <img src="https://images.unsplash.com/photo-1605433246995-23f532d1e001?w=900" alt="Family cooking" className="w-full h-[520px] object-cover"/>
              <div className="absolute bottom-4 left-4 right-4 glass rounded-2xl p-4">
                <p className="script text-2xl text-terracotta">— Jeana Marie</p>
                <p className="text-sm text-espresso font-medium">"The kitchen is the best classroom I know."</p>
              </div>
            </div>
            <div className="absolute -top-6 -right-6 w-28 h-28 rounded-full bg-cream flex items-center justify-center shadow-xl border-4 border-honey rotate-6">
              <Logo size={80}/>
            </div>
          </div>
        </div>
      </section>

      {/* Age tiers */}
      <section className="max-w-7xl mx-auto px-6 py-20">
        <div className="max-w-2xl">
          <p className="text-xs uppercase tracking-[0.2em] text-sage font-bold">Four Books, One Club</p>
          <h2 className="mt-3 serif text-4xl sm:text-5xl font-black text-espresso">A kitchen learning experience that grows with your family.</h2>
          <p className="mt-4 text-muted2">Age-tiered content updated every week. Parents choose which book each family member can open.</p>
        </div>
        <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {TIERS.map((t) => (
            <div key={t.key} data-testid={`tier-card-${t.key}`} className="card-warm p-6 hover:-translate-y-1 transition-transform">
              <div className="text-5xl">{t.emoji}</div>
              <p className="mt-4 text-xs uppercase tracking-widest text-terracotta font-bold">{t.ages}</p>
              <h3 className="mt-1 serif text-2xl font-bold text-espresso">{t.name}</h3>
              <p className="mt-3 text-sm text-muted2 leading-relaxed">{t.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Free samples */}
      <section id="samples" className="bg-ivory py-20">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex items-end justify-between flex-wrap gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.2em] text-sage font-bold">Free Taste</p>
              <h2 className="mt-3 serif text-4xl sm:text-5xl font-black text-espresso">Three recipes on the house.</h2>
            </div>
            <Link data-testid="samples-see-all" to="/pricing" className="btn-pill btn-primary">Unlock the full archive</Link>
          </div>
          <div className="mt-12 grid md:grid-cols-3 gap-6">
            {samples.map((r) => (
              <div key={r.id} data-testid={`sample-recipe-${r.id}`} className="card-warm overflow-hidden">
                {r.photo_url && <img src={r.photo_url} alt={r.title} className="w-full h-56 object-cover"/>}
                <div className="p-6">
                  <p className="text-xs uppercase tracking-widest text-terracotta font-bold">{r.tier}</p>
                  <h3 className="mt-2 serif text-2xl font-bold text-espresso">{r.title}</h3>
                  <p className="mt-3 text-sm text-muted2 line-clamp-3">{r.description}</p>
                  <div className="mt-4 text-xs text-muted2">{r.prep_time + r.cook_time} min · Serves {r.servings}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Homeschool differentiator */}
      <section className="max-w-7xl mx-auto px-6 py-24 grid lg:grid-cols-2 gap-16 items-center">
        <div>
          <img src="https://images.unsplash.com/photo-1713942589752-6c6bb58ca8b6?w=900" alt="Homeschool cooking" className="rounded-3xl shadow-xl -rotate-1"/>
        </div>
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-sage font-bold">Supplemental Homeschool Enrichment</p>
          <h2 className="mt-3 serif text-4xl sm:text-5xl font-black text-espresso">Printable worksheets that actually teach.</h2>
          <ul className="mt-6 space-y-4">
            <li className="flex gap-4"><Printer className="w-6 h-6 text-terracotta shrink-0 mt-1"/><div><p className="font-bold text-espresso">Coloring pages & food-ID sheets</p><p className="text-sm text-muted2">For Little Chefs learning kitchen tools and food groups.</p></div></li>
            <li className="flex gap-4"><BookOpen className="w-6 h-6 text-terracotta shrink-0 mt-1"/><div><p className="font-bold text-espresso">Meal costing worksheets</p><p className="text-sm text-muted2">Teen Kitchen: real prices, real math, per-serving calculations.</p></div></li>
            <li className="flex gap-4"><Sparkles className="w-6 h-6 text-terracotta shrink-0 mt-1"/><div><p className="font-bold text-espresso">Weekly family learning guides</p><p className="text-sm text-muted2">Every recipe ties to a family learning topic — fractions, nutrition, cultural background.</p></div></li>
          </ul>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="bg-espresso text-cream py-24">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center max-w-2xl mx-auto">
            <p className="text-xs uppercase tracking-[0.2em] text-honey font-bold">Membership</p>
            <h2 className="mt-3 serif text-4xl sm:text-5xl font-black">One club. Every book. Weekly drops.</h2>
            <p className="mt-4 text-cream/70">Cancel future renewals anytime. Your membership remains active through the end of your paid billing period, and your journal and notes remain available in read-only mode while your account stays open.</p>
          </div>
          <div className="mt-14 grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {pricing.map((p) => (
              <div key={p.lookup_key} data-testid={`pricing-${p.lookup_key}`} className={`rounded-2xl p-6 border-2 ${p.lookup_key === "annual" ? "bg-honey text-espresso border-honey" : "bg-espresso border-cream/20"}`}>
                <p className="text-xs uppercase tracking-widest font-bold">{p.name}</p>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-5xl font-black">${(p.amount/100).toFixed(0)}</span>
                  <span className="text-sm opacity-70">.{String(p.amount % 100).padStart(2,'0')}</span>
                </div>
                <p className="text-xs mt-1 opacity-70">Billed every {p.interval === "year" ? "year" : p.lookup_key === "monthly" ? "month" : `${p.lookup_key.replace("month"," months")}`}</p>
                <Link data-testid={`pricing-cta-${p.lookup_key}`} to={`/pricing?plan=${p.lookup_key}`} className={`mt-6 btn-pill w-full justify-center ${p.lookup_key === "annual" ? "btn-primary" : "btn-honey"}`}>Choose {p.name.split(' ')[0]}</Link>
              </div>
            ))}
          </div>
          <p className="text-center mt-10 text-cream/60 text-sm">Bought on Etsy? <Link data-testid="etsy-redeem-link" to="/redeem" className="underline text-honey">Redeem your code here</Link>. Want to <Link data-testid="gift-cta-link" to="/gift" className="underline text-honey">gift a membership</Link>?</p>
        </div>
      </section>

      {/* Footer */}
      <Footer/>
    </div>
  );
}
