/* Source-level wording guard for public-facing copy: "homeschool" may only appear inside the approved audience sentence. */
const fs = require("fs");
const path = require("path");

const SRC = path.join(__dirname, "..");
const APPROVED = "Created for families, homeschoolers, after-school learning, community groups, and children who simply enjoy cooking.";
const FILES = [
  "pages/Landing.jsx", "pages/Pricing.jsx", "pages/FAQ.jsx", "pages/Terms.jsx", "pages/Privacy.jsx", "pages/Gift.jsx",
  "pages/Dashboard.jsx", "pages/Library.jsx", "pages/Book.jsx", "pages/Printables.jsx", "pages/Recipe.jsx",
  "components/Nav.jsx", "components/Footer.jsx", "components/OnboardingTour.jsx", "lib/tiers.js", "../public/index.html",
];

const strip = (txt) => txt.split(APPROVED).join("").replace(/homeschool_topic/g, "").replace(/Homeschool topic/g, "");

test.each(FILES)("%s has no homeschool-first wording outside the audience sentence", (f) => {
  const txt = fs.readFileSync(path.join(SRC, f), "utf8");
  expect(strip(txt).toLowerCase()).not.toContain("homeschool");
});

test.each(FILES)("%s has no retired tier terminology", (f) => {
  const txt = fs.readFileSync(path.join(SRC, f), "utf8");
  expect(txt).not.toMatch(/Mom & Dad|Grown-ups|Adult Kitchen|"adult"(?!_photo_upload)|Teen Kitchen \(10–15\)|four books/);
});

test("landing exposes the skills section for all five tiers and the audience sentence", () => {
  const txt = fs.readFileSync(path.join(SRC, "pages/Landing.jsx"), "utf8");
  expect(txt).toContain('data-testid="skills-section"');
  expect(txt).toContain("tier-skills-${t.key}");
  expect(txt).toContain("AUDIENCE_SENTENCE");
});
