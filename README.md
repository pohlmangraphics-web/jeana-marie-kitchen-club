# Jeana Marie's Kitchen Club for Homeschoolers

A membership web app where Chef Jeana Marie delivers weekly recipes and homeschool-ready kitchen activities across four age tiers. Families cook, learn, and build a personalized journal cookbook together.

## What's inside

- **Public landing** with brand story, 3 free sample recipes, and pricing tiers
- **Family accounts** (JWT + bcrypt, min 8-char passwords, forgot/reset flow, rate-limited auth)
- **Up to 6 sub-profiles** per family, avatar-based switcher, COPPA-safe defaults
- **Four age-tiered books** — Little Chefs (3–5), Junior Cooks (6–9), Teen Kitchen (10–15), Mom & Dad (Quick & Easy)
- **Weekly recipe drops** + searchable archive
- **Printables library** with server-generated PDFs (coloring, food-ID, shopping list, meal costing, lesson plan)
- **Interactive meal costing tool** for the teen tier
- **Journal editor** styled like a real notebook + personalized cookbook PDF export (flag-gated)
- **Redeem codes** for Etsy purchases + **Stripe subscription checkout** for direct signups
- **Admin panel** — recipes, printables, codes, families, analytics, feature flags, branding, CSV/JSON export
- **Feature flags** — 7 features hidden behind flags for controlled MVP rollout

## Stack

- **Frontend**: React 19 + Tailwind + shadcn/ui + React Router
- **Backend**: FastAPI + Pydantic v2 + PyJWT + bcrypt + Motor + fpdf2
- **Database**: MongoDB
- **Payments**: Stripe subscriptions
- **File storage**: Emergent Object Storage
- **Auth**: JWT + bcrypt (custom)

## Local setup

**Backend**
```bash
cd backend
cp .env.example .env       # fill in real values
pip install -r requirements.txt
python seed.py             # creates admin + demo family + sample data
python setup_stripe.py     # syncs Stripe catalog (needs a Stripe key)
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

**Frontend**
```bash
cd frontend
cp .env.example .env       # set REACT_APP_BACKEND_URL
yarn install
yarn start                 # http://localhost:3000
```

## Seeded credentials (dev only)
- **Admin** — `admin@jeanamarie.club` / `JeanaAdmin2026!`
- **Demo family** — `demo@family.com` / `DemoFamily123!` (annual membership, 4 profiles)

## Feature flags

All admin-toggleable at `/admin › Flags`.

| ON by default | OFF by default (MVP-hidden) |
|---|---|
| free_samples, recipes_by_tier, printables, meal_costing, notes_and_favorites, admin_publishing, stripe_checkout, redeem_codes | kid_photo_upload, adult_photo_upload, personalized_pdf_export, profile_pins, advanced_analytics, pwa_install, weekly_challenges |

## Brand

- **Colors** — Terracotta `#E07A5F`, Honey Mustard `#F2CC8F`, Soft Sage `#81B29A`, Cream `#FDFBF7`, Espresso `#2C1E16`
- **Type** — Dancing Script + Merriweather + Nunito
- **Logo** — Recipe Book Stack: stacked cookbooks + chef hat + wooden spoon, admin-replaceable from `/admin › Branding`

## License

Proprietary — © Jeana Marie. All rights reserved.
