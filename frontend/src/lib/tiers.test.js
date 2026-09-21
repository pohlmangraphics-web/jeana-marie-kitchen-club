import { TIERS, TIER_KEYS, CHILD_TIER_KEYS, tierLabel, tierName, normalizeTier, AUDIENCE_SENTENCE, TAGLINE } from "./tiers";

test("five tiers in approved order with approved names, ages and skills", () => {
  expect(TIER_KEYS).toEqual(["little", "junior", "young", "teen", "family"]);
  expect(CHILD_TIER_KEYS).toEqual(["little", "junior", "young", "teen"]);
  expect(TIERS.map((t) => [t.name, t.ages])).toEqual([
    ["Little Chefs", "Ages 3–5"], ["Junior Cooks", "Ages 6–9"], ["Young Chefs", "Ages 10–12"], ["Teen Kitchen", "Ages 13–15+"], ["Family Kitchen", "Whole household"],
  ]);
  expect(TIERS.map((t) => t.skills)).toEqual([
    "Explore food, senses, colors, counting, and simple kitchen tasks.",
    "Practice recipes, measurement, nutrition, kitchen safety, reading, and math.",
    "Build skills in meal planning, food science, budgeting, nutrition, and cooking techniques.",
    "Develop independent cooking, meal costing, grocery shopping, nutrition, and practical life skills.",
    "Recipes and resources for parents, caregivers, and the whole household; not a child age tier.",
  ]);
});

test("legacy adult maps to family everywhere", () => {
  expect(normalizeTier("adult")).toBe("family");
  expect(tierName("adult")).toBe("Family Kitchen");
  expect(tierLabel("adult")).toBe("Family Kitchen");
  expect(tierLabel("teen")).toBe("Teen Kitchen (13–15+)");
  expect(tierLabel("young")).toBe("Young Chefs (10–12)");
  expect(tierName("unknown")).toBe("unknown");
});

test("audience sentence is the only sanctioned homeschool mention and tagline has none", () => {
  expect(AUDIENCE_SENTENCE).toBe("Created for families, homeschoolers, after-school learning, community groups, and children who simply enjoy cooking.");
  expect(TAGLINE.toLowerCase()).not.toContain("homeschool");
  expect(JSON.stringify(TIERS).toLowerCase()).not.toMatch(/adult|mom & dad|grown-ups|homeschool/);
});
