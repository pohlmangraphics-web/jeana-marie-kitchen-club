import { useEffect, useState } from "react";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { Plus, Trash2 } from "lucide-react";
import { toast } from "sonner";

export default function MealCosting() {
  const profile = JSON.parse(localStorage.getItem("jmk_profile") || "null");
  const [saved, setSaved] = useState([]);
  const [meal, setMeal] = useState("");
  const [servings, setServings] = useState(4);
  const [items, setItems] = useState([{ name: "", qty: 1, unit_price: 0 }]);

  const load = () => profile && api.get(`/meal-costs/${profile.id}`).then(r => setSaved(r.data));
  useEffect(() => { load(); /* eslint-disable-next-line */ }, []);

  if (!profile) return <div className="min-h-screen"><Nav/><p className="p-10">Pick a profile first.</p></div>;

  const total = items.reduce((s, i) => s + Number(i.qty || 0) * Number(i.unit_price || 0), 0);
  const perServing = total / Math.max(1, servings);

  const save = async () => {
    if (!meal) return toast.error("Add a meal name");
    await api.post("/meal-costs", { profile_id: profile.id, meal_name: meal, servings: Number(servings), items });
    toast.success("Costing saved!");
    setMeal(""); setItems([{ name: "", qty: 1, unit_price: 0 }]);
    load();
  };

  const upd = (idx, key, val) => setItems(items.map((it, i) => i === idx ? { ...it, [key]: val } : it));

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-4xl mx-auto px-6 py-10">
        <p className="script text-3xl text-terracotta">Interactive Worksheet</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Meal Costing Tool</h1>
        <p className="mt-2 text-muted2">Type the real prices your family paid at the store. The math happens automatically.</p>

        <div className="mt-8 card-warm p-6">
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-bold">Meal name</label>
              <input data-testid="mc-meal-name" value={meal} onChange={(e) => setMeal(e.target.value)} placeholder="Chicken Stir Fry"
                className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
            </div>
            <div>
              <label className="text-sm font-bold">Servings</label>
              <input data-testid="mc-servings" type="number" min="1" value={servings} onChange={(e) => setServings(e.target.value)}
                className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10"/>
            </div>
          </div>

          <table className="mt-6 w-full text-sm">
            <thead className="text-espresso">
              <tr className="border-b-2 border-espresso/10 text-left">
                <th className="py-2">Item</th><th>Qty</th><th>Unit price</th><th>Total</th><th></th>
              </tr>
            </thead>
            <tbody>
              {items.map((it, i) => (
                <tr key={i} className="border-b border-espresso/5">
                  <td className="py-2"><input data-testid={`mc-item-${i}-name`} value={it.name} onChange={(e) => upd(i, "name", e.target.value)} className="w-full px-2 py-1 rounded border border-espresso/10"/></td>
                  <td><input data-testid={`mc-item-${i}-qty`} type="number" step="0.1" value={it.qty} onChange={(e) => upd(i, "qty", e.target.value)} className="w-20 px-2 py-1 rounded border border-espresso/10"/></td>
                  <td><input data-testid={`mc-item-${i}-price`} type="number" step="0.01" value={it.unit_price} onChange={(e) => upd(i, "unit_price", e.target.value)} className="w-24 px-2 py-1 rounded border border-espresso/10"/></td>
                  <td>${(Number(it.qty || 0) * Number(it.unit_price || 0)).toFixed(2)}</td>
                  <td><button data-testid={`mc-remove-${i}`} onClick={() => setItems(items.filter((_, j) => j !== i))} className="text-terracotta"><Trash2 className="w-4 h-4"/></button></td>
                </tr>
              ))}
            </tbody>
          </table>
          <button data-testid="mc-add-item" onClick={() => setItems([...items, { name: "", qty: 1, unit_price: 0 }])} className="mt-3 btn-pill btn-outline !py-2 !px-4 text-sm"><Plus className="w-4 h-4"/> Add row</button>

          <div className="mt-6 rounded-xl bg-honey/30 p-5">
            <div className="flex justify-between text-espresso"><span className="font-bold">Total meal cost</span><span className="serif text-2xl font-black">${total.toFixed(2)}</span></div>
            <div className="flex justify-between mt-2 text-espresso"><span className="font-bold">Cost per serving</span><span className="serif text-2xl font-black">${perServing.toFixed(2)}</span></div>
          </div>

          <button data-testid="mc-save" onClick={save} className="mt-6 btn-pill btn-primary">Save Worksheet</button>
        </div>

        {saved.length > 0 && (
          <div className="mt-10">
            <h2 className="serif text-2xl font-black">Saved worksheets</h2>
            <div className="mt-4 space-y-3">
              {saved.map(m => (
                <div data-testid={`mc-saved-${m.id}`} key={m.id} className="card-warm p-4 flex justify-between items-center">
                  <div>
                    <p className="font-bold">{m.meal_name}</p>
                    <p className="text-sm text-muted2">${m.total_cost} total · ${m.per_serving_cost}/serving · {m.servings} servings</p>
                  </div>
                  <p className="text-xs text-muted2">{new Date(m.created_at).toLocaleDateString()}</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
