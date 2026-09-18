import axios from "axios";
const BACKEND = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND}/api`;

const FIELD_LABELS = { new_password: "Password", password: "Password", email: "Email", token: "Reset link", family_name: "Family name" };

export function errorMessage(err, fallback = "Something went wrong") {
  const d = err?.response?.data?.detail;
  if (typeof d === "string" && d.trim()) return d;
  if (Array.isArray(d)) {
    const parts = d.map((it) => {
      if (typeof it === "string") return it;
      const field = Array.isArray(it?.loc) ? it.loc[it.loc.length - 1] : null;
      const label = FIELD_LABELS[field] || (typeof field === "string" ? field.replace(/_/g, " ") : null);
      const msg = typeof it?.msg === "string" ? it.msg.replace(/^String should have/, "must have").replace(/^Value error, /i, "") : "is invalid";
      return label ? `${label} ${msg}` : msg;
    }).filter(Boolean);
    if (parts.length) return parts.join(". ");
  }
  if (d && typeof d === "object" && typeof d.msg === "string") return d.msg;
  if (err?.response?.status === 429) return "Too many attempts. Please wait and try again.";
  if (err?.message === "Network Error") return "Can't reach the server. Check your connection and try again.";
  return fallback;
}

export const api = axios.create({ baseURL: API });
api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem("jmk_token");
  if (t) cfg.headers.Authorization = `Bearer ${t}`;
  return cfg;
});
