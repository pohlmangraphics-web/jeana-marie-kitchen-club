import { useState } from "react";
import { Send } from "lucide-react";
import { toast } from "sonner";
import { api, errorMessage } from "../lib/api";

const PROVIDER_LABEL = { resend: "Resend", emergent: "Emergent" };

export function WeeklyDropPreviewButton() {
  const [busy, setBusy] = useState(false);

  const send = async () => {
    if (busy) return;
    setBusy(true);
    try {
      const { data: { recipient } } = await api.get("/admin/email/weekly-drop/preview-recipient");
      if (!window.confirm(`Send a [PREVIEW] of this week's drop email to ${recipient}?\n\nNothing is sent to families.`)) return;
      const { data } = await api.post("/admin/email/weekly-drop/preview");
      const provider = PROVIDER_LABEL[data.provider] || "email";
      toast.success(`Preview sent to ${data.recipient} via ${provider} — "${data.recipe}"`);
    } catch (err) {
      toast.error(errorMessage(err, "Couldn't send the preview. Please try again."));
    } finally { setBusy(false); }
  };

  return (
    <button type="button" data-testid="weekly-drop-preview" onClick={send} disabled={busy} aria-busy={busy}
      className="btn-pill btn-outline !py-1 !px-3 text-xs inline-flex items-center gap-1.5 disabled:opacity-60">
      <Send size={12} aria-hidden="true"/>{busy ? "Sending preview…" : "Send preview to me"}
    </button>
  );
}
