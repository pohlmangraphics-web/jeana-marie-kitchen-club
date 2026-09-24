"""One-time Preview script: upload 4 photos + create 5 approved launch recipes via the public API. Idempotent by exact title."""
import os, sys, json, requests
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
from creds import ADMIN  # noqa

API = os.environ["REACT_APP_BACKEND_URL"].rstrip("/") + "/api"
PUB = os.environ["APP_PUBLIC_URL"].rstrip("/") + "/api"
D = Path("/app/memory/launch_recipes")
tok = requests.post(f"{API}/auth/login", json=ADMIN).json()["token"]
H = {"Authorization": f"Bearer {tok}"}

def upload(fn):
    r = requests.post(f"{API}/files/upload", headers=H, data={"purpose": "recipe_photo"},
                      files={"file": (fn, (D / fn).read_bytes(), "image/jpeg")}); r.raise_for_status()
    fid = r.json()["file_id"]; return fid, f"{PUB}/files/{fid}"

photos = {k: upload(f"{k}_photo.jpg") for k in ("pizza", "cookies", "tacos", "grilled")}
BURGER_URL = "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=1200"

R = [
 dict(title="Mini Rainbow Pizza Bites", tier="little", homeschool_topic="Colors, Counting & Simple Kitchen Tasks",
  description="Colorful mini pizzas that let little chefs practice spreading, sprinkling, counting, and creating patterns while an adult handles the hot oven.",
  prep_time=15, cook_time=10, servings=12, yield_text="12 mini pizzas", time_text="Prep 15 minutes · Cook 8–10 minutes · Total approximately 25 minutes",
  ingredients=["12 mini whole-wheat English muffin halves or mini naan","1/2 cup pizza sauce","1 cup shredded mozzarella","1/4 cup finely diced bell pepper","1/4 cup finely chopped spinach","1/4 cup finely shredded carrot","1/4 cup pineapple tidbits, finely chopped","12 small turkey or vegetable pepperoni pieces, optional"],
  steps=["Heat the oven to 400°F.","Place the English muffin halves or mini naan on a baking sheet.","Let the child spread a small amount of pizza sauce onto each one.","Sprinkle each pizza with mozzarella.","Add small amounts of colorful toppings to create a rainbow or pattern.","An adult places the baking sheet in the oven.","Bake for 8–10 minutes, until the cheese is melted and bubbly.","An adult removes the baking sheet. Let the pizzas cool before serving."],
  safety_notes=["An adult must handle the oven and hot baking sheet.","Use dry oven mitts.","Cut the vegetables into age-appropriate pieces before the child begins.","Check the pizza temperature before serving."],
  lesson_plan="Rainbow Pizza Patterns: Name the colors of the toppings, count how many pieces go on each pizza, and create a repeating color pattern. Compare which toppings are fruits and which are vegetables.",
  photo_file_id=photos["pizza"][0], photo_url=photos["pizza"][1]),
 dict(title="Chocolate Chip Cookie Shop Cookies", tier="junior", homeschool_topic="Measurement, Fractions & Baking Science",
  description="Classic chocolate-chip cookies with lightly golden edges and soft, chewy centers. Junior cooks practice measuring, mixing, following steps, and oven safety with adult help.",
  prep_time=15, cook_time=12, servings=24, yield_text="24 cookies", time_text="Prep 15 minutes · Cook 10–12 minutes · Total approximately 30 minutes, including cooling",
  ingredients=["1/2 cup (1 stick) butter, softened","1/2 cup brown sugar","1/4 cup granulated sugar","1 egg","1 teaspoon vanilla","1 1/2 cups all-purpose flour","1/2 teaspoon baking soda","1/4 teaspoon salt","1 cup chocolate chips"],
  steps=["Heat the oven to 350°F. Line a baking sheet with parchment paper or a silicone baking mat.","In a large bowl, cream together the softened butter, brown sugar, and granulated sugar.","Mix in the egg and vanilla.","Add the flour, baking soda, and salt. Stir only until no dry flour remains.","Fold in the chocolate chips.","Scoop level tablespoon-sized portions onto the lined baking sheet, leaving approximately 2 inches between cookies.","An adult places the baking sheet in the oven.","Bake for 10–12 minutes, until the edges are lightly golden but the centers still look soft.","An adult removes the baking sheet.","Cool the cookies on the baking sheet for 5 minutes before transferring them to a cooling rack."],
  safety_notes=["An adult must supervise the oven and handle hot baking sheets.","Use dry oven mitts.","Do not eat raw dough because uncooked flour and eggs may contain harmful bacteria.","Wash hands and clean surfaces after handling raw egg."],
  tips=["The butter should be soft but not melted.","Do not overmix after adding flour.","Equal-sized scoops help the cookies bake evenly."],
  lesson_plan="Cookie Shop Math: Estimate the batch cost and divide it by 24 to calculate the cost per cookie. Choose a pretend selling price and calculate revenue and pretend profit. As an extension, calculate ingredient amounts for a half or double batch.",
  photo_file_id=photos["cookies"][0], photo_url=photos["cookies"][1]),
 dict(title="Kid-Friendly Walking Tacos", tier="junior", homeschool_topic="Measuring, Food Groups & Build-Your-Own Meals",
  description="A fun build-your-own meal served in individual chip bags. Junior cooks practice measuring, following steps, identifying food groups, and creating their own topping combinations while an adult cooks the meat.",
  prep_time=15, cook_time=10, servings=6, time_text="Prep 15 minutes · Cook approximately 10 minutes · Total approximately 25 minutes",
  ingredients=["6 individual bags of Doritos or Fritos","1 pound lean ground beef or ground turkey","1 packet mild taco seasoning","1/2 cup water","1 cup shredded cheddar cheese","1/2 cup corn","1/2 cup diced tomatoes, optional","1/2 cup shredded lettuce","Salsa, as desired","Sour cream, as desired","Sliced black olives, optional"],
  steps=["An adult browns the ground beef or turkey in a skillet and drains excess grease.","Add the taco seasoning and water. Simmer for 3–5 minutes.","Confirm the ground meat reaches an internal temperature of 160°F.","Gently crush the chips inside the unopened bags.","Cut or tear open the top of each bag.","Add a scoop of cooked taco meat.","Add cheese, corn, lettuce, tomatoes, and any optional toppings.","Finish with salsa and sour cream as desired.","Serve with a fork and eat directly from the bag."],
  safety_notes=["An adult should cook and drain the meat.","Keep raw meat separate from toppings and cooked food.","Wash hands and sanitize utensils and surfaces that contact raw meat.","Never place cooked meat back on a plate that held raw meat.","Verify the meat reaches 160°F."],
  lesson_plan="Build a Balanced Taco: Identify the food group represented by each ingredient. Design a preferred topping combination, measure the ingredients, and compare combinations with other family members.",
  photo_file_id=photos["tacos"][0], photo_url=photos["tacos"][1]),
 dict(title="Dunkable Grilled Cheese & Tomato Soup", tier="young", homeschool_topic="Heat Control & Meal Coordination",
  description="Crispy grilled-cheese strips with warm, creamy tomato soup for dunking. Young chefs practice measuring, simmering, controlling skillet heat, timing, and coordinating two parts of a meal.",
  prep_time=10, cook_time=25, servings=4, time_text="Prep approximately 10 minutes · Cook approximately 25 minutes · Total approximately 35 minutes",
  ingredients=["Grilled Cheese: 8 slices brioche or sourdough bread","Grilled Cheese: 4 slices American cheese","Grilled Cheese: 4 slices cheddar cheese","Grilled Cheese: 2 tablespoons butter","Grilled Cheese: 1/4 cup shredded mozzarella","Tomato Soup: 1 can (28 ounces) crushed tomatoes","Tomato Soup: 1 1/2 cups vegetable broth","Tomato Soup: 1/2 cup half-and-half","Tomato Soup: 1 tablespoon butter","Tomato Soup: 1 teaspoon Italian seasoning","Tomato Soup: 1/2 teaspoon garlic powder","Tomato Soup: 1/2 teaspoon sugar","Tomato Soup: Salt and pepper to taste"],
  steps=["Melt 1 tablespoon butter in a pot over medium heat.","Add the crushed tomatoes, vegetable broth, Italian seasoning, garlic powder, and sugar.","Simmer gently for 15 minutes.","Stir in the half-and-half and warm gently. Do not boil.","Season with salt and pepper to taste.","Butter one side of each bread slice.","Place one slice of American cheese, one slice of cheddar, and one-fourth of the mozzarella between each pair of bread slices, with the buttered sides facing outward.","Cook the sandwiches in a skillet over medium-low heat for 3–4 minutes per side, until golden and the cheese is melted.","Cut each sandwich into strips for dunking."],
  safety_notes=["Use care around the hot stove, soup pot, skillet, steam, and splattering liquids.","Turn skillet handles inward.","Use dry oven mitts or potholders when needed.","Adult supervision is recommended until the child demonstrates safe stovetop skills.","Refrigerate leftovers promptly."],
  lesson_plan="Grilled Cheese Dunk-Off: Try different bread or cheese combinations and score each for crispness, cheese melt, flavor, and dunkability. Record the results and select a family favorite. As an extension, record ingredient prices and divide the meal cost by four to find the cost per serving.",
  photo_file_id=photos["grilled"][0], photo_url=photos["grilled"][1]),
 dict(title="Ultimate Smash Burgers", tier="teen", homeschool_topic="High-Heat Cooking, Food Safety & Meal Costing",
  description="Crispy-edged, cheesy double smash burgers with quick homemade sauce and build-your-own toppings. Teen cooks practice safe handling of ground beef, high-heat cooking, temperature testing, timing, and meal assembly.",
  prep_time=10, cook_time=10, servings=4, yield_text="4 double-patty burgers", time_text="Prep 10 minutes · Cook 10 minutes · Total 20 minutes",
  ingredients=["Burgers: 1 pound ground beef, preferably 80/20","Burgers: 4 hamburger buns","Burgers: 4 slices American or cheddar cheese","Burgers: 1 tablespoon butter","Burgers: Salt and pepper","Optional toppings: Shredded lettuce","Optional toppings: Tomato slices","Optional toppings: Pickles","Optional toppings: Thinly sliced onion","Optional toppings: Ketchup","Optional toppings: Mustard","Optional toppings: Burger sauce","Easy Burger Sauce: 1/4 cup mayonnaise","Easy Burger Sauce: 2 tablespoons ketchup","Easy Burger Sauce: 1 tablespoon yellow mustard","Easy Burger Sauce: 1 tablespoon finely chopped pickles","Easy Burger Sauce: 1/2 teaspoon pickle juice"],
  steps=["Mix the mayonnaise, ketchup, mustard, chopped pickles, and pickle juice. Refrigerate until needed.","Prepare the toppings before handling raw beef.","Divide the beef into 8 equal, loosely formed balls. Do not pack them tightly.","Heat a large skillet or griddle over medium-high heat.","Working in batches, place 2–3 beef balls on the hot surface and immediately press each into a thin patty with a sturdy metal spatula.","Season with salt and pepper. Cook for approximately 2 minutes, until the edges are browned and crisp.","Scrape underneath each patty, flip it, and cook for another 1–2 minutes. Add cheese during the final minute.","Confirm every patty reaches an internal temperature of 160°F.","Lightly butter the buns and toast them cut-side down until golden.","Build each burger with a bottom bun, sauce, lettuce, two patties, pickles, onion, tomato, additional sauce, and the top bun."],
  safety_notes=["Keep raw beef separate from buns, toppings, utensils, and cooked food.","Wash hands with soap and water after handling raw beef.","Clean and sanitize every plate, utensil, and surface that contacts raw beef.","Never use a raw-meat plate or utensil for cooked burgers.","Confirm the patties reach 160°F.","The skillet, spatula, grease, and steam will be extremely hot.","Adult supervision is recommended until the teen demonstrates safe high-heat cooking."],
  tips=["Loosely formed meat creates crispier edges.","Prepare toppings first because thin patties cook quickly.","Use a firm metal spatula and a splatter screen if available.","Ventilate the kitchen.","Refrigerate leftover sauce promptly."],
  lesson_plan="Burger Shop Cost Challenge: Calculate the cost of four double burgers, including buns, beef, cheese, sauce, and toppings. Divide the total by four to find the cost per burger. Compare it with a restaurant burger, then choose a pretend selling price that covers the ingredients and leaves a pretend profit.",
  photo_url=BURGER_URL),
]
existing = {r["title"] for r in requests.get(f"{API}/recipes", headers=H).json()}
out = []
for body in R:
    if body["title"] in existing: print("EXISTS, skipping:", body["title"]); continue
    body["is_sample"] = False
    r = requests.post(f"{API}/recipes", headers=H, json=body); r.raise_for_status()
    d = r.json(); out.append({"id": d["id"], "title": d["title"], "tier": d["tier"], "photo_file_id": d.get("photo_file_id")})
print(json.dumps(out, indent=1)); print("photos:", {k: v[0] for k, v in photos.items()})
