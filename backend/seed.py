"""Seed initial admin + demo data for Jeana Marie's Kitchen Club."""
import asyncio
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv(Path(__file__).parent / ".env")
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]


def h(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def uid():
    return str(uuid.uuid4())


def now_iso():
    return datetime.now(timezone.utc).isoformat()


ADMIN = {
    "id": uid(),
    "email": "admin@jeanamarie.club",
    "family_name": "Jeana Marie",
    "password_hash": h("JeanaAdmin2026!"),
    "role": "admin",
    "membership_expires_at": (datetime.now(timezone.utc) + timedelta(days=3650)).isoformat(),
    "created_at": now_iso(),
}

DEMO = {
    "id": uid(),
    "email": "demo@family.com",
    "family_name": "The Bakers",
    "password_hash": h("DemoFamily123!"),
    "role": "family",
    "membership_expires_at": (datetime.now(timezone.utc) + timedelta(days=365)).isoformat(),
    "created_at": now_iso(),
}


RECIPES = [
    {
        "id": uid(), "title": "Apple Cinnamon Snack Muffins", "tier": "little",
        "description": "Simple parent-guided muffins - little ones stir and sprinkle cinnamon.",
        "ingredients": ["1 cup flour", "1/2 cup sugar", "1 tsp baking powder", "1 tsp cinnamon",
                        "1 large apple, chopped", "1 egg", "1/2 cup milk", "1/4 cup oil"],
        "steps": ["Preheat oven to 375F.", "Mix dry ingredients in a bowl.",
                  "Have your little chef stir in the wet ingredients.",
                  "Fold in the chopped apple.", "Spoon into muffin tins.",
                  "Bake 18-20 minutes until golden."],
        "prep_time": 10, "cook_time": 20, "servings": 12,
        "photo_url": "https://images.unsplash.com/photo-1607958996333-41aef7caefaa?w=800",
        "homeschool_topic": "Fractions & Measuring",
        "lesson_plan": "Talk about fractions using 1/2 cup vs 1/4 cup. Count apple pieces.",
        "published_at": now_iso(), "is_sample": True, "created_at": now_iso(),
    },
    {
        "id": uid(), "title": "Rainbow Veggie Wraps", "tier": "junior",
        "description": "Kid-driven wraps that teach food groups and knife safety.",
        "ingredients": ["4 large tortillas", "1 cup hummus", "1 bell pepper, sliced",
                        "1 carrot, shredded", "1 cup spinach", "1/2 cucumber, sliced"],
        "steps": ["Lay tortillas flat.", "Spread hummus on each.",
                  "Add veggies in a rainbow line.", "Roll tightly and slice."],
        "prep_time": 15, "cook_time": 0, "servings": 4,
        "photo_url": "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?w=800",
        "homeschool_topic": "Nutrition & Food Groups",
        "lesson_plan": "Identify each color and what nutrients it provides.",
        "published_at": now_iso(), "is_sample": True, "created_at": now_iso(),
    },
    {
        "id": uid(), "title": "Teen Chef Chicken Stir-Fry", "tier": "teen",
        "description": "Independent recipe with meal costing worksheet.",
        "ingredients": ["1 lb chicken breast", "2 cups broccoli", "1 bell pepper",
                        "3 cloves garlic", "3 tbsp soy sauce", "1 tbsp sesame oil", "2 cups cooked rice"],
        "steps": ["Cut chicken into cubes.", "Heat oil in a wok or large pan.",
                  "Cook chicken until browned.", "Add garlic and veggies.",
                  "Stir in soy sauce.", "Serve over rice."],
        "prep_time": 15, "cook_time": 15, "servings": 4,
        "photo_url": "https://images.unsplash.com/photo-1512058564366-18510be2db19?w=800",
        "homeschool_topic": "Meal Costing & Math",
        "lesson_plan": "Use the meal costing worksheet to calculate cost per serving.",
        "published_at": now_iso(), "is_sample": True, "created_at": now_iso(),
    },
    {
        "id": uid(), "title": "20-Minute Sheet Pan Salmon", "tier": "adult",
        "description": "Weeknight-fast, one pan, minimal cleanup.",
        "ingredients": ["4 salmon fillets", "1 lb asparagus", "2 tbsp olive oil",
                        "2 cloves garlic minced", "1 lemon", "salt and pepper"],
        "steps": ["Preheat oven to 425F.", "Toss asparagus with oil, garlic, salt.",
                  "Place salmon on the sheet pan with asparagus.", "Squeeze lemon over.",
                  "Bake 12-15 minutes until salmon flakes."],
        "prep_time": 5, "cook_time": 15, "servings": 4,
        "photo_url": "https://images.unsplash.com/photo-1467003909585-2f8a72700288?w=800",
        "homeschool_topic": "Time Management",
        "lesson_plan": "Discuss oven temperature conversions (F to C).",
        "published_at": now_iso(), "is_sample": False, "created_at": now_iso(),
    },
    {
        "id": uid(), "title": "Weeknight Beef Tacos", "tier": "adult",
        "description": "Family-favorite tacos ready in 20 minutes.",
        "ingredients": ["1 lb ground beef", "1 packet taco seasoning", "8 tortillas",
                        "shredded lettuce", "diced tomato", "shredded cheese", "sour cream"],
        "steps": ["Brown beef in a skillet.", "Add seasoning and 1/2 cup water.",
                  "Simmer 5 minutes.", "Warm tortillas.", "Assemble tacos with toppings."],
        "prep_time": 5, "cook_time": 15, "servings": 4,
        "photo_url": "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?w=800",
        "homeschool_topic": "Cultural Cuisine",
        "lesson_plan": "Explore the origin of tacos and Mexican culinary traditions.",
        "published_at": now_iso(), "is_sample": False, "created_at": now_iso(),
    },
    {
        "id": uid(), "title": "Rainbow Fruit Kabobs", "tier": "little",
        "description": "Threading practice for fine motor skills.",
        "ingredients": ["strawberries", "orange slices", "pineapple chunks",
                        "green grapes", "blueberries", "wooden skewers"],
        "steps": ["Wash and prep fruit.", "Thread fruit onto skewers in rainbow order.",
                  "Chill and serve."],
        "prep_time": 10, "cook_time": 0, "servings": 6,
        "photo_url": "https://images.unsplash.com/photo-1490474418585-ba9bad8fd0ea?w=800",
        "homeschool_topic": "Colors & Patterns",
        "lesson_plan": "Identify rainbow order (ROY G BIV) with the fruit colors.",
        "published_at": now_iso(), "is_sample": False, "created_at": now_iso(),
    },
]


PRINTABLES = [
    {"id": uid(), "title": "Kitchen Tools Coloring Page", "tier": "little", "kind": "coloring",
     "description": "Whisk, pan, spoon and rolling pin ready to be colored in.",
     "content": "Color each tool. Say its name out loud with your grown-up.",
     "created_at": now_iso()},
    {"id": uid(), "title": "Food Group Match Worksheet", "tier": "little", "kind": "food_id",
     "description": "Draw a line from each food to its group.",
     "content": "Groups: Fruit, Grain, Dairy, Protein, Vegetable",
     "created_at": now_iso()},
    {"id": uid(), "title": "My Blank Shopping List", "tier": "junior", "kind": "shopping_list",
     "description": "20 blank lines for your grocery list. Check them off in the store!",
     "content": "", "created_at": now_iso()},
    {"id": uid(), "title": "Meal Costing Worksheet", "tier": "teen", "kind": "meal_costing",
     "description": "Enter store prices and calculate cost per serving.",
     "content": "", "created_at": now_iso()},
    {"id": uid(), "title": "Weekly Family Learning Guide - Fractions in the Kitchen", "tier": "junior", "kind": "lesson_plan",
     "description": "One-page family learning guide tying this week's muffin recipe to fractions.",
     "content": "Objective: Recognize 1/4, 1/2, 3/4 cup measurements.\n\nActivity: While measuring, pause and ask the child to identify each fraction.\n\nExtension: Combine 1/4 + 1/4 = 1/2. Prove it in the measuring cup!",
     "created_at": now_iso()},
]


async def main():
    if not await db.users.find_one({"email": ADMIN["email"]}):
        await db.users.insert_one(ADMIN)
        print(f"Admin created: {ADMIN['email']} / JeanaAdmin2026!")
    else:
        print("Admin exists")
    if not await db.users.find_one({"email": DEMO["email"]}):
        await db.users.insert_one(DEMO)
        # add profiles
        for p in [
            {"name": "Emma", "tier": "little", "avatar_emoji": "🧒"},
            {"name": "Liam", "tier": "junior", "avatar_emoji": "👦"},
            {"name": "Sofia", "tier": "teen", "avatar_emoji": "👧"},
            {"name": "Parent", "tier": "adult", "avatar_emoji": "👩‍🍳"},
        ]:
            await db.profiles.insert_one({
                "id": uid(), "user_id": DEMO["id"], "photo_opt_in": False,
                "pin": None, "created_at": now_iso(), **p,
            })
        print(f"Demo family created: {DEMO['email']} / DemoFamily123!")
    else:
        print("Demo family exists")

    if await db.recipes.count_documents({}) == 0:
        await db.recipes.insert_many(RECIPES)
        print(f"Inserted {len(RECIPES)} recipes")
    if await db.printables.count_documents({}) == 0:
        await db.printables.insert_many(PRINTABLES)
        print(f"Inserted {len(PRINTABLES)} printables")


if __name__ == "__main__":
    asyncio.run(main())
