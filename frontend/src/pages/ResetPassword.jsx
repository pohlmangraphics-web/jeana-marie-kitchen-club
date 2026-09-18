import { useState } from "react";
import { useSearchParams, useNavigate, Link } from "react-router-dom";
import Nav from "../components/Nav";
import { api, errorMessage } from "../lib/api";
import { toast } from "sonner";

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [pw, setPw] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (pw.length < 8) { setError("Password must have at least 8 characters."); return; }
    setBusy(true);
    try {
      await api.post("/auth/reset-password", { token, new_password: pw });
      toast.success("Password updated. Sign in.");
      nav("/auth");
    } catch (err) {
      const msg = errorMessage(err, "Reset failed. Please request a new link.");
      setError(msg);
      toast.error(msg);
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen"><Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">Choose a new password</h1>
        {!token ? (
          <div data-testid="reset-missing-token" className="mt-8 rounded-xl bg-terracotta/10 border-l-4 border-terracotta p-5">
            <p className="font-bold text-espresso">This reset link is incomplete</p>
            <p className="mt-2 text-sm text-muted2">Please open the link from your email again, or request a new one.</p>
            <Link to="/forgot" data-testid="reset-request-new" className="inline-block mt-4 text-terracotta font-bold">Request a new link →</Link>
          </div>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-4">
            <input data-testid="reset-password" type="password" minLength={8} required value={pw} onChange={(e) => setPw(e.target.value)}
              placeholder="At least 8 characters" className="w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
            {error && (
              <div data-testid="reset-error" role="alert" className="rounded-xl bg-terracotta/10 border-l-4 border-terracotta p-4 text-sm text-espresso">
                {error} {/invalid|expired/i.test(error) && <Link to="/forgot" data-testid="reset-error-request-new" className="text-terracotta font-bold">Request a new link →</Link>}
              </div>
            )}
            <button data-testid="reset-submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">{busy ? "…" : "Update password"}</button>
          </form>
        )}
      </div>
    </div>
  );
}
