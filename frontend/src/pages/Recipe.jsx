import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { toast } from "sonner";
import { Heart, Check, Clock, Users, Zap, NotebookPen } from "lucide-react";

export default function Recipe() {
  const { id } = useParams();
  const [r, setR] = useState(null);
  const [kitchen, setKitchen] = useState(false);
  const [note, setNote] = useState("");
  const profile = JSON.parse(localStorage.getItem("jmk_profile") || "null");

  useEffect(() => {
    api.get(`/recipes/${id}`).then(res => setR(res.data)).catch(() => toast.error("Cannot load recipe"));
    if (kitchen) {
      // try to keep screen on
      if (navigator.wakeLock) navigator.wakeLock.request("screen").catch(() => {});
    }
  }, [id, kitchen]);

  const fav = async (made) => {
    if (!profile) return toast.error("Select a profile first");
    await api.post("/favorites", { profile_id: profile.id, recipe_id: id, made });
    toast.success(made ? "Marked as made! 🎉" : "Added to favorites");
  };

  const saveNote = async () => {
    if (!profile) return toast.error("Select a profile first");
    if (!note.trim()) return;
    await api.post("/journal", { profile_id: profile.id, recipe_id: id, title: `Note: ${r.title}`, notes: note });
    setNote("");
    toast.success("Saved to your journal");
  };

  if (!r) return <div className="min-h-screen"><Nav/><p className="p-10">Loading…</p></div>;

  return (
    <div className={`min-h-screen ${kitchen ? "kitchen-mode" : ""}`}>
      <Nav/>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <Link to={`/app/book/${r.tier}`} className="text-terracotta text-sm font-bold">← Back to book</Link>
          <button data-testid="kitchen-mode-toggle" onClick={() => setKitchen(!kitchen)}
            className={`btn-pill ${kitchen ? "btn-primary" : "btn-honey"} !py-2 !px-4 text-sm`}>
            <Zap className="w-4 h-4"/> {kitchen ? "Exit Kitchen Mode" : "Kitchen Mode"}
          </button>
        </div>

        {r.photo_url && <img src={r.photo_url} alt="" className="mt-6 w-full h-80 object-cover rounded-2xl"/>}

        <p className="mt-6 text-xs uppercase tracking-widest text-sage font-bold">{r.homeschool_topic}</p>
        <h1 className="serif text-4xl sm:text-6xl font-black text-espresso">{r.title}</h1>
        <p className="mt-4 text-lg text-muted2">{r.description}</p>

        <div className="mt-6 flex flex-wrap gap-6 text-sm text-muted2">
          <span className="flex items-center gap-2"><Clock className="w-4 h-4"/> {r.prep_time + r.cook_time} min</span>
          <span className="flex items-center gap-2"><Users className="w-4 h-4"/> Serves {r.servings}</span>
        </div>

        <div className="mt-4 flex gap-3">
          <button data-testid="fav-btn" onClick={() => fav(false)} className="btn-pill btn-outline !py-2"><Heart className="w-4 h-4"/> Favorite</button>
          <button data-testid="made-btn" onClick={() => fav(true)} className="btn-pill btn-primary !py-2"><Check className="w-4 h-4"/> We Made This</button>
        </div>

        <div className="mt-10 grid md:grid-cols-2 gap-10">
          <div>
            <h2 className="serif text-2xl font-black">Ingredients</h2>
            <ul className="mt-4 space-y-2">
              {r.ingredients.map((i, idx) => (
                <li key={idx} className="flex gap-3 items-start"><span className="w-5 h-5 rounded-full border-2 border-terracotta mt-1 shrink-0"/><span>{i}</span></li>
              ))}
            </ul>
          </div>
          <div>
            <h2 className="serif text-2xl font-black">Steps</h2>
            <ol className="mt-4 space-y-3">
              {r.steps.map((s, idx) => (
                <li key={idx} className="step flex gap-4 rounded-xl bg-ivory p-4">
                  <span className="serif text-terracotta font-black text-2xl leading-none">{idx+1}.</span>
                  <span>{s}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        {r.lesson_plan && (
          <div className="mt-10 rounded-2xl bg-sage/10 border-l-4 border-sage p-6">
            <p className="text-xs uppercase tracking-widest text-sage font-bold">Family Learning Guide</p>
            <h3 className="serif text-xl font-bold text-espresso mt-1">{r.homeschool_topic}</h3>
            <p className="mt-2 text-muted2">{r.lesson_plan}</p>
          </div>
        )}

        <div className="mt-10">
          <h2 className="serif text-2xl font-black flex items-center gap-2"><NotebookPen className="w-6 h-6"/> Journal note</h2>
          <p className="text-sm text-muted2 mt-1">{profile ? `Writing as ${profile.name}` : "Select a profile from your dashboard first."}</p>
          <textarea data-testid="journal-note-input" value={note} onChange={(e) => setNote(e.target.value)} placeholder="How did it go? What did the kids learn?"
            className="mt-3 w-full min-h-28 p-4 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none bg-white"/>
          <button data-testid="journal-note-save" onClick={saveNote} className="mt-3 btn-pill btn-primary">Save to journal</button>
        </div>
      </div>
    </div>
  );
}
