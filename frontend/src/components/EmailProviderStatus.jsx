import { useCallback, useEffect, useState } from "react";
import { RefreshCw, Mail, AlertTriangle } from "lucide-react";
import { api } from "../lib/api";

export function describeEmailStatus(s) {
  if (!s) return { state: "unavailable", label: "Email status unavailable" };
  if (s.resend_active) return { state: "resend", label: "Email: Resend" };
  if (s.use_resend) return { state: "warning", label: "Email: Emergent (fallback)", note: "Resend is enabled but not active — check the key in Preview config." };
  return { state: "emergent", label: "Email: Emergent" };
}

const STYLES = {
  resend: "bg-sage/15 border-sage text-espresso",
  emergent: "bg-honey/15 border-honey text-espresso",
  warning: "bg-terracotta/10 border-terracotta text-espresso",
  unavailable: "bg-espresso/5 border-espresso/20 text-muted2",
};

export function EmailProviderStatus() {
  const [status, setStatus] = useState(null);
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setBusy(true);
    try {
      const r = await api.get("/admin/email/status");
      setStatus(r.data); setFailed(false);
    } catch { setStatus(null); setFailed(true); }
    finally { setBusy(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const d = describeEmailStatus(failed ? null : status);
  const Icon = d.state === "warning" ? AlertTriangle : Mail;
  return (
    <div data-testid="email-provider-status" data-state={d.state} role="status" aria-live="polite"
      className={`card-warm border-l-4 px-4 py-3 flex items-center gap-3 ${STYLES[d.state]}`}>
      <Icon size={18} aria-hidden="true" className="shrink-0"/>
      <div className="min-w-0 flex-1">
        <p data-testid="email-provider-label" className="text-sm font-bold">{busy && !status && !failed ? "Checking email provider…" : d.label}</p>
        {d.note && <p data-testid="email-provider-note" className="text-xs text-muted2 mt-0.5">{d.note}</p>}
      </div>
      <button type="button" data-testid="email-provider-refresh" onClick={load} disabled={busy} aria-label="Refresh email provider status"
        className="btn-pill border-2 border-espresso/15 px-3 py-1.5 text-xs font-bold hover:border-terracotta disabled:opacity-50 inline-flex items-center gap-1.5">
        <RefreshCw size={14} className={busy ? "animate-spin" : ""} aria-hidden="true"/> Refresh
      </button>
    </div>
  );
}
