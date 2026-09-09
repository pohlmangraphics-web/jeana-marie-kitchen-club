import Nav from "../components/Nav";
import Footer, { DISCLAIMER } from "../components/Footer";

const FAQS = [
  {
    q: "Is Jeana Marie's Kitchen Club a school?",
    a: "No. We provide family cooking activities and supplemental educational enrichment. We are not a school, accredited educational program, or provider of academic credit. Parents and guardians decide how activities fit into their family's homeschool requirements.",
  },
  {
    q: "Who are the four age tiers for?",
    a: "Little Chefs (3–5), Junior Cooks (6–9), Teen Kitchen (10–15), and Mom & Dad — Quick & Easy. Each tier is age-tailored, but every family member gets access with a single family membership.",
  },
  {
    q: "How often are new recipes and activities published?",
    a: "Weekly. Chef Jeana Marie publishes new recipes and printable family learning guides every week across all four age tiers.",
  },
  {
    q: "What comes with a membership?",
    a: "Access to every recipe in every book, all printable activities, meal costing worksheets, shopping list templates, and weekly family learning guides. Members can save notes and favorites for each family member.",
  },
  {
    q: "How does the Etsy redeem code work?",
    a: "Purchase a code on Etsy, create your family account, then enter the code on the Redeem page. Your membership activates immediately for the duration you purchased.",
  },
  {
    q: "Can grandparents buy a gift membership?",
    a: "Yes. Etsy codes are gift-friendly and can be forwarded to the recipient, who redeems the code into their own family account.",
  },
  {
    q: "What happens if I cancel?",
    a: "Your notes, favorites, and journal entries stay saved. New weekly recipes will lock until you renew.",
  },
];

export default function FAQ() {
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-3xl mx-auto px-6 py-16">
        <p className="script text-3xl text-terracotta">Questions & Answers</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Frequently Asked</h1>
        <div className="mt-10 space-y-6">
          {FAQS.map((f, i) => (
            <details key={i} data-testid={`faq-item-${i}`} className="card-warm p-6 group">
              <summary className="serif text-xl font-bold text-espresso cursor-pointer list-none flex justify-between items-center">
                {f.q}
                <span className="text-terracotta group-open:rotate-45 transition-transform text-2xl leading-none">+</span>
              </summary>
              <p className="mt-4 text-muted2 leading-relaxed">{f.a}</p>
            </details>
          ))}
        </div>
        <div data-testid="faq-disclaimer" className="mt-12 rounded-2xl bg-honey/30 border-2 border-honey p-6 text-sm text-espresso leading-relaxed">
          <p className="font-bold mb-2">Important</p>
          <p>{DISCLAIMER}</p>
        </div>
      </div>
      <Footer/>
    </div>
  );
}
