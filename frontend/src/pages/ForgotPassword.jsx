import { useState } from "react";
import { Link } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { toast } from "sonner";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/auth/forgot-password", { email });
      setSent(true);
      toast.success("Check your email for a reset link");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">Reset your password</h1>
        <p className="mt-2 text-muted2">Enter the email you signed up with. We'll send a secure reset link that expires in one hour.</p>
        {!sent ? (
          <form onSubmit={submit} className="mt-8 space-y-4">
            <input data-testid="forgot-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com" className="w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
            <button data-testid="forgot-submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">
              {busy ? "…" : "Send reset link"}
            </button>
          </form>
        ) : (
          <div data-testid="forgot-sent" className="mt-8 rounded-xl bg-sage/10 border-l-4 border-sage p-5">
            <p className="font-bold text-espresso">Check your inbox</p>
            <p className="mt-2 text-sm text-muted2">If an account exists for <span className="font-bold">{email}</span>, we've emailed a reset link. The link is good for one hour.</p>
          </div>
        )}
        <p className="mt-6 text-sm text-center"><Link to="/auth" className="text-terracotta font-bold">← Back to sign in</Link></p>
      </div>
    </div>
  );
}
