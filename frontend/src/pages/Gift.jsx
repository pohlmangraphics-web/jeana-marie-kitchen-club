import { useState } from "react";
import Nav from "../components/Nav";
import Footer from "../components/Footer";
import { API } from "../lib/api";
import { toast } from "sonner";
import { Gift, Download, Printer } from "lucide-react";

const DURATIONS = [
  { key: "monthly", label: "1 Month", price: "$9.99" },
  { key: "3month", label: "3 Months", price: "$26.99" },
  { key: "6month", label: "6 Months", price: "$49.99" },
  { key: "annual", label: "1 Year", price: "$89.99" },
];

export default function GiftPage() {
  const [form, setForm] = useState({ to: "", from: "", code: "", duration: "annual", message: "" });
  const [busy, setBusy] = useState(false);

  const download = async () => {
    if (!form.to.trim() || !form.from.trim() || !form.code.trim()) {
      return toast.error("Please fill in Recipient, From, and Code");
    }
    setBusy(true);
    try {
      const res = await fetch(`${API}/gift-certificate/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error("Failed");
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = `KitchenClub_Gift_${form.to.replace(/\s+/g, "_")}.pdf`; a.click();
      URL.revokeObjectURL(url);
      toast.success("Certificate downloaded!");
    } catch { toast.error("Could not generate certificate"); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav/>

      <section className="paper-tex">
        <div className="max-w-7xl mx-auto px-6 pt-14 pb-16 grid lg:grid-cols-12 gap-12 items-center">
          <div className="lg:col-span-7">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-honey text-espresso text-xs uppercase tracking-[0.2em] font-bold">
              <Gift className="w-3 h-3"/> Give the Kitchen Club
            </div>
            <h1 className="mt-6 serif text-5xl sm:text-6xl font-black leading-[1.05] text-espresso">
              A gift that <span className="script text-terracotta font-normal text-6xl sm:text-7xl">nourishes</span>.
            </h1>
            <p className="mt-6 text-lg text-muted2 max-w-xl leading-relaxed">
              Grandparents, aunts and uncles, family friends — give a whole year of weekly recipes and printable family learning guides. Perfect for birthdays, holidays and Just Because.
            </p>
            <div className="mt-8 grid sm:grid-cols-2 gap-4 max-w-lg">
              {DURATIONS.map(d => (
                <div key={d.key} data-testid={`gift-tier-${d.key}`} className="card-warm p-4">
                  <p className="font-bold text-espresso">{d.label}</p>
                  <p className="serif text-2xl font-black text-terracotta mt-1">{d.price}</p>
                </div>
              ))}
            </div>
            <a data-testid="gift-etsy-link" href="https://www.etsy.com/" target="_blank" rel="noreferrer"
               className="btn-pill btn-primary mt-8 inline-flex">Buy on Etsy →</a>
          </div>

          <div className="lg:col-span-5">
            <div className="rounded-3xl overflow-hidden shadow-2xl rotate-1 bg-cream">
              <div className="p-8 border-4 border-double border-terracotta">
                <p className="text-center script text-3xl text-terracotta">Jeana Marie's</p>
                <p className="text-center serif text-lg text-espresso font-bold -mt-1">Kitchen Club</p>
                <p className="mt-8 text-center text-xs uppercase tracking-widest text-muted2">This certificate entitles</p>
                <p className="mt-1 text-center serif text-2xl font-black text-espresso">Your Recipient</p>
                <p className="mt-4 text-center text-xs uppercase tracking-widest text-muted2">To a membership of</p>
                <p className="mt-1 text-center serif text-3xl font-black text-terracotta">1 Full Year</p>
                <div className="mt-6 border-t-2 border-dashed border-terracotta/30 pt-4 text-center">
                  <p className="text-xs uppercase tracking-widest text-muted2">Redeem code</p>
                  <p className="mt-1 font-mono font-bold text-espresso tracking-widest">JMK-XXXXXXXXXX</p>
                </div>
              </div>
            </div>
            <p className="mt-3 text-center text-sm text-muted2 italic">Print, fold, hand-deliver.</p>
          </div>
        </div>
      </section>

      <section className="bg-ivory py-16">
        <div className="max-w-3xl mx-auto px-6">
          <p className="text-xs uppercase tracking-[0.2em] text-sage font-bold">Print Your Own Certificate</p>
          <h2 className="mt-3 serif text-3xl sm:text-4xl font-black text-espresso">Already have a code?</h2>
          <p className="mt-2 text-muted2">Fill in the details below and download a beautiful printable certificate to hand to your recipient.</p>

          <div className="mt-8 card-warm p-6 space-y-4">
            <div className="grid sm:grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-bold text-espresso">To (recipient)</label>
                <input data-testid="gift-to" value={form.to} onChange={(e) => setForm({...form, to: e.target.value})} placeholder="The Baker Family"
                  className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10 focus:border-terracotta outline-none"/>
              </div>
              <div>
                <label className="text-sm font-bold text-espresso">From</label>
                <input data-testid="gift-from" value={form.from} onChange={(e) => setForm({...form, from: e.target.value})} placeholder="Grandma & Grandpa"
                  className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10 focus:border-terracotta outline-none"/>
              </div>
              <div>
                <label className="text-sm font-bold text-espresso">Redeem code</label>
                <input data-testid="gift-code" value={form.code} onChange={(e) => setForm({...form, code: e.target.value.toUpperCase()})}
                  placeholder="JMK-XXXXXXXXXX"
                  className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10 focus:border-terracotta outline-none font-mono uppercase tracking-widest"/>
              </div>
              <div>
                <label className="text-sm font-bold text-espresso">Duration</label>
                <select data-testid="gift-duration" value={form.duration} onChange={(e) => setForm({...form, duration: e.target.value})}
                  className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10 bg-white">
                  {DURATIONS.map(d => <option key={d.key} value={d.key}>{d.label}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm font-bold text-espresso">Personal message (optional)</label>
              <textarea data-testid="gift-message" value={form.message} onChange={(e) => setForm({...form, message: e.target.value})} rows={3}
                placeholder="Because family time is the best kind of time..."
                className="mt-1 w-full px-3 py-2 rounded-lg border-2 border-espresso/10 focus:border-terracotta outline-none"/>
            </div>
            <button data-testid="gift-download" onClick={download} disabled={busy}
              className="btn-pill btn-primary"><Download className="w-4 h-4"/> {busy ? "…" : "Download printable PDF"}</button>
          </div>

          <div className="mt-10 flex items-start gap-4 rounded-2xl bg-sage/10 border-l-4 border-sage p-5">
            <Printer className="w-6 h-6 text-sage shrink-0 mt-1"/>
            <p className="text-sm text-muted2 leading-relaxed">
              <span className="font-bold text-espresso">Best results:</span> print on 8.5×11 paper, ideally card stock. Fold in half for a card, or leave flat inside a birthday envelope. Includes the redeem code the recipient will enter at
              <span className="font-mono text-terracotta"> /redeem</span>.
            </p>
          </div>
        </div>
      </section>

      <Footer/>
    </div>
  );
}
