import { useState } from "react";
import { Link } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.post("/auth/forgot-password", { email });
      // In Phase 4 an email will carry the token; for now we surface it if available.
      if (data.reset_token) setToken(data.reset_token);
      toast.success("If the email exists, a reset link has been generated.");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">Reset your password</h1>
        <p className="mt-2 text-muted2">Enter the email you signed up with.</p>
        <form onSubmit={submit} className="mt-8 space-y-4">
          <input data-testid="forgot-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com" className="w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
          <button data-testid="forgot-submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">
            {busy ? "…" : "Send reset link"}
          </button>
        </form>
        {token && (
          <div className="mt-6 p-4 rounded-xl bg-honey/40 border-2 border-honey">
            <p className="text-sm font-bold text-espresso">Email delivery is not enabled yet.</p>
            <p className="text-xs mt-1 text-muted2">Use this one-time link (share via a secure channel):</p>
            <Link data-testid="forgot-link" to={`/reset?token=${token}`} className="mt-2 block break-all font-mono text-xs text-terracotta underline">
              /reset?token={token}
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
