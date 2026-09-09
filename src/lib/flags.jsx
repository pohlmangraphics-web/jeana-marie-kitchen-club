import { createContext, useContext, useEffect, useState } from "react";
import { api } from "./api";

const FlagsCtx = createContext({});

export function FlagsProvider({ children }) {
  const [flags, setFlags] = useState({});
  const [loaded, setLoaded] = useState(false);
  const refresh = async () => {
    try { const { data } = await api.get("/flags"); setFlags(data); } catch {}
    setLoaded(true);
  };
  useEffect(() => { refresh(); }, []);
  return <FlagsCtx.Provider value={{ flags, loaded, refresh }}>{children}</FlagsCtx.Provider>;
}
export const useFlags = () => useContext(FlagsCtx);
