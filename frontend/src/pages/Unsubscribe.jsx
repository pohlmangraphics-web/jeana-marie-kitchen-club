import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import Nav from "../components/Nav";
import Footer from "../components/Footer";
import { api } from "../lib/api";

export default function Unsubscribe() {
  const [params] = useSearchParams();
  const token = params.get("token") || "";
  const [state, setState] = useState({ loading: true, ok: false, message: "" });

  useEffect(() => {
    if (!token) { setState({ loading: false, ok: false, message: "Missing unsubscribe token." }); return; }
    api.get(`/unsubscribe?token=${encodeURIComponent(token)}`)
      .then(r => setState({ loading: false, ok: r.data.ok, message: r.data.message }))
      .catch(() => setState({ loading: false, ok: false, message: "Something went wrong." }));
  }, [token]);

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <p className="script text-3xl text-terracotta">Preferences</p>
        <h1 className="serif text-4xl font-black text-espresso">Unsubscribe</h1>
        <p data-testid="unsubscribe-status" className="mt-6 text-muted2">{state.loading ? "…" : state.message}</p>
        {state.ok && <p className="mt-4 text-sm text-muted2">You can resubscribe any time from your account preferences.</p>}
        <Link data-testid="unsubscribe-home" to="/" className="btn-pill btn-outline mt-8 inline-flex">Back home</Link>
      </div>
      <Footer/>
    </div>
  );
}
