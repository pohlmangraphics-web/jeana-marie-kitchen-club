import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { Search } from "lucide-react";

const TIERS = { little: "Little Chefs", junior: "Junior Cooks", teen: "Teen Kitchen", adult: "Mom & Dad — Quick & Easy" };

export default function Book() {
  const { tier } = useParams();
  const [recipes, setRecipes] = useState([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const isKid = tier === "little" || tier === "junior";

  useEffect(() => {
    setLoading(true);
    api.get(`/recipes?tier=${tier}${q ? `&q=${q}` : ""}`)
      .then(r => { setRecipes(r.data); setErr(""); })
      .catch(e => setErr(e.response?.status === 402 ? "Active membership required" : "Failed to load"))
      .finally(() => setLoading(false));
  }, [tier, q]);

  return (
    <div className={`min-h-screen ${isKid ? "kid-theme" : ""}`}>
      <Nav/>
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="script text-3xl text-terracotta">The Book of</p>
        <h1 className="serif text-4xl sm:text-6xl font-black text-espresso">{TIERS[tier]}</h1>

        <div className="mt-6 relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted2"/>
          <input data-testid="book-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search recipes..."
            className="w-full pl-11 pr-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none bg-white"/>
        </div>

        {err && <p data-testid="book-error" className="mt-6 text-terracotta font-bold">{err} — <Link to="/#pricing" className="underline">Activate</Link></p>}
        {loading && <p className="mt-6 text-muted2">Loading…</p>}

        <div className="mt-8 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {recipes.map((r) => (
            <Link data-testid={`recipe-tile-${r.id}`} key={r.id} to={`/app/recipe/${r.id}`} className="card-warm overflow-hidden hover:-translate-y-1 transition-transform">
              {r.photo_url && <img src={r.photo_url} alt="" className="w-full h-48 object-cover"/>}
              <div className="p-5">
                <p className="text-xs uppercase tracking-widest text-terracotta font-bold">{r.homeschool_topic || r.tier}</p>
                <h3 className="mt-2 serif text-2xl font-bold text-espresso">{r.title}</h3>
                <p className="mt-2 text-sm text-muted2 line-clamp-2">{r.description}</p>
                <p className="mt-3 text-xs text-muted2">{r.prep_time + r.cook_time} min · Serves {r.servings}</p>
              </div>
            </Link>
          ))}
        </div>
        {!loading && !err && recipes.length === 0 && (
          <p className="mt-10 text-muted2">No recipes yet for this book. Jeana Marie is cooking!</p>
        )}
      </div>
    </div>
  );
}
