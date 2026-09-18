import { useState } from "react";
import { FileText } from "lucide-react";
import { toast } from "sonner";
import { api, errorMessage } from "../lib/api";

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a"); a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}

export function GenerateCardButton({ recipe }) {
  const [busy, setBusy] = useState(false);

  const run = async () => {
    if (busy) return;
    if (!window.confirm(`Generate a recipe card PDF for "${recipe.title}" from its saved recipe data?\n\nThis previews the branded card and downloads it. It does not change the recipe.`)) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/admin/recipes/${recipe.id}/card/generate`);
      const pdf = await api.get(`/recipes/${recipe.id}/card`, { params: { source: "generated" }, responseType: "blob" });
      downloadBlob(pdf.data, data.filename);
      const note = data.uploaded_card_valid ? " Members still receive the uploaded card." : " Members receive this generated card.";
      toast.success(`Recipe card ready — ${data.pages} page${data.pages === 1 ? "" : "s"}${data.image_included ? ", with photo" : ""}.${note}`);
    } catch (err) {
      toast.error(errorMessage(err, "Couldn't generate the recipe card. Please try again."));
    } finally { setBusy(false); }
  };

  return (
    <button type="button" data-testid={`admin-recipe-gencard-${recipe.id}`} onClick={run} disabled={busy} aria-busy={busy}
      title="Generate / regenerate recipe card PDF" className="p-2 rounded-lg hover:bg-honey/30 text-espresso disabled:opacity-50">
      <FileText className={`w-4 h-4 ${busy ? "animate-pulse" : ""}`}/>
    </button>
  );
}
