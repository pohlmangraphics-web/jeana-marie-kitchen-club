import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { LogOut, Shield } from "lucide-react";
import Logo from "./Logo";
import { useEffect, useState } from "react";
import { api } from "../lib/api";

export default function Nav() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [hasCustomLogo, setHasCustomLogo] = useState(false);
  useEffect(() => { api.get("/branding/logo").then(r => setHasCustomLogo(!!r.data.file_id)).catch(() => {}); }, []);

  return (
    <header className="sticky top-0 z-40 glass border-b border-terracotta/10">
      <div className="max-w-7xl mx-auto flex items-center justify-between px-6 py-3">
        <Link to="/" data-testid="nav-home" className="flex items-center gap-3">
          <Logo size={64} hasCustom={hasCustomLogo}/>
          <div className="leading-tight hidden sm:block">
            <div className="script text-3xl text-terracotta -mb-1">Jeana Marie's</div>
            <div className="serif text-base text-espresso font-bold">Kitchen Club</div>
          </div>
        </Link>
        <nav className="flex items-center gap-3">
          {user ? (
            <>
              <Link data-testid="nav-dashboard" to="/app" className="text-sm font-semibold hover:text-terracotta">My Kitchen</Link>
              <Link data-testid="nav-library" to="/app/library" className="text-sm font-semibold hover:text-terracotta hidden sm:inline">Library</Link>
              <Link data-testid="nav-printables" to="/app/printables" className="text-sm font-semibold hover:text-terracotta hidden sm:inline">Printables</Link>
              <Link data-testid="nav-redeem" to="/redeem" className="text-sm font-semibold hover:text-terracotta hidden sm:inline">Redeem</Link>
              {user.role === "admin" && (
                <Link data-testid="nav-admin" to="/admin" className="flex items-center gap-1 text-sm font-semibold text-sage"><Shield className="w-4 h-4"/> Admin</Link>
              )}
              <button data-testid="nav-logout" onClick={() => { logout(); nav("/"); }} className="btn-pill btn-outline text-sm !px-4 !py-2">
                <LogOut className="w-4 h-4"/> Sign Out
              </button>
            </>
          ) : (
            <>
              <Link data-testid="nav-signin" to="/auth" className="text-sm font-semibold hover:text-terracotta">Sign In</Link>
              <Link data-testid="nav-join" to="/auth?mode=register" className="btn-pill btn-primary text-sm !px-4 !py-2">Join the Club</Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}
