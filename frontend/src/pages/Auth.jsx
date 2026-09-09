import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import Nav from "../components/Nav";
import { toast } from "sonner";

export default function Auth() {
  const [params] = useSearchParams();
  const [mode, setMode] = useState(params.get("mode") === "register" ? "register" : "login");
  const plan = params.get("plan");
  const nav = useNavigate();
  const { login, register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [familyName, setFamilyName] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const user = mode === "login"
        ? await login(email, password)
        : await register(email, password, familyName);
      toast.success(mode === "login" ? "Welcome back!" : "Family created!");
      if (plan && user.role !== "admin") {
        const { data } = await api.post("/payments/checkout", { lookup_key: plan, origin_url: window.location.origin });
        window.location.href = data.checkout_url;
        return;
      }
      nav(user.role === "admin" ? "/admin" : "/app");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-16">
        <h1 className="serif text-4xl font-black text-espresso">
          {mode === "login" ? "Welcome back" : "Join the club"}
        </h1>
        <p className="mt-2 text-muted2">
          {mode === "login" ? "Sign in to your family kitchen." : "Create your family container. One buyer, up to 6 profiles."}
        </p>
        <form onSubmit={submit} className="mt-8 space-y-4">
          {mode === "register" && (
            <div>
              <label className="text-sm font-bold text-espresso">Family name</label>
              <input data-testid="auth-family-name" required value={familyName} onChange={(e) => setFamilyName(e.target.value)}
                placeholder="The Bakers" className="mt-1 w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
            </div>
          )}
          <div>
            <label className="text-sm font-bold text-espresso">Email</label>
            <input data-testid="auth-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
          </div>
          <div>
            <label className="text-sm font-bold text-espresso">Password</label>
            <input data-testid="auth-password" type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full px-4 py-3 rounded-xl border-2 border-espresso/10 focus:border-terracotta outline-none"/>
            <p className="text-xs text-muted2 mt-1">Min 8 characters.</p>
          </div>
          <button data-testid="auth-submit" type="submit" disabled={busy} className="btn-pill btn-primary w-full justify-center">
            {busy ? "…" : (mode === "login" ? "Sign in" : "Create account")}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-muted2">
          {mode === "login" ? "New here? " : "Already a member? "}
          <button data-testid="auth-toggle-mode" onClick={() => setMode(mode === "login" ? "register" : "login")} className="text-terracotta font-bold underline">
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
        <p className="mt-4 text-center text-sm">
          <Link data-testid="auth-redeem" to="/redeem" className="text-sage font-bold">Have a redeem code? Enter it →</Link>
        </p>
        <p className="mt-2 text-center text-sm">
          <Link data-testid="auth-forgot" to="/forgot" className="text-muted2 underline">Forgot password?</Link>
        </p>
      </div>
    </div>
  );
}
