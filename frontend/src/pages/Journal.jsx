import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api, API } from "../lib/api";
import { Download, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useFlags } from "../lib/flags";

export default function Journal() {
  const profile = JSON.parse(localStorage.getItem("jmk_profile") || "null");
  const { flags } = useFlags();
  const [entries, setEntries] = useState([]);
  const [title, setTitle] = useState("");
  const [notes, setNotes] = useState("");

  const load = () => profile && api.get(`/journal/${profile.id}`).then(r => setEntries(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  if (!profile) return (
    <div className="min-h-screen"><Nav/>
      <div className="p-10">Pick a profile from <a className="text-terracotta underline" href="/app">your kitchen</a> first.</div>
    </div>
  );

  const add = async (e) => {
    e.preventDefault();
    await api.post("/journal", { profile_id: profile.id, title, notes });
    setTitle(""); setNotes("");
    load();
    toast.success("Saved");
  };
  const del = async (id) => { await api.delete(`/journal/${id}`); load(); };

  const exportPDF = async () => {
    const t = localStorage.getItem("jmk_token");
    const res = await fetch(`${API}/journal/${profile.id}/export`, { headers: { Authorization: `Bearer ${t}` } });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "cookbook.pdf"; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <p className="script text-3xl text-terracotta">{profile.name}'s</p>
            <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Journal</h1>
          </div>
          <button data-testid="journal-export" onClick={exportPDF} disabled={!flags.personalized_pdf_export}
            className={`btn-pill ${flags.personalized_pdf_export ? "btn-primary" : "btn-outline opacity-50 cursor-not-allowed"}`}>
            <Download className="w-4 h-4"/> {flags.personalized_pdf_export ? "Export Cookbook PDF" : "Cookbook Export (coming soon)"}
          </button>
        </div>

        <form onSubmit={add} className="mt-8 notebook p-8 rounded-2xl border-2 border-terracotta/10">
          <input data-testid="journal-title" required placeholder="Today's title..." value={title} onChange={(e) => setTitle(e.target.value)}
            className="w-full bg-transparent serif text-2xl font-bold text-espresso outline-none placeholder:text-espresso/30"/>
          <textarea data-testid="journal-notes" placeholder="What did you cook today? Draw a heart on the page..." value={notes} onChange={(e) => setNotes(e.target.value)}
            className="mt-4 w-full min-h-40 bg-transparent outline-none resize-none leading-8 text-espresso"/>
          <button data-testid="journal-add" className="btn-pill btn-primary mt-4">Add to Journal</button>
        </form>

        <div className="mt-10 space-y-4">
          {entries.map(e => (
            <div data-testid={`journal-entry-${e.id}`} key={e.id} className="card-warm p-6">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs text-muted2">{new Date(e.created_at).toLocaleDateString()}</p>
                  <h3 className="serif text-xl font-bold text-espresso">{e.title}</h3>
                </div>
                <button data-testid={`journal-delete-${e.id}`} onClick={() => del(e.id)} className="text-terracotta"><Trash2 className="w-4 h-4"/></button>
              </div>
              <p className="mt-2 whitespace-pre-wrap text-muted2">{e.notes}</p>
            </div>
          ))}
          {entries.length === 0 && <p className="text-muted2">Your journal is empty. Start writing!</p>}
        </div>
      </div>
    </div>
  );
}
