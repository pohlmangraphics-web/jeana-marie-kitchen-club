export const TIERS = [
  { key: "little", name: "Little Chefs", ages: "Ages 3–5", short: "3–5", emoji: "🧒",
    skills: "Explore food, senses, colors, counting, and simple kitchen tasks.",
    color: "bg-terracotta/10 border-terracotta/30", accent: "text-terracotta" },
  { key: "junior", name: "Junior Cooks", ages: "Ages 6–9", short: "6–9", emoji: "👦",
    skills: "Practice recipes, measurement, nutrition, kitchen safety, reading, and math.",
    color: "bg-honey/30 border-honey", accent: "text-espresso" },
  { key: "young", name: "Young Chefs", ages: "Ages 10–12", short: "10–12", emoji: "🧑‍🍳",
    skills: "Build skills in meal planning, food science, budgeting, nutrition, and cooking techniques.",
    color: "bg-sage/15 border-sage/40", accent: "text-sage" },
  { key: "teen", name: "Teen Kitchen", ages: "Ages 13–15+", short: "13–15+", emoji: "👩‍🍳",
    skills: "Develop independent cooking, meal costing, grocery shopping, nutrition, and practical life skills.",
    color: "bg-espresso/5 border-espresso/20", accent: "text-espresso" },
  { key: "family", name: "Family Kitchen", ages: "Whole household", short: "All ages", emoji: "🍳",
    skills: "Recipes and resources for parents, caregivers, and the whole household; not a child age tier.",
    color: "bg-cream border-honey", accent: "text-terracotta" },
];

export const TIER_KEYS = TIERS.map((t) => t.key);
export const CHILD_TIER_KEYS = TIER_KEYS.filter((k) => k !== "family");
const LEGACY = { adult: "family" };

export const normalizeTier = (t) => LEGACY[t] || t;
export const tierByKey = (t) => TIERS.find((x) => x.key === normalizeTier(t)) || null;
export const tierName = (t) => tierByKey(t)?.name || t || "";
export const tierLabel = (t) => { const x = tierByKey(t); return x ? (x.key === "family" ? x.name : `${x.name} (${x.short})`) : t || ""; };

export const AUDIENCE_SENTENCE = "Created for families, homeschoolers, after-school learning, community groups, and children who simply enjoy cooking.";
export const TAGLINE = "Cooking and learning activities for families";
