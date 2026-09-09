import { useEffect, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import Nav from "../components/Nav";
import { api } from "../lib/api";
import { useAuth } from "../lib/auth";
import { CheckCircle2 } from "lucide-react";

export default function PaymentSuccess() {
  const [params] = useSearchParams();
  const sid = params.get("session_id");
  const { refresh } = useAuth();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    if (!sid) return;
    let tries = 0;
    const poll = async () => {
      tries++;
      try {
        const { data } = await api.get(`/payments/status/${sid}`);
        if (data.payment_status === "paid") {
          setStatus("paid");
          await refresh();
          return;
        }
        if (data.status === "expired" || data.status === "failed") { setStatus("failed"); return; }
      } catch {}
      if (tries < 20) setTimeout(poll, 2000);
      else setStatus("timeout");
    };
    poll();
  }, [sid, refresh]);

  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        {status === "paid" && (
          <>
            <CheckCircle2 className="w-20 h-20 text-sage mx-auto"/>
            <h1 className="mt-6 serif text-4xl font-black text-espresso">Welcome to the club!</h1>
            <p className="mt-3 text-muted2">Your membership is active.</p>
            <Link data-testid="success-go-kitchen" to="/app" className="btn-pill btn-primary mt-8 inline-flex">Enter Your Kitchen →</Link>
          </>
        )}
        {status === "checking" && <p className="text-muted2">Confirming your payment…</p>}
        {(status === "failed" || status === "timeout") && (
          <>
            <h1 className="serif text-3xl font-black text-espresso">Something's off</h1>
            <p className="mt-2 text-muted2">Try again or contact support.</p>
            <Link to="/" className="btn-pill btn-outline mt-6 inline-flex">Back home</Link>
          </>
        )}
      </div>
    </div>
  );
}
