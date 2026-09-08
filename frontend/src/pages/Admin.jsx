import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api, API } from "../lib/api";
import { toast } from "sonner";
import { Trash2, Upload, Download } from "lucide-react";
import { useFlags } from "../lib/flags";

export default function Admin() {
  const [tab, setTab] = useState("recipes");
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="script text-3xl text-terracotta">Admin</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Kitchen Club HQ</h1>

        <div className="mt-6 flex gap-2 flex-wrap">
          {["recipes", "printables", "codes", "families", "analytics", "flags", "branding", "export"].map(t => (
            <button data-testid={`admin-tab-${t}`} key={t} onClick={() => setTab(t)}
              className={`btn-pill !py-2 !px-4 text-sm ${tab === t ? "btn-primary" : "btn-outline"}`}>{t.charAt(0).toUpperCase() + t.slice(1)}</button>
          ))}
        </div>

        <div className="mt-8">
          {tab === "recipes" && <RecipesAdmin/>}
          {tab === "printables" && <PrintablesAdmin/>}
          {tab === "codes" && <CodesAdmin/>}
          {tab === "families" && <FamiliesAdmin/>}
          {tab === "analytics" && <AnalyticsAdmin/>}
          {tab === "flags" && <FlagsAdmin/>}
          {tab === "branding" && <BrandingAdmin/>}
          {tab === "export" && <ExportAdmin/>}
        </div>
      </div>
    </div>
  );
}

function RecipesAdmin() {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ title: "", tier: "adult", description: "", ingredients: "", steps: "", prep_time: 10, cook_time: 15, servings: 4, photo_url: "", homeschool_topic: "", lesson_plan: "", is_sample: false });
  const load = () => api.get("/recipes").then(r => setList(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    await api.post("/recipes", {
      ...f,
      ingredients: f.ingredients.split("\n").filter(Boolean),
      steps: f.steps.split("\n").filter(Boolean),
      prep_time: Number(f.prep_time), cook_time: Number(f.cook_time), servings: Number(f.servings),
    });
    toast.success("Recipe published");
    setF({ ...f, title: "", description: "", ingredients: "", steps: "" });
    load();
  };
  const del = async (id) => { await api.delete(`/recipes/${id}`); load(); };

  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <form onSubmit={create} className="card-warm p-6 space-y-3">
        <h3 className="serif text-xl font-bold">New Recipe</h3>
        <input data-testid="admin-recipe-title" required placeholder="Title" value={f.title} onChange={(e) => setF({...f, title: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <select data-testid="admin-recipe-tier" value={f.tier} onChange={(e) => setF({...f, tier: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">
          {["little","junior","teen","adult"].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <textarea data-testid="admin-recipe-desc" placeholder="Description" value={f.description} onChange={(e) => setF({...f, description: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <textarea data-testid="admin-recipe-ingredients" placeholder="Ingredients (one per line)" rows={4} value={f.ingredients} onChange={(e) => setF({...f, ingredients: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <textarea data-testid="admin-recipe-steps" placeholder="Steps (one per line)" rows={4} value={f.steps} onChange={(e) => setF({...f, steps: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <div className="grid grid-cols-3 gap-2">
          <input placeholder="Prep" type="number" value={f.prep_time} onChange={(e) => setF({...f, prep_time: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10"/>
          <input placeholder="Cook" type="number" value={f.cook_time} onChange={(e) => setF({...f, cook_time: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10"/>
          <input placeholder="Servings" type="number" value={f.servings} onChange={(e) => setF({...f, servings: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        </div>
        <input placeholder="Photo URL" value={f.photo_url} onChange={(e) => setF({...f, photo_url: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <input placeholder="Homeschool topic" value={f.homeschool_topic} onChange={(e) => setF({...f, homeschool_topic: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <textarea placeholder="Family learning guide" value={f.lesson_plan} onChange={(e) => setF({...f, lesson_plan: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={f.is_sample} onChange={(e) => setF({...f, is_sample: e.target.checked})}/> Free sample</label>
        <button data-testid="admin-recipe-publish" className="btn-pill btn-primary">Publish</button>
      </form>
      <div>
        <h3 className="serif text-xl font-bold mb-3">Published ({list.length})</h3>
        <div className="space-y-2 max-h-[600px] overflow-y-auto">
          {list.map(r => (
            <div key={r.id} className="card-warm p-4 flex justify-between items-center">
              <div>
                <p className="font-bold text-espresso">{r.title}</p>
                <p className="text-xs text-muted2">{r.tier} · {new Date(r.published_at).toLocaleDateString()}</p>
              </div>
              <button data-testid={`admin-recipe-del-${r.id}`} onClick={() => del(r.id)} className="text-terracotta"><Trash2 className="w-4 h-4"/></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function PrintablesAdmin() {
  const [list, setList] = useState([]);
  const [f, setF] = useState({ title: "", tier: "little", kind: "coloring", description: "", content: "" });
  const load = () => api.get("/printables").then(r => setList(r.data));
  useEffect(() => { load(); }, []);
  const create = async (e) => {
    e.preventDefault();
    await api.post("/printables", f);
    toast.success("Published");
    setF({ ...f, title: "", description: "", content: "" });
    load();
  };
  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <form onSubmit={create} className="card-warm p-6 space-y-3">
        <h3 className="serif text-xl font-bold">New Printable</h3>
        <input data-testid="admin-printable-title" required placeholder="Title" value={f.title} onChange={(e) => setF({...f, title: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <div className="grid grid-cols-2 gap-2">
          <select value={f.tier} onChange={(e) => setF({...f, tier: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["little","junior","teen","adult"].map(t => <option key={t} value={t}>{t}</option>)}</select>
          <select value={f.kind} onChange={(e) => setF({...f, kind: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["coloring","food_id","shopping_list","meal_costing","lesson_plan"].map(t => <option key={t} value={t}>{t}</option>)}</select>
        </div>
        <textarea placeholder="Description" value={f.description} onChange={(e) => setF({...f, description: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <textarea placeholder="Content / instructions" rows={4} value={f.content} onChange={(e) => setF({...f, content: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <button data-testid="admin-printable-publish" className="btn-pill btn-primary">Publish</button>
      </form>
      <div className="space-y-2 max-h-[600px] overflow-y-auto">
        {list.map(p => (
          <div key={p.id} className="card-warm p-4 flex justify-between items-center">
            <div><p className="font-bold text-espresso">{p.title}</p><p className="text-xs text-muted2">{p.tier} · {p.kind}</p></div>
            <button data-testid={`admin-printable-del-${p.id}`} onClick={async () => { await api.delete(`/printables/${p.id}`); load(); }} className="text-terracotta"><Trash2 className="w-4 h-4"/></button>
          </div>
        ))}
      </div>
    </div>
  );
}

function CodesAdmin() {
  const [list, setList] = useState([]);
  const [duration, setDuration] = useState("monthly");
  const [count, setCount] = useState(1);
  const load = () => api.get("/admin/codes").then(r => setList(r.data));
  useEffect(() => { load(); }, []);
  const gen = async () => {
    await api.post("/admin/codes", { duration, count: Number(count) });
    toast.success(`Generated ${count} codes`);
    load();
  };
  return (
    <div>
      <div className="card-warm p-6 flex flex-wrap gap-3 items-end">
        <div><label className="text-sm font-bold">Duration</label><select data-testid="admin-code-duration" value={duration} onChange={(e) => setDuration(e.target.value)} className="mt-1 block px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["monthly","3month","6month","annual"].map(d => <option key={d} value={d}>{d}</option>)}</select></div>
        <div><label className="text-sm font-bold">Count</label><input data-testid="admin-code-count" type="number" min="1" max="100" value={count} onChange={(e) => setCount(e.target.value)} className="mt-1 block w-32 px-3 py-2 rounded-lg border-2 border-espresso/10"/></div>
        <button data-testid="admin-code-generate" onClick={gen} className="btn-pill btn-primary">Generate</button>
      </div>
      <div className="mt-6 grid md:grid-cols-2 gap-3 max-h-[600px] overflow-y-auto">
        {list.map(c => (
          <div key={c.id} className="card-warm p-4 font-mono text-sm">
            <p className="font-bold text-lg">{c.code}</p>
            <p className="text-xs text-muted2 font-sans">{c.duration} · {c.redeemed_by ? `Used ${new Date(c.redeemed_at).toLocaleDateString()}` : "Unused"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function FamiliesAdmin() {
  const [list, setList] = useState([]);
  const load = () => api.get("/admin/families").then(r => setList(r.data));
  useEffect(() => { load(); }, []);
  return (
    <div className="space-y-3">
      {list.map(u => (
        <div key={u.id} data-testid={`admin-family-${u.id}`} className="card-warm p-4 flex justify-between items-center">
          <div>
            <p className="font-bold text-espresso">{u.family_name}</p>
            <p className="text-xs text-muted2">{u.email} · {u.profile_count} profiles · {u.has_active_membership ? "Active" : "Inactive"}</p>
          </div>
          <button data-testid={`admin-family-revoke-${u.id}`} onClick={async () => { await api.post(`/admin/families/${u.id}/revoke`); load(); toast.success("Revoked"); }} className="btn-pill btn-outline !py-2 !px-4 text-sm">Revoke</button>
        </div>
      ))}
    </div>
  );
}

function AnalyticsAdmin() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get("/admin/analytics").then(r => setD(r.data)); }, []);
  if (!d) return <p>Loading…</p>;
  return (
    <div className="grid md:grid-cols-4 gap-4">
      {[["Total families", d.total_families], ["Active members", d.active_families], ["Recipes", d.total_recipes], ["Printables", d.total_printables]].map(([k, v]) => (
        <div key={k} className="card-warm p-6">
          <p className="text-xs uppercase tracking-widest text-sage font-bold">{k}</p>
          <p className="serif text-4xl font-black text-espresso mt-2">{v}</p>
        </div>
      ))}
      <div className="md:col-span-4 card-warm p-6">
        <p className="text-xs uppercase tracking-widest text-sage font-bold">Top Recipes</p>
        <ul className="mt-3 space-y-2">
          {d.top_recipes.map((r, i) => <li key={i} className="flex justify-between"><span>{r.title}</span><span className="font-bold">{r.count}</span></li>)}
          {d.top_recipes.length === 0 && <li className="text-muted2">No favorites yet.</li>}
        </ul>
      </div>
    </div>
  );
}

function FlagsAdmin() {
  const { flags, refresh } = useFlags();
  const [local, setLocal] = useState({});
  useEffect(() => { setLocal(flags); }, [flags]);
  const toggle = (k) => setLocal({ ...local, [k]: !local[k] });
  const save = async () => {
    await api.put("/admin/flags", { flags: local });
    toast.success("Feature flags updated");
    refresh();
  };
  const groups = {
    "Public MVP (always on)": ["free_samples", "recipes_by_tier", "printables", "meal_costing", "notes_and_favorites", "admin_publishing", "stripe_checkout", "redeem_codes"],
    "Hidden until ready": ["kid_photo_upload", "adult_photo_upload", "profile_pins", "personalized_pdf_export", "advanced_analytics", "pwa_install", "weekly_challenges"],
  };
  return (
    <div className="space-y-8">
      {Object.entries(groups).map(([title, keys]) => (
        <div key={title}>
          <h3 className="serif text-xl font-bold text-espresso">{title}</h3>
          <div className="mt-3 grid md:grid-cols-2 gap-2">
            {keys.map(k => (
              <label key={k} data-testid={`flag-${k}`} className="card-warm p-3 flex justify-between items-center cursor-pointer">
                <span className="text-sm font-mono">{k}</span>
                <input type="checkbox" checked={!!local[k]} onChange={() => toggle(k)} className="w-5 h-5 accent-terracotta"/>
              </label>
            ))}
          </div>
        </div>
      ))}
      <button data-testid="flags-save" onClick={save} className="btn-pill btn-primary">Save Flags</button>
    </div>
  );
}

function BrandingAdmin() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [saved, setSaved] = useState(null);
  useEffect(() => { api.get("/branding/logo").then(r => setSaved(r.data.file_id)); }, []);
  const upload = async () => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file);
    const t = localStorage.getItem("jmk_token");
    const res = await fetch(`${API}/admin/branding/logo`, { method: "POST", headers: { Authorization: `Bearer ${t}` }, body: fd });
    if (!res.ok) return toast.error("Upload failed");
    const data = await res.json();
    setSaved(data.file_id);
    toast.success("Logo updated");
  };
  return (
    <div className="max-w-xl">
      <h3 className="serif text-xl font-bold">Brand Logo</h3>
      <p className="text-sm text-muted2 mt-1">Recommended: transparent PNG or SVG, square, 512×512 minimum. Max 4MB. Palette locked to terracotta, honey, sage, buttercream, espresso.</p>
      <div className="mt-4 flex items-center gap-6">
        <div className="w-32 h-32 rounded-2xl border-2 border-espresso/10 bg-cream flex items-center justify-center overflow-hidden">
          {preview ? <img src={preview} alt="preview" className="max-w-full max-h-full"/> :
           saved ? <img src={`${API}/branding/logo/raw`} alt="current" className="max-w-full max-h-full"/> :
           <span className="text-xs text-muted2">Default</span>}
        </div>
        <div>
          <input data-testid="logo-file" type="file" accept="image/png,image/svg+xml,image/jpeg,image/webp"
            onChange={(e) => { const f = e.target.files?.[0]; setFile(f || null); if (f) setPreview(URL.createObjectURL(f)); }}/>
          <button data-testid="logo-upload" onClick={upload} disabled={!file} className="mt-3 btn-pill btn-primary"><Upload className="w-4 h-4"/> Upload logo</button>
        </div>
      </div>
    </div>
  );
}

function ExportAdmin() {
  const entities = ["families", "parents", "profiles", "recipes", "entitlements", "codes", "subscriptions"];
  const download = async (e, format) => {
    const t = localStorage.getItem("jmk_token");
    const res = await fetch(`${API}/admin/export/${e}?format=${format}`, { headers: { Authorization: `Bearer ${t}` } });
    if (!res.ok) return toast.error("Export failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = `${e}.${format}`; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div>
      <h3 className="serif text-xl font-bold text-espresso">Data Export</h3>
      <p className="text-sm text-muted2 mt-1">Download all admin data as CSV or JSON. Great for backups & reporting.</p>
      <div className="mt-4 grid sm:grid-cols-2 gap-3">
        {entities.map(e => (
          <div key={e} data-testid={`export-${e}`} className="card-warm p-4 flex justify-between items-center">
            <span className="font-mono text-sm">{e}</span>
            <div className="flex gap-2">
              <button data-testid={`export-${e}-csv`} onClick={() => download(e, "csv")} className="btn-pill btn-outline !py-1 !px-3 text-xs"><Download className="w-3 h-3"/> CSV</button>
              <button data-testid={`export-${e}-json`} onClick={() => download(e, "json")} className="btn-pill btn-outline !py-1 !px-3 text-xs"><Download className="w-3 h-3"/> JSON</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
