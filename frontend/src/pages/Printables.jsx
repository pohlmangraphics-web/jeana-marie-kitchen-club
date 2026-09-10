import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api, API } from "../lib/api";
import { Download, Printer } from "lucide-react";

const KIND_LABEL = { coloring: "Coloring Page", food_id: "Food ID", shopping_list: "Shopping List", meal_costing: "Meal Costing", lesson_plan: "Family Learning Guide" };

export default function Printables() {
  const [items, setItems] = useState([]);
  const [tier, setTier] = useState("");

  useEffect(() => {
    api.get(`/printables${tier ? `?tier=${tier}` : ""}`).then(r => setItems(r.data));
  }, [tier]);

  const download = async (p) => {
    const t = localStorage.getItem("jmk_token");
    const res = await fetch(`${API}/printables/${p.id}/pdf`, { headers: { Authorization: `Bearer ${t}` } });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `${p.title}.pdf`; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-7xl mx-auto px-6 py-10">
        <p className="script text-3xl text-terracotta">Printables</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Family Learning Library</h1>
        <p className="mt-2 text-muted2">Print-ready 8.5×11 PDFs. Coloring pages, worksheets, shopping lists, meal costing sheets, and weekly family learning guides.</p>

        <div className="mt-6 flex gap-2 flex-wrap">
          {["", "little", "junior", "teen", "adult"].map(t => (
            <button data-testid={`printable-tier-${t || "all"}`} key={t} onClick={() => setTier(t)}
              className={`btn-pill !py-2 !px-4 text-sm ${tier === t ? "btn-primary" : "btn-outline"}`}>
              {t ? t.charAt(0).toUpperCase() + t.slice(1) : "All"}
            </button>
          ))}
        </div>

        <div className="mt-8 grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map(p => (
            <div key={p.id} data-testid={`printable-${p.id}`} className="card-warm overflow-hidden">
              {p.thumbnail_file_id && (
                <img src={`${API}/printables/${p.id}/thumbnail`} alt="" className="w-full h-40 object-cover"/>
              )}
              <div className="p-6">
                <div className="flex items-center gap-2 text-xs uppercase tracking-widest font-bold text-sage">
                  <Printer className="w-3 h-3"/> {KIND_LABEL[p.kind]} · {p.tier}
                </div>
                <h3 className="mt-2 serif text-xl font-bold text-espresso">{p.title}</h3>
                <p className="mt-2 text-sm text-muted2">{p.description}</p>
                <button data-testid={`printable-download-${p.id}`} onClick={() => download(p)} className="mt-4 btn-pill btn-primary !py-2 !px-4 text-sm">
                  <Download className="w-4 h-4"/> Download PDF
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
