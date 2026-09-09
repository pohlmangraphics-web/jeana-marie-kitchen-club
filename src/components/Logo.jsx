import { API } from "../lib/api";

/**
 * Brand logo. If admin has uploaded a custom logo, we use /api/branding/logo/raw.
 * Otherwise we render an inline SVG "Recipe Book Stack" - stacked cookbooks with chef hat and wooden spoon,
 * in the locked Kitchen Club palette (terracotta, honey, sage, buttercream, espresso).
 */
export default function Logo({ size = 40, hasCustom = false, className = "" }) {
  if (hasCustom) {
    return (
      <img src={`${API}/branding/logo/raw`} alt="Jeana Marie's Kitchen Club" width={size} height={size} className={className}/>
    );
  }
  return (
    <svg
      viewBox="0 0 64 64"
      width={size}
      height={size}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
      aria-label="Jeana Marie's Kitchen Club logo"
    >
      {/* Buttercream backdrop */}
      <rect x="1" y="1" width="62" height="62" rx="14" fill="#FDFBF7" stroke="#2C1E16" strokeWidth="1.5"/>
      {/* Wooden spoon (behind books) */}
      <g transform="rotate(-24 32 40)">
        <rect x="30.5" y="8" width="3" height="34" rx="1.5" fill="#C8A16A"/>
        <ellipse cx="32" cy="44" rx="6" ry="8" fill="#C8A16A" stroke="#8B6A3E" strokeWidth="1"/>
      </g>
      {/* Bottom cookbook - sage */}
      <rect x="10" y="45" width="44" height="10" rx="1.5" fill="#81B29A" stroke="#2C1E16" strokeWidth="1.4"/>
      <line x1="14" y1="49" x2="50" y2="49" stroke="#2C1E16" strokeWidth="0.8" opacity="0.4"/>
      <line x1="14" y1="52" x2="30" y2="52" stroke="#2C1E16" strokeWidth="0.8" opacity="0.4"/>
      {/* Middle cookbook - honey */}
      <rect x="13" y="35" width="38" height="10" rx="1.5" fill="#F2CC8F" stroke="#2C1E16" strokeWidth="1.4"/>
      <line x1="17" y1="39" x2="47" y2="39" stroke="#2C1E16" strokeWidth="0.8" opacity="0.4"/>
      {/* Top cookbook - terracotta */}
      <rect x="16" y="25" width="32" height="10" rx="1.5" fill="#E07A5F" stroke="#2C1E16" strokeWidth="1.4"/>
      <line x1="20" y1="29" x2="44" y2="29" stroke="#FDFBF7" strokeWidth="0.8" opacity="0.6"/>
      {/* Chef hat sitting on top */}
      <g>
        <path d="M 22 25 C 21 15 27 12 32 14 C 37 12 43 15 42 25 Z" fill="#FDFBF7" stroke="#2C1E16" strokeWidth="1.4"/>
        <circle cx="26" cy="18" r="3.5" fill="#FDFBF7" stroke="#2C1E16" strokeWidth="1"/>
        <circle cx="32" cy="15" r="4" fill="#FDFBF7" stroke="#2C1E16" strokeWidth="1"/>
        <circle cx="38" cy="18" r="3.5" fill="#FDFBF7" stroke="#2C1E16" strokeWidth="1"/>
      </g>
    </svg>
  );
}
