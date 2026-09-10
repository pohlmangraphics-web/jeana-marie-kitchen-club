import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { Search, Filter } from "lucide-react";

const TIERS = [
  { key: "", label: "All Books" },
  { key: "little", label: "Little Chefs (3–5)" },
  { key: "junior", label: "Junior Cooks (6–9)" },
  { key: "teen", label: "Teen Kitchen (10–15)" },
  { key: "adult", label: "Mom & Dad" },
];
const CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Snack", "Dessert", "Holiday"];

export default function Library() {
  const [tier, setTier] = useState("");
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [recipes, setRecipes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  useEffect(() => {
    setLoading(true);
    const params = new URLSearchParams();
    if (tier) params.set("tier", tier);
    if (q) params.set("q", q);
    if (category) params.set("category", category);
    api.get(`/recipes${params.toString() ? `?${params}` : ""}`)
      .then(r => { setRecipes(r.data); setErr(""); })
      .catch(e => setErr(e.response?.status === 402 ? "Active membership required" : "Failed to load"))
      .finally(() => setLoading(false));
  }, [tier, q, category]);

  const grouped = recipes.reduce((acc, r) => {
    (acc[r.tier] = acc[r.tier] || []).push(r);
    return acc;
  }, {});

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="script text-3xl text-terracotta">The Complete Archive</p>
        <h1 className="serif text-4xl sm:text-6xl font-black text-espresso">Recipe Library</h1>
        <p className="mt-2 text-muted2 max-w-2xl">Every recipe Chef Jeana Marie has ever published, across all four books. Available to every active family membership — every book, every family member.</p>

        <div className="mt-8 flex flex-wrap gap-4 items-center">
          <div className="relative flex-1 min-w-[240px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted2"/>
            <input data-testid="library-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search all recipes..."
              className="w-full pl-11 pr-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none bg-white"/>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <Filter className="w-4 h-4 text-muted2"/>
            {TIERS.map(t => (
              <button data-testid={`library-tier-${t.key || "all"}`} key={t.key} onClick={() => setTier(t.key)}
                className={`btn-pill !py-2 !px-4 text-xs ${tier === t.key ? "btn-primary" : "btn-outline"}`}>{t.label}</button>
            ))}
          </div>
        </div>

        <div className="mt-3 flex items-center gap-2 flex-wrap">
          <span className="text-xs uppercase tracking-widest text-sage font-bold">Category:</span>
          <button data-testid="library-cat-all" onClick={() => setCategory("")}
            className={`btn-pill !py-1 !px-3 text-xs ${category === "" ? "btn-primary" : "btn-outline"}`}>Any</button>
          {CATEGORIES.map(c => (
            <button data-testid={`library-cat-${c}`} key={c} onClick={() => setCategory(category === c ? "" : c)}
              className={`btn-pill !py-1 !px-3 text-xs ${category === c ? "btn-primary" : "btn-outline"}`}>{c}</button>
          ))}
        </div>

        {/* Seasonal Collections */}
        <div className="mt-8" data-testid="seasonal-collections">
          <p className="text-xs uppercase tracking-[0.2em] text-sage font-bold">Seasonal Collections</p>
          <div className="mt-3 flex gap-3 flex-wrap">
            <button data-testid="seasonal-holiday" onClick={() => setCategory("Holiday")}
              className="rounded-2xl border-2 border-terracotta/30 bg-terracotta/5 hover:bg-terracotta/10 px-5 py-3 text-left">
              <p className="serif font-bold text-espresso">Holiday Recipes</p>
              <p className="text-xs text-muted2 mt-0.5">Thanksgiving, Christmas, cultural feasts</p>
            </button>
            <button data-testid="seasonal-breakfast" onClick={() => setCategory("Breakfast")}
              className="rounded-2xl border-2 border-honey bg-honey/20 hover:bg-honey/40 px-5 py-3 text-left">
              <p className="serif font-bold text-espresso">Weekend Breakfast</p>
              <p className="text-xs text-muted2 mt-0.5">Slow mornings, big smiles</p>
            </button>
            <button data-testid="seasonal-snack" onClick={() => setCategory("Snack")}
              className="rounded-2xl border-2 border-sage/40 bg-sage/10 hover:bg-sage/20 px-5 py-3 text-left">
              <p className="serif font-bold text-espresso">Afterschool Snacks</p>
              <p className="text-xs text-muted2 mt-0.5">Quick bites the kids can help make</p>
            </button>
          </div>
        </div>

        {err && (
          <p data-testid="library-error" className="mt-6 text-terracotta font-bold">
            {err} — <Link to="/#pricing" className="underline">Activate membership</Link>
          </p>
        )}
        {loading && <p className="mt-8 text-muted2">Loading the archive…</p>}

        {!loading && !err && recipes.length === 0 && (
          <p className="mt-10 text-muted2" data-testid="library-empty">No recipes match your filters.</p>
        )}

        {!loading && !err && tier === "" && (
          <div className="mt-4 text-xs text-muted2">Showing <span className="font-bold text-espresso">{recipes.length}</span> recipes across all books</div>
        )}

        {!loading && !err && tier === "" ? (
          // Grouped by book when viewing all
          <div className="mt-8 space-y-14">
            {TIERS.filter(t => t.key).map(t => grouped[t.key]?.length ? (
              <section key={t.key} data-testid={`library-section-${t.key}`}>
                <div className="flex items-baseline justify-between flex-wrap gap-2">
                  <h2 className="serif text-2xl sm:text-3xl font-black text-espresso">{t.label}</h2>
                  <Link to={`/app/book/${t.key}`} className="text-sm font-bold text-terracotta">Open book →</Link>
                </div>
                <div className="mt-4 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {grouped[t.key].map(r => <RecipeCard key={r.id} r={r}/>)}
                </div>
              </section>
            ) : null)}
          </div>
        ) : (
          !loading && !err && (
            <div className="mt-8 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
              {recipes.map(r => <RecipeCard key={r.id} r={r}/>)}
            </div>
          )
        )}
      </div>
    </div>
  );
}

function RecipeCard({ r }) {
  return (
    <Link data-testid={`library-recipe-${r.id}`} to={`/app/recipe/${r.id}`} className="card-warm overflow-hidden hover:-translate-y-1 transition-transform">
      {r.photo_url && <img src={r.photo_url} alt="" className="w-full h-40 object-cover"/>}
      <div className="p-4">
        <p className="text-xs uppercase tracking-widest text-terracotta font-bold">{r.tier}{r.recipe_card_file_id ? " · 📄 Card" : ""}</p>
        <h3 className="mt-1 serif text-lg font-bold text-espresso">{r.title}</h3>
        <p className="text-xs text-muted2 mt-1">{r.prep_time + r.cook_time} min · Serves {r.servings}</p>
        {r.categories && r.categories.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {r.categories.map(c => <span key={c} className="text-[10px] uppercase tracking-widest bg-honey/40 text-espresso px-2 py-0.5 rounded-full font-bold">{c}</span>)}
          </div>
        )}
      </div>
    </Link>
  );
}
