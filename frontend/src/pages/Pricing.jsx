import { useEffect, useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import Nav from "../components/Nav";
import Footer from "../components/Footer";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";

export default function Pricing() {
  const { user, loading } = useAuth();
  const [params] = useSearchParams();
  const nav = useNavigate();
  const [pricing, setPricing] = useState([]);
  const [busy, setBusy] = useState(null);
  const preselected = params.get("plan");

  useEffect(() => {
    api.get("/payments/pricing").then(r => setPricing(r.data)).catch(() => {});
  }, []);

  // Active members shouldn't be here
  useEffect(() => {
    if (!loading && user?.has_active_membership) nav("/app", { replace: true });
  }, [user, loading, nav]);

  const choose = async (lookup_key) => {
    if (!user) {
      // Preserve plan through signup then Auth.jsx completes checkout
      nav(`/auth?mode=register&plan=${lookup_key}`);
      return;
    }
    setBusy(lookup_key);
    try {
      const { data } = await api.post("/payments/checkout", { lookup_key, origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Checkout failed");
      setBusy(null);
    }
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <section className="max-w-7xl mx-auto px-6 py-16">
        <p className="script text-3xl text-terracotta text-center">Membership</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso text-center">
          One club. Every book. Weekly drops.
        </h1>
        <p className="mt-3 text-center text-muted2 max-w-2xl mx-auto">
          {user ? `Welcome, ${user.family_name}. Pick a plan to activate your family membership.` : "Cancel future renewals anytime. Your membership remains active through the end of your paid billing period, and your journal and notes remain available in read-only mode while your account stays open."}
        </p>

        <div className="mt-12 grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {pricing.map((p) => {
            const highlight = p.lookup_key === "annual" || p.lookup_key === preselected;
            return (
              <div key={p.lookup_key} data-testid={`pricing-${p.lookup_key}`}
                className={`rounded-2xl p-6 border-2 ${highlight ? "bg-honey text-espresso border-honey" : "bg-cream border-espresso/10"}`}>
                <p className="text-xs uppercase tracking-widest font-bold">{p.name}</p>
                <div className="mt-3 flex items-baseline gap-1">
                  <span className="text-5xl font-black">${(p.amount / 100).toFixed(0)}</span>
                  <span className="text-sm opacity-70">.{String(p.amount % 100).padStart(2, "0")}</span>
                </div>
                <p className="text-xs mt-1 opacity-70">
                  Billed every {p.interval === "year" ? "year" : p.lookup_key === "monthly" ? "month" : p.lookup_key.replace("month", " months")}
                </p>
                <button data-testid={`pricing-cta-${p.lookup_key}`} onClick={() => choose(p.lookup_key)} disabled={busy === p.lookup_key}
                  className={`mt-6 btn-pill w-full justify-center ${highlight ? "btn-primary" : "btn-outline"}`}>
                  {busy === p.lookup_key ? "…" : (user ? "Continue to checkout" : `Choose ${p.name.split(' ')[0]}`)}
                </button>
              </div>
            );
          })}
        </div>

        <p className="text-center mt-10 text-muted2 text-sm">
          Have an Etsy code instead? <Link data-testid="pricing-redeem" to="/redeem" className="underline text-terracotta font-bold">Redeem it here</Link>.
        </p>
      </section>
      <Footer/>
    </div>
  );
}
