import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import { Plus, BookOpen, Printer, Calculator, NotebookPen, X } from "lucide-react";

const TIERS = { little: "Little Chefs (3–5)", junior: "Junior Cooks (6–9)", teen: "Teen Kitchen (10–15)", adult: "Mom & Dad" };
const EMOJIS = ["🧒","👦","👧","🧑","👨‍🍳","👩‍🍳","🦸","🐻","🐰","🦄"];

export default function Dashboard() {
  const { user } = useAuth();
  const [profiles, setProfiles] = useState([]);
  const [thisWeek, setThisWeek] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ name: "", tier: "junior", avatar_emoji: "🧒" });
  const nav = useNavigate();
  const active = user?.has_active_membership;

  const load = async () => {
    const p = await api.get("/profiles");
    setProfiles(p.data);
    if (active) {
      try { const w = await api.get("/recipes/this-week"); setThisWeek(w.data); } catch {}
    }
  };
  useEffect(() => { load(); }, [active]);

  const addProfile = async (e) => {
    e.preventDefault();
    try {
      await api.post("/profiles", form);
      setShowNew(false);
      setForm({ name: "", tier: "junior", avatar_emoji: "🧒" });
      load();
      toast.success("Profile added");
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const selectProfile = (p) => {
    localStorage.setItem("jmk_profile", JSON.stringify(p));
    nav(`/app/book/${p.tier}`);
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-7xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <p className="script text-3xl text-terracotta">Welcome, {user?.family_name}</p>
            <h1 className="serif text-4xl sm:text-5xl font-black text-espresso mt-1">Who's cooking today?</h1>
          </div>
          {!active && (
            <Link data-testid="dash-upgrade" to="/#pricing" className="btn-pill btn-primary">Activate Membership</Link>
          )}
        </div>

        {!active && (
          <div data-testid="dash-membership-warning" className="mt-6 rounded-xl bg-honey/40 border-2 border-honey p-4 text-espresso">
            <p className="font-bold">Journal is view-only until you activate.</p>
            <p className="text-sm mt-1">Sample recipes and printables are still available. <Link className="underline font-bold" to="/redeem">Have a code?</Link></p>
          </div>
        )}

        <div className="mt-10 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {profiles.map((p) => (
            <button data-testid={`profile-tile-${p.id}`} key={p.id} onClick={() => selectProfile(p)}
              className="card-warm p-6 text-center hover:-translate-y-1 transition-transform">
              <div className="text-6xl">{p.avatar_emoji}</div>
              <p className="mt-3 serif font-bold text-espresso text-lg">{p.name}</p>
              <p className="text-xs text-muted2 mt-1">{TIERS[p.tier]}</p>
            </button>
          ))}
          {profiles.length < 6 && (
            <button data-testid="add-profile-btn" onClick={() => setShowNew(true)} className="card-warm border-2 border-dashed border-terracotta/40 p-6 text-center hover:bg-terracotta/5">
              <Plus className="w-12 h-12 text-terracotta mx-auto"/>
              <p className="mt-3 font-bold text-terracotta">Add Profile</p>
            </button>
          )}
        </div>

        {/* Quick access */}
        <div className="mt-14 grid md:grid-cols-3 gap-6">
          <Link data-testid="quick-printables" to="/app/printables" className="card-warm p-6 hover:-translate-y-1 transition-transform">
            <Printer className="w-8 h-8 text-terracotta"/>
            <h3 className="mt-4 serif text-2xl font-bold text-espresso">Printables Library</h3>
            <p className="text-sm text-muted2 mt-2">Coloring pages, worksheets, shopping lists.</p>
          </Link>
          <Link data-testid="quick-meal-costing" to="/app/meal-costing" className="card-warm p-6 hover:-translate-y-1 transition-transform">
            <Calculator className="w-8 h-8 text-sage"/>
            <h3 className="mt-4 serif text-2xl font-bold text-espresso">Meal Costing Tool</h3>
            <p className="text-sm text-muted2 mt-2">Interactive worksheet for Teen Kitchen.</p>
          </Link>
          <Link data-testid="quick-journal" to="/app/journal" className="card-warm p-6 hover:-translate-y-1 transition-transform">
            <NotebookPen className="w-8 h-8 text-honey"/>
            <h3 className="mt-4 serif text-2xl font-bold text-espresso">Family Journal</h3>
            <p className="text-sm text-muted2 mt-2">Notes, photos, personalized cookbook export.</p>
          </Link>
        </div>

        {/* This week */}
        {active && thisWeek.length > 0 && (
          <div className="mt-14">
            <div className="flex items-baseline justify-between">
              <h2 className="serif text-3xl font-black text-espresso">This Week</h2>
              <p className="text-sm text-muted2">Fresh from Jeana Marie's kitchen</p>
            </div>
            <div className="mt-6 grid md:grid-cols-3 gap-6">
              {thisWeek.slice(0, 6).map((r) => (
                <Link data-testid={`week-recipe-${r.id}`} key={r.id} to={`/app/recipe/${r.id}`} className="card-warm overflow-hidden hover:-translate-y-1 transition-transform">
                  {r.photo_url && <img src={r.photo_url} alt="" className="w-full h-40 object-cover"/>}
                  <div className="p-4">
                    <p className="text-xs uppercase tracking-widest text-terracotta font-bold">{r.tier}</p>
                    <h3 className="mt-1 serif font-bold text-espresso">{r.title}</h3>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>

      {showNew && (
        <div className="fixed inset-0 z-50 bg-espresso/60 flex items-center justify-center p-4" onClick={() => setShowNew(false)}>
          <form onSubmit={addProfile} onClick={(e) => e.stopPropagation()} className="bg-cream rounded-2xl p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="serif text-2xl font-black">New Profile</h3>
              <button type="button" onClick={() => setShowNew(false)} data-testid="profile-modal-close"><X/></button>
            </div>
            <label className="text-sm font-bold">Name</label>
            <input data-testid="profile-form-name" required value={form.name} onChange={(e) => setForm({...form, name: e.target.value})} className="mt-1 mb-4 w-full px-4 py-2 rounded-xl border-2 border-espresso/10"/>
            <label className="text-sm font-bold">Book / Age tier</label>
            <select data-testid="profile-form-tier" value={form.tier} onChange={(e) => setForm({...form, tier: e.target.value})} className="mt-1 mb-4 w-full px-4 py-2 rounded-xl border-2 border-espresso/10 bg-white">
              {Object.entries(TIERS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <label className="text-sm font-bold">Avatar</label>
            <div className="mt-2 grid grid-cols-5 gap-2">
              {EMOJIS.map((e) => (
                <button data-testid={`profile-emoji-${e}`} type="button" key={e} onClick={() => setForm({...form, avatar_emoji: e})}
                  className={`text-3xl p-2 rounded-xl border-2 ${form.avatar_emoji === e ? "border-terracotta bg-terracotta/10" : "border-transparent"}`}>{e}</button>
              ))}
            </div>
            <button data-testid="profile-form-submit" className="mt-6 btn-pill btn-primary w-full justify-center">Create Profile</button>
          </form>
        </div>
      )}
    </div>
  );
}
