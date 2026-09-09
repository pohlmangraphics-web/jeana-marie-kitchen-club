import { useState } from "react";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export default function Redeem() {
  const { user, refresh } = useAuth();
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    if (!user) { nav("/auth?mode=register"); return; }
    setBusy(true);
    try {
      const { data } = await api.post("/redeem", { code });
      toast.success(`Membership active until ${new Date(data.membership_expires_at).toLocaleDateString()}`);
      await refresh();
      nav("/app");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Invalid code");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">Redeem a code</h1>
        <p className="mt-2 text-muted2">Enter the code from your Etsy purchase or gift. Extends your membership from today (or stacks onto an active one).</p>
        <form onSubmit={submit} className="mt-8 space-y-4">
          <input data-testid="redeem-code-input" required value={code} onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="JMK-XXXXXXXXXX" className="w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none uppercase tracking-widest text-center font-mono text-lg"/>
          <button data-testid="redeem-submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">
            {busy ? "…" : "Redeem"}
          </button>
        </form>
        {!user && <p className="mt-6 text-center text-sm text-muted2">You'll need to sign in first when you submit.</p>}
      </div>
    </div>
  );
}
