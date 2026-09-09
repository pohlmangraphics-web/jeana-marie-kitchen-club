import { useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      toast.success("Password updated. Sign in.");
      nav("/auth");
    } catch (err) { toast.error(err.response?.data?.detail || "Reset failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen"><Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">Choose a new password</h1>
        <form onSubmit={submit} className="mt-8 space-y-4">
          <input data-testid="reset-password" type="password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)}
            placeholder="At least 8 characters" className="w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
          <button data-testid="reset-submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">{busy ? "…" : "Update password"}</button>
        </form>
      </div>
    </div>
  );
}
