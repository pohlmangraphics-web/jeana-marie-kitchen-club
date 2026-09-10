import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api, API } from "../lib/api";
import { toast } from "sonner";
import { Trash2, Upload, Download, Copy, Pencil, FileText, X, Star } from "lucide-react";
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

async function uploadFile(file, purpose) {
  const fd = new FormData(); fd.append("file", file); fd.append("purpose", purpose);
  const t = localStorage.getItem("jmk_token");
  const res = await fetch(`${API}/files/upload`, { method: "POST", headers: { Authorization: `Bearer ${t}` }, body: fd });
  if (!res.ok) throw new Error("Upload failed");
  return res.json();
}

const BLANK_RECIPE = { title: "", tier: "adult", description: "", ingredients: "", steps: "", prep_time: 10, cook_time: 15, servings: 4, photo_url: "", photo_file_id: null, recipe_card_file_id: null, categories: [], homeschool_topic: "", lesson_plan: "", is_sample: false };
const CATEGORIES = ["Breakfast", "Lunch", "Dinner", "Snack", "Dessert", "Holiday"];

function RecipesAdmin() {
  const [list, setList] = useState([]);
  const [f, setF] = useState(BLANK_RECIPE);
  const [editingId, setEditingId] = useState(null);
  const [featuredId, setFeaturedId] = useState(null);
  const [featuredSchedule, setFeaturedSchedule] = useState({ starts_at: "", ends_at: "" });
  const [broadcastBusy, setBroadcastBusy] = useState(false);
  const [busy, setBusy] = useState(false);
  const load = () => {
    api.get("/recipes").then(r => setList(r.data)).catch(() => {});
    api.get("/admin/featured-recipe").then(r => {
      setFeaturedId(r.data.recipe_id || null);
      setFeaturedSchedule({ starts_at: r.data.starts_at || "", ends_at: r.data.ends_at || "" });
    }).catch(() => {});
  };
  useEffect(() => { load(); }, []);

  const startEdit = (r) => {
    setEditingId(r.id);
    setF({
      title: r.title || "", tier: r.tier || "adult", description: r.description || "",
      ingredients: (r.ingredients || []).join("\n"),
      steps: (r.steps || []).join("\n"),
      prep_time: r.prep_time ?? 10, cook_time: r.cook_time ?? 15, servings: r.servings ?? 4,
      photo_url: r.photo_url || "", photo_file_id: r.photo_file_id || null,
      recipe_card_file_id: r.recipe_card_file_id || null,
      categories: r.categories || [],
      homeschool_topic: r.homeschool_topic || "", lesson_plan: r.lesson_plan || "",
      is_sample: !!r.is_sample,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const cancelEdit = () => { setEditingId(null); setF(BLANK_RECIPE); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const payload = {
        ...f,
        ingredients: f.ingredients.split("\n").filter(Boolean),
        steps: f.steps.split("\n").filter(Boolean),
        prep_time: Number(f.prep_time), cook_time: Number(f.cook_time), servings: Number(f.servings),
      };
      if (editingId) {
        await api.patch(`/recipes/${editingId}`, payload);
        toast.success("Recipe updated");
      } else {
        await api.post("/recipes", payload);
        toast.success("Recipe published");
      }
      cancelEdit();
      load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };

  const del = async (id) => {
    if (!window.confirm("Delete this recipe? This cannot be undone.")) return;
    await api.delete(`/recipes/${id}`); load();
    if (editingId === id) cancelEdit();
  };
  const duplicate = async (id) => {
    await api.post(`/recipes/${id}/duplicate`);
    toast.success("Duplicated — edit the copy below");
    load();
  };
  const feature = async (id) => {
    const next = featuredId === id ? null : id;
    await api.put("/admin/featured-recipe", { recipe_id: next, starts_at: featuredSchedule.starts_at || null, ends_at: featuredSchedule.ends_at || null });
    setFeaturedId(next);
    toast.success(next ? "Set as Jeana's Pick of the Week" : "Cleared featured recipe");
  };
  const saveSchedule = async () => {
    await api.put("/admin/featured-recipe", { recipe_id: featuredId, starts_at: featuredSchedule.starts_at || null, ends_at: featuredSchedule.ends_at || null });
    toast.success("Schedule saved");
  };
  const broadcast = async () => {
    if (!window.confirm("Send this week's recipe email to all opted-in active families?")) return;
    setBroadcastBusy(true);
    try {
      const { data } = await api.post("/admin/email/weekly-drop");
      toast.success(`Sent ${data.sent} email(s) - "${data.recipe}"`);
    } catch (err) { toast.error(err.response?.data?.detail || "Broadcast failed"); }
    finally { setBroadcastBusy(false); }
  };
  const uploadPhoto = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true);
    try { const r = await uploadFile(file, "recipe_photo"); setF({...f, photo_file_id: r.file_id, photo_url: `${API}/files/${r.file_id}?auth=${localStorage.getItem("jmk_token")}`}); toast.success("Photo uploaded"); }
    catch { toast.error("Photo upload failed"); }
    finally { setBusy(false); }
  };
  const uploadCard = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true);
    try { const r = await uploadFile(file, "recipe_card"); setF({...f, recipe_card_file_id: r.file_id}); toast.success("Recipe card uploaded"); }
    catch { toast.error("Card upload failed"); }
    finally { setBusy(false); }
  };
  const removeCard = () => setF({...f, recipe_card_file_id: null});

  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <form onSubmit={submit} className="card-warm p-6 space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="serif text-xl font-bold">{editingId ? "Edit Recipe" : "New Recipe"}</h3>
          {editingId && <button type="button" onClick={cancelEdit} data-testid="admin-recipe-cancel" className="text-xs text-muted2 underline">Cancel</button>}
        </div>
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
        <div className="rounded-lg border-2 border-dashed border-espresso/10 p-3">
          <p className="text-xs font-bold text-espresso mb-2">Recipe photo</p>
          <input placeholder="Photo URL (or upload below)" value={f.photo_url} onChange={(e) => setF({...f, photo_url: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10 text-sm"/>
          <div className="mt-2 flex items-center gap-2">
            <input data-testid="admin-recipe-photo" type="file" accept="image/*" onChange={uploadPhoto}/>
            {f.photo_file_id && <span className="text-xs text-sage">✓ Uploaded</span>}
          </div>
        </div>
        <input placeholder="Homeschool topic" value={f.homeschool_topic} onChange={(e) => setF({...f, homeschool_topic: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <div>
          <p className="text-xs font-bold text-espresso mb-2">Categories</p>
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(c => (
              <button data-testid={`admin-recipe-cat-${c}`} type="button" key={c}
                onClick={() => setF({...f, categories: f.categories.includes(c) ? f.categories.filter(x => x !== c) : [...f.categories, c]})}
                className={`btn-pill !py-1 !px-3 text-xs ${f.categories.includes(c) ? "btn-primary" : "btn-outline"}`}>
                {c}
              </button>
            ))}
          </div>
        </div>
        <textarea placeholder="Family learning guide" value={f.lesson_plan} onChange={(e) => setF({...f, lesson_plan: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <div className="rounded-lg border-2 border-dashed border-espresso/10 p-3">
          <p className="text-xs font-bold text-espresso mb-2">Recipe card PDF (optional)</p>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="btn-pill btn-outline !py-1 !px-3 text-xs cursor-pointer">
              <Upload className="w-3 h-3"/> {f.recipe_card_file_id ? "Replace" : "Upload"} PDF
              <input data-testid="admin-recipe-card" type="file" accept="application/pdf" onChange={uploadCard} className="hidden"/>
            </label>
            {f.recipe_card_file_id && (
              <>
                <span className="text-xs text-sage flex items-center gap-1"><FileText className="w-3 h-3"/> Attached</span>
                <button data-testid="admin-recipe-card-remove" type="button" onClick={removeCard} className="btn-pill btn-outline !py-1 !px-3 text-xs"><X className="w-3 h-3"/> Remove</button>
              </>
            )}
          </div>
        </div>
        <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={f.is_sample} onChange={(e) => setF({...f, is_sample: e.target.checked})}/> Free sample</label>
        <button data-testid="admin-recipe-publish" disabled={busy} className="btn-pill btn-primary">{busy ? "…" : (editingId ? "Save Changes" : "Publish")}</button>
      </form>
      <div>
        <h3 className="serif text-xl font-bold mb-3">Published ({list.length})</h3>
        <div className="card-warm p-4 mb-4 bg-honey/20">
          <p className="text-xs uppercase tracking-widest text-espresso font-bold flex items-center gap-1"><Star className="w-3 h-3 fill-espresso"/> Jeana's Pick of the Week</p>
          <p className="text-xs text-muted2 mt-1">Optional schedule. If empty or outside the window, the newest published recipe shows automatically as the fallback.</p>
          <div className="mt-3 grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-bold">Starts</label>
              <input data-testid="featured-starts" type="datetime-local" value={featuredSchedule.starts_at ? featuredSchedule.starts_at.slice(0,16) : ""}
                onChange={(e) => setFeaturedSchedule({...featuredSchedule, starts_at: e.target.value ? new Date(e.target.value).toISOString() : ""})}
                className="mt-1 w-full px-2 py-1.5 text-sm rounded-lg border-2 border-espresso/10"/>
            </div>
            <div>
              <label className="text-xs font-bold">Ends</label>
              <input data-testid="featured-ends" type="datetime-local" value={featuredSchedule.ends_at ? featuredSchedule.ends_at.slice(0,16) : ""}
                onChange={(e) => setFeaturedSchedule({...featuredSchedule, ends_at: e.target.value ? new Date(e.target.value).toISOString() : ""})}
                className="mt-1 w-full px-2 py-1.5 text-sm rounded-lg border-2 border-espresso/10"/>
            </div>
          </div>
          <div className="mt-3 flex gap-2 flex-wrap">
            <button data-testid="featured-save-schedule" onClick={saveSchedule} className="btn-pill btn-outline !py-1 !px-3 text-xs">Save schedule</button>
            <button data-testid="weekly-drop-broadcast" onClick={broadcast} disabled={broadcastBusy}
              className="btn-pill btn-primary !py-1 !px-3 text-xs">
              {broadcastBusy ? "Sending…" : "Send weekly drop email"}
            </button>
          </div>
        </div>
        <div className="space-y-2 max-h-[720px] overflow-y-auto pr-2 recipes-list">
          {list.map(r => (
            <div key={r.id} data-testid={`admin-recipe-${r.id}`} className={`card-warm p-4 ${editingId === r.id ? "ring-2 ring-terracotta" : ""}`}>
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0">
                  <p className="font-bold text-espresso truncate">{r.title}</p>
                  <p className="text-xs text-muted2">{r.tier} · {new Date(r.published_at).toLocaleDateString()}{r.recipe_card_file_id ? " · 📄 Card" : ""}{r.is_sample ? " · Sample" : ""}</p>
                </div>
                <div className="flex gap-1 shrink-0">
                  <button data-testid={`admin-recipe-feature-${r.id}`} onClick={() => feature(r.id)} title={featuredId === r.id ? "Featured — click to unfeature" : "Feature as Jeana's Pick"}
                    className={`p-2 rounded-lg ${featuredId === r.id ? "bg-honey text-espresso" : "hover:bg-honey/30 text-espresso"}`}>
                    <Star className={`w-4 h-4 ${featuredId === r.id ? "fill-espresso" : ""}`}/>
                  </button>
                  <button data-testid={`admin-recipe-edit-${r.id}`} onClick={() => startEdit(r)} title="Edit" className="p-2 rounded-lg hover:bg-honey/30 text-espresso"><Pencil className="w-4 h-4"/></button>
                  <button data-testid={`admin-recipe-dup-${r.id}`} onClick={() => duplicate(r.id)} title="Duplicate" className="p-2 rounded-lg hover:bg-sage/20 text-sage"><Copy className="w-4 h-4"/></button>
                  <button data-testid={`admin-recipe-del-${r.id}`} onClick={() => del(r.id)} title="Delete" className="p-2 rounded-lg hover:bg-terracotta/10 text-terracotta"><Trash2 className="w-4 h-4"/></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

const BLANK_PRINTABLE = { title: "", tier: "little", kind: "coloring", description: "", content: "", pdf_file_id: null, thumbnail_file_id: null };

function PrintablesAdmin() {
  const [list, setList] = useState([]);
  const [f, setF] = useState(BLANK_PRINTABLE);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => api.get("/printables").then(r => setList(r.data));
  useEffect(() => { load(); }, []);

  const startEdit = (p) => {
    setEditingId(p.id);
    setF({
      title: p.title || "", tier: p.tier || "little", kind: p.kind || "coloring",
      description: p.description || "", content: p.content || "",
      pdf_file_id: p.pdf_file_id || null, thumbnail_file_id: p.thumbnail_file_id || null,
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  const cancelEdit = () => { setEditingId(null); setF(BLANK_PRINTABLE); };

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      if (editingId) { await api.patch(`/printables/${editingId}`, f); toast.success("Printable updated"); }
      else { await api.post("/printables", f); toast.success("Printable published"); }
      cancelEdit(); load();
    } catch (err) { toast.error(err.response?.data?.detail || "Failed"); }
    finally { setBusy(false); }
  };
  const del = async (id) => {
    if (!window.confirm("Delete this printable?")) return;
    await api.delete(`/printables/${id}`); load();
    if (editingId === id) cancelEdit();
  };
  const uploadPdf = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true);
    try { const r = await uploadFile(file, "printable_pdf"); setF({...f, pdf_file_id: r.file_id}); toast.success("PDF uploaded"); }
    catch { toast.error("PDF upload failed"); }
    finally { setBusy(false); }
  };
  const uploadThumb = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    setBusy(true);
    try { const r = await uploadFile(file, "printable_thumbnail"); setF({...f, thumbnail_file_id: r.file_id}); toast.success("Thumbnail uploaded"); }
    catch { toast.error("Thumbnail upload failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="grid lg:grid-cols-2 gap-8">
      <form onSubmit={submit} className="card-warm p-6 space-y-3">
        <div className="flex justify-between items-center">
          <h3 className="serif text-xl font-bold">{editingId ? "Edit Printable" : "New Printable"}</h3>
          {editingId && <button type="button" onClick={cancelEdit} data-testid="admin-printable-cancel" className="text-xs text-muted2 underline">Cancel</button>}
        </div>
        <input data-testid="admin-printable-title" required placeholder="Title" value={f.title} onChange={(e) => setF({...f, title: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <div className="grid grid-cols-2 gap-2">
          <select data-testid="admin-printable-tier" value={f.tier} onChange={(e) => setF({...f, tier: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["little","junior","teen","adult"].map(t => <option key={t} value={t}>{t}</option>)}</select>
          <select data-testid="admin-printable-kind" value={f.kind} onChange={(e) => setF({...f, kind: e.target.value})} className="px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["coloring","food_id","shopping_list","meal_costing","lesson_plan"].map(t => <option key={t} value={t}>{t}</option>)}</select>
        </div>
        <textarea data-testid="admin-printable-desc" placeholder="Description" value={f.description} onChange={(e) => setF({...f, description: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>

        <div className="rounded-lg border-2 border-dashed border-espresso/10 p-3">
          <p className="text-xs font-bold text-espresso mb-2">Upload finished PDF (optional — falls back to generated template)</p>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="btn-pill btn-outline !py-1 !px-3 text-xs cursor-pointer">
              <Upload className="w-3 h-3"/> {f.pdf_file_id ? "Replace" : "Upload"} PDF
              <input data-testid="admin-printable-pdf" type="file" accept="application/pdf" onChange={uploadPdf} className="hidden"/>
            </label>
            {f.pdf_file_id && (
              <>
                <span className="text-xs text-sage flex items-center gap-1"><FileText className="w-3 h-3"/> Uploaded</span>
                <button data-testid="admin-printable-pdf-remove" type="button" onClick={() => setF({...f, pdf_file_id: null})} className="btn-pill btn-outline !py-1 !px-3 text-xs"><X className="w-3 h-3"/> Remove</button>
              </>
            )}
          </div>
        </div>

        <div className="rounded-lg border-2 border-dashed border-espresso/10 p-3">
          <p className="text-xs font-bold text-espresso mb-2">Thumbnail image (optional)</p>
          <div className="flex items-center gap-2 flex-wrap">
            <label className="btn-pill btn-outline !py-1 !px-3 text-xs cursor-pointer">
              <Upload className="w-3 h-3"/> {f.thumbnail_file_id ? "Replace" : "Upload"} image
              <input data-testid="admin-printable-thumb" type="file" accept="image/*" onChange={uploadThumb} className="hidden"/>
            </label>
            {f.thumbnail_file_id && (
              <>
                <span className="text-xs text-sage">✓ Attached</span>
                <button data-testid="admin-printable-thumb-remove" type="button" onClick={() => setF({...f, thumbnail_file_id: null})} className="btn-pill btn-outline !py-1 !px-3 text-xs"><X className="w-3 h-3"/> Remove</button>
              </>
            )}
          </div>
        </div>

        <textarea placeholder="Content / instructions (used if no PDF uploaded)" rows={3} value={f.content} onChange={(e) => setF({...f, content: e.target.value})} className="w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
        <button data-testid="admin-printable-publish" disabled={busy} className="btn-pill btn-primary">{busy ? "…" : (editingId ? "Save Changes" : "Publish")}</button>
      </form>

      <div>
        <h3 className="serif text-xl font-bold mb-3">Published ({list.length})</h3>
        <div className="space-y-2 max-h-[720px] overflow-y-auto pr-2">
          {list.map(p => (
            <div key={p.id} data-testid={`admin-printable-${p.id}`} className={`card-warm p-4 flex items-center gap-3 ${editingId === p.id ? "ring-2 ring-terracotta" : ""}`}>
              <div className="w-16 h-16 rounded-lg bg-ivory overflow-hidden flex items-center justify-center shrink-0">
                {p.thumbnail_file_id
                  ? <img src={`${API}/printables/${p.id}/thumbnail`} alt="" className="w-full h-full object-cover"/>
                  : <FileText className="w-8 h-8 text-terracotta/40"/>}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-bold text-espresso truncate">{p.title}</p>
                <p className="text-xs text-muted2">
                  {p.tier} · {p.kind}
                  {p.pdf_file_id ? <span className="ml-1 text-sage">· 📎 Uploaded PDF</span> : <span className="ml-1 text-muted2">· Generated</span>}
                </p>
              </div>
              <div className="flex gap-1 shrink-0">
                <button data-testid={`admin-printable-edit-${p.id}`} onClick={() => startEdit(p)} title="Edit" className="p-2 rounded-lg hover:bg-honey/30 text-espresso"><Pencil className="w-4 h-4"/></button>
                <button data-testid={`admin-printable-del-${p.id}`} onClick={() => del(p.id)} title="Delete" className="p-2 rounded-lg hover:bg-terracotta/10 text-terracotta"><Trash2 className="w-4 h-4"/></button>
              </div>
            </div>
          ))}
        </div>
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
  const printSheet = async () => {
    const t = localStorage.getItem("jmk_token");
    const res = await fetch(`${API}/admin/codes/print-sheet.pdf`, { headers: { Authorization: `Bearer ${t}` } });
    if (!res.ok) return toast.error("Print sheet failed");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a"); a.href = url; a.download = "unredeemed_codes.pdf"; a.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div>
      <div className="card-warm p-6 flex flex-wrap gap-3 items-end">
        <div><label className="text-sm font-bold">Duration</label><select data-testid="admin-code-duration" value={duration} onChange={(e) => setDuration(e.target.value)} className="mt-1 block px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">{["monthly","3month","6month","annual"].map(d => <option key={d} value={d}>{d}</option>)}</select></div>
        <div><label className="text-sm font-bold">Count</label><input data-testid="admin-code-count" type="number" min="1" max="100" value={count} onChange={(e) => setCount(e.target.value)} className="mt-1 block w-32 px-3 py-2 rounded-lg border-2 border-espresso/10"/></div>
        <button data-testid="admin-code-generate" onClick={gen} className="btn-pill btn-primary">Generate</button>
        <button data-testid="admin-code-print-sheet" onClick={printSheet} className="btn-pill btn-outline"><Download className="w-4 h-4"/> Print unredeemed sheet</button>
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
      <div className="md:col-span-2 card-warm p-6">
        <p className="text-xs uppercase tracking-widest text-sage font-bold">Top Recipes (favorites)</p>
        <ul className="mt-3 space-y-2">
          {d.top_recipes.map((r, i) => <li key={i} className="flex justify-between"><span className="truncate pr-2">{r.title}</span><span className="font-bold shrink-0">{r.count}</span></li>)}
          {d.top_recipes.length === 0 && <li className="text-muted2">No favorites yet.</li>}
        </ul>
      </div>
      <div className="md:col-span-2 card-warm p-6">
        <p className="text-xs uppercase tracking-widest text-sage font-bold">Printable Downloads</p>
        <div data-testid="admin-printable-downloads">
          <ul className="mt-3 space-y-2">
            {(d.top_printables || []).map((p, i) => (
              <li key={i} className="flex justify-between">
                <span className="truncate pr-2">{p.title}</span>
                <span className="font-bold shrink-0">{p.download_count}</span>
              </li>
            ))}
            {(!d.top_printables || d.top_printables.length === 0) && <li className="text-muted2">No downloads tracked yet.</li>}
          </ul>
          <p data-testid="admin-privacy-note" className="mt-3 text-xs text-muted2 italic">Aggregate download counts. No child-level data collected.</p>
        </div>
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
  const [etsyUrl, setEtsyUrl] = useState("");
  const [etsyBusy, setEtsyBusy] = useState(false);
  useEffect(() => {
    api.get("/branding/logo").then(r => setSaved(r.data.file_id));
    api.get("/branding/etsy-url").then(r => setEtsyUrl(r.data.url || ""));
  }, []);
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
  const saveEtsy = async () => {
    setEtsyBusy(true);
    try {
      await api.put("/admin/branding/etsy-url", { url: etsyUrl });
      toast.success("Etsy shop URL saved");
    } catch { toast.error("Failed to save"); }
    finally { setEtsyBusy(false); }
  };
  return (
    <div className="max-w-xl space-y-10">
      <div>
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

      <div>
        <h3 className="serif text-xl font-bold">Etsy Shop URL</h3>
        <p className="text-sm text-muted2 mt-1">Used on the public Gift page's "Buy on Etsy" button. Leave blank to show a generic link.</p>
        <div className="mt-3 flex gap-2 flex-wrap">
          <input data-testid="etsy-url-input" type="url" value={etsyUrl} onChange={(e) => setEtsyUrl(e.target.value)}
            placeholder="https://www.etsy.com/shop/JeanaMariesKitchenClub"
            className="flex-1 min-w-[260px] px-3 py-2 rounded-lg border-2 border-espresso/10 outline-none focus:border-terracotta"/>
          <button data-testid="etsy-url-save" onClick={saveEtsy} disabled={etsyBusy} className="btn-pill btn-primary">
            {etsyBusy ? "…" : "Save"}
          </button>
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
