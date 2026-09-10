import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import { Plus, BookOpen, Printer, Calculator, NotebookPen, X, Pencil, Trash2, Library as LibraryIcon, Star, Compass, Mail, CreditCard } from "lucide-react";
import OnboardingTour, { replayTour } from "../components/OnboardingTour";

const TIERS = { little: "Little Chefs (3–5)", junior: "Junior Cooks (6–9)", teen: "Teen Kitchen (10–15)", adult: "Mom & Dad" };
const BOOKS = [
  { key: "little", name: "Little Chefs", ages: "3–5", emoji: "🧒", color: "bg-terracotta/10 border-terracotta/30", accent: "text-terracotta" },
  { key: "junior", name: "Junior Cooks", ages: "6–9", emoji: "👦", color: "bg-honey/30 border-honey", accent: "text-espresso" },
  { key: "teen", name: "Teen Kitchen", ages: "10–15", emoji: "👩‍🍳", color: "bg-sage/15 border-sage/40", accent: "text-sage" },
  { key: "adult", name: "Mom & Dad — Quick & Easy", ages: "Grown-ups", emoji: "🍳", color: "bg-espresso/5 border-espresso/20", accent: "text-espresso" },
];
const EMOJIS = ["🧒","👦","👧","🧑","👨‍🍳","👩‍🍳","🦸","🐻","🐰","🦄"];
const BLANK_FORM = { name: "", tier: "junior", avatar_emoji: "🧒" };

export default function Dashboard() {
  const { user, refresh } = useAuth();
  const [profiles, setProfiles] = useState([]);
  const [thisWeek, setThisWeek] = useState([]);
  const [featured, setFeatured] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(BLANK_FORM);
  const [tourReplay, setTourReplay] = useState(false);
  const nav = useNavigate();
  const active = user?.has_active_membership;

  const load = async () => {
    const p = await api.get("/profiles");
    setProfiles(p.data);
    if (active) {
      try { const w = await api.get("/recipes/this-week"); setThisWeek(w.data); } catch {}
      try { const f = await api.get("/recipes/featured"); setFeatured(f.data.recipe); } catch {}
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [active]);

  const startReplay = () => { replayTour(); setTourReplay(true); };
  const toggleEmailOptin = async () => {
    const next = !(user?.email_optin_weekly !== false);
    try {
      await api.patch("/auth/preferences", { email_optin_weekly: next });
      await refresh();
      toast.success(next ? "Weekly recipe emails: ON" : "Weekly recipe emails: OFF");
    } catch { toast.error("Failed to update preference"); }
  };
  const openPortal = async () => {
    try {
      const { data } = await api.post("/payments/portal", { origin_url: window.location.origin });
      window.location.href = data.portal_url;
    } catch (err) {
      toast.error(err.response?.data?.detail || "Couldn't open the billing portal");
    }
  };

  const sub = user?.subscription;
  const cancelDate = sub?.cancel_at_period_end && sub?.current_period_end
    ? new Date(sub.current_period_end).toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" })
    : null;

  const openCreate = () => { setEditingId(null); setForm(BLANK_FORM); setShowModal(true); };
  const openEdit = (p) => { setEditingId(p.id); setForm({ name: p.name, tier: p.tier, avatar_emoji: p.avatar_emoji }); setShowModal(true); };
  const closeModal = () => { setShowModal(false); setEditingId(null); setForm(BLANK_FORM); };

  const submit = async (e) => {
    e.preventDefault();
    try {
      if (editingId) {
        await api.patch(`/profiles/${editingId}`, form);
        toast.success("Profile updated");
      } else {
        await api.post("/profiles", form);
        toast.success("Profile added");
      }
      closeModal(); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
  };

  const del = async (p) => {
    if (!window.confirm(`Delete ${p.name}'s profile? Their journal, favorites, and "we made this" history will be permanently removed.`)) return;
    try {
      await api.delete(`/profiles/${p.id}`);
      const active_profile = JSON.parse(localStorage.getItem("jmk_profile") || "null");
      if (active_profile?.id === p.id) localStorage.removeItem("jmk_profile");
      toast.success("Profile deleted");
      load();
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
            <Link data-testid="dash-upgrade" to="/pricing" className="btn-pill btn-primary">Activate Membership</Link>
          )}
          {active && sub?.has_stripe_subscription && (
            <div className="flex items-center gap-3 flex-wrap">
              {cancelDate && (
                <span data-testid="dash-cancels-on" className="text-xs uppercase tracking-widest font-bold px-3 py-1.5 rounded-full bg-honey/70 text-espresso border border-honey">
                  Cancels on {cancelDate}
                </span>
              )}
              <button data-testid="dash-manage-membership" onClick={openPortal} className="btn-pill btn-outline text-sm !px-4 !py-2">
                <CreditCard className="w-4 h-4"/> Manage Membership
              </button>
            </div>
          )}
        </div>

        {!active && (
          <div data-testid="dash-membership-warning" className="mt-6 rounded-xl bg-honey/40 border-2 border-honey p-4 text-espresso">
            <p className="font-bold">Your membership has ended — journal is now read-only.</p>
            <p className="text-sm mt-1">
              Your notes, favorites and "We Made This" history stay safely stored. Reactivate any time to add new entries.
              Sample recipes and printables remain available. <Link className="underline font-bold" to="/redeem">Have a code?</Link>
            </p>
          </div>
        )}

        {/* Profile switcher */}
        <div className="mt-10">
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <h2 className="serif text-2xl font-black text-espresso">Family profiles</h2>
            <p className="text-xs text-muted2">Each profile keeps their own journal, favorites and "We Made This" history.</p>
          </div>
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
            {profiles.map((p) => (
              <div key={p.id} data-testid={`profile-tile-${p.id}`} className="card-warm p-6 text-center relative group hover:-translate-y-1 transition-transform">
                <button onClick={() => selectProfile(p)} className="w-full">
                  <div className="text-6xl">{p.avatar_emoji}</div>
                  <p className="mt-3 serif font-bold text-espresso text-lg">{p.name}</p>
                  <p className="text-xs text-muted2 mt-1">{TIERS[p.tier]}</p>
                </button>
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button data-testid={`profile-edit-${p.id}`} onClick={(e) => { e.stopPropagation(); openEdit(p); }} title="Edit"
                    className="p-1.5 rounded-lg bg-honey/60 hover:bg-honey text-espresso"><Pencil className="w-3.5 h-3.5"/></button>
                  <button data-testid={`profile-delete-${p.id}`} onClick={(e) => { e.stopPropagation(); del(p); }} title="Delete"
                    className="p-1.5 rounded-lg bg-terracotta/15 hover:bg-terracotta hover:text-white text-terracotta"><Trash2 className="w-3.5 h-3.5"/></button>
                </div>
              </div>
            ))}
            {profiles.length < 6 && (
              <button data-testid="add-profile-btn" onClick={openCreate} className="card-warm border-2 border-dashed border-terracotta/40 p-6 text-center hover:bg-terracotta/5">
                <Plus className="w-12 h-12 text-terracotta mx-auto"/>
                <p className="mt-3 font-bold text-terracotta">Add Profile</p>
              </button>
            )}
            {profiles.length === 0 && (
              <p data-testid="profiles-empty" className="col-span-full text-sm text-muted2 italic">
                No profiles yet. Add one for each family member — pick a name and default age tier. You can change either anytime and journal history is preserved.
              </p>
            )}
          </div>
        </div>

        {/* Our Recipe Books — always visible to members, independent of profiles */}
        <div className="mt-14">
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <h2 className="serif text-2xl font-black text-espresso">Our Recipe Books</h2>
            <Link data-testid="dash-open-library" to="/app/library" className="text-sm font-bold text-terracotta flex items-center gap-1">
              <LibraryIcon className="w-4 h-4"/> Open Full Library
            </Link>
          </div>
          <p className="text-xs text-muted2 mt-1">Every family membership includes access to all four books. Profiles only personalize favorites and journal — they never restrict recipes.</p>
          <div className="mt-4 grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {BOOKS.map(b => (
              <Link data-testid={`dash-book-${b.key}`} key={b.key} to={`/app/book/${b.key}`}
                className={`rounded-2xl border-2 ${b.color} p-6 hover:-translate-y-1 transition-transform`}>
                <div className="text-4xl">{b.emoji}</div>
                <p className={`mt-3 text-xs uppercase tracking-widest font-bold ${b.accent}`}>{b.ages}</p>
                <h3 className="mt-1 serif text-xl font-bold text-espresso">{b.name}</h3>
                <p className="mt-2 text-xs text-espresso/70">Open book →</p>
              </Link>
            ))}
          </div>
        </div>

        {/* Quick access tools */}
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
            <p className="text-sm text-muted2 mt-2">Notes, favorites, "We Made This" tracker.</p>
          </Link>
        </div>

        {/* Jeana's Pick of the Week */}
        {active && featured && (
          <div className="mt-14">
            <div className="flex items-center gap-2">
              <Star className="w-5 h-5 text-terracotta fill-terracotta"/>
              <p className="script text-2xl text-terracotta">Jeana's Pick of the Week</p>
            </div>
            <Link data-testid="featured-recipe" to={`/app/recipe/${featured.id}`}
              className="mt-3 grid md:grid-cols-5 gap-6 card-warm overflow-hidden hover:-translate-y-1 transition-transform">
              {featured.photo_url && (
                <div className="md:col-span-2 h-56 md:h-auto">
                  <img src={featured.photo_url} alt="" className="w-full h-full object-cover"/>
                </div>
              )}
              <div className={`p-6 flex flex-col justify-center ${featured.photo_url ? "md:col-span-3" : "md:col-span-5"}`}>
                <div className="inline-flex self-start items-center gap-1 px-3 py-1 rounded-full bg-honey text-espresso text-xs uppercase tracking-widest font-bold">
                  <Star className="w-3 h-3 fill-espresso"/> New this week
                </div>
                <p className="mt-3 text-xs uppercase tracking-widest text-sage font-bold">{featured.homeschool_topic || featured.tier}</p>
                <h3 className="mt-1 serif text-3xl font-black text-espresso">{featured.title}</h3>
                <p className="mt-3 text-muted2 line-clamp-3">{featured.description}</p>
                <p className="mt-4 text-xs text-muted2">{featured.prep_time + featured.cook_time} min · Serves {featured.servings}</p>
              </div>
            </Link>
          </div>
        )}

        {/* Other new weekly recipes */}
        {active && thisWeek.length > 0 && (
          <div className="mt-14">
            <div className="flex items-baseline justify-between">
              <h2 className="serif text-3xl font-black text-espresso">{featured ? "Also New This Week" : "This Week"}</h2>
              <p className="text-sm text-muted2">Fresh from Jeana Marie's kitchen</p>
            </div>
            <div className="mt-6 grid md:grid-cols-3 gap-6">
              {thisWeek.filter(r => !featured || r.id !== featured.id).slice(0, 6).map((r) => (
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

        <div className="mt-14 flex flex-wrap gap-3 justify-center">
          <button data-testid="replay-tour" onClick={startReplay} className="btn-pill btn-outline !py-2 !px-4 text-sm">
            <Compass className="w-4 h-4"/> Replay welcome tour
          </button>
          <button data-testid="toggle-email-optin" onClick={toggleEmailOptin} className="btn-pill btn-outline !py-2 !px-4 text-sm">
            <Mail className="w-4 h-4"/> {user?.email_optin_weekly === false ? "Turn on weekly recipe emails" : "Pause weekly recipe emails"}
          </button>
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 z-50 bg-espresso/60 flex items-center justify-center p-4" onClick={closeModal}>
          <form onSubmit={submit} onClick={(e) => e.stopPropagation()} className="bg-cream rounded-2xl p-6 max-w-md w-full">
            <div className="flex justify-between items-center mb-4">
              <h3 className="serif text-2xl font-black">{editingId ? "Edit Profile" : "New Profile"}</h3>
              <button type="button" onClick={closeModal} data-testid="profile-modal-close"><X/></button>
            </div>
            <label className="text-sm font-bold">Name</label>
            <input data-testid="profile-form-name" required value={form.name} onChange={(e) => setForm({...form, name: e.target.value})}
              placeholder="e.g. Ada, Sam, Mom" className="mt-1 mb-4 w-full px-4 py-2 rounded-xl border-2 border-espresso/10"/>
            <label className="text-sm font-bold">Default book / age tier</label>
            <select data-testid="profile-form-tier" value={form.tier} onChange={(e) => setForm({...form, tier: e.target.value})}
              className="mt-1 w-full px-4 py-2 rounded-xl border-2 border-espresso/10 bg-white">
              {Object.entries(TIERS).map(([k,v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <p className="text-xs text-muted2 mt-1">Changing tiers keeps this profile's journal, favorites and "We Made This" history intact.</p>
            <label className="text-sm font-bold mt-4 block">Avatar</label>
            <div className="mt-2 grid grid-cols-5 gap-2">
              {EMOJIS.map((e) => (
                <button data-testid={`profile-emoji-${e}`} type="button" key={e} onClick={() => setForm({...form, avatar_emoji: e})}
                  className={`text-3xl p-2 rounded-xl border-2 ${form.avatar_emoji === e ? "border-terracotta bg-terracotta/10" : "border-transparent"}`}>{e}</button>
              ))}
            </div>
            <button data-testid="profile-form-submit" className="mt-6 btn-pill btn-primary w-full justify-center">
              {editingId ? "Save Changes" : "Create Profile"}
            </button>
          </form>
        </div>
      )}
      <OnboardingTour forceOpen={tourReplay} onClose={() => setTourReplay(false)}/>
    </div>
  );
}
