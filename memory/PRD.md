# Jeana Marie's Kitchen Club - PRD

## Problem Statement
Membership web app: weekly recipes + printable homeschool activities across 4 age tiers (Little 3-5, Junior 6-9, Teen 10-15, Adult). Family container model, up to 6 sub-profiles. Sold via Stripe (website) + Etsy redeem codes.

## Architecture
React + TypeScript (JS in practice) + Tailwind + shadcn | FastAPI + JWT + bcrypt | MongoDB | Stripe (claimable sandbox) | Emergent Object Storage | Server-side PDF via fpdf2

## User Personas
1. Homeschool parent (primary)
2. Time-crunched weeknight cook
3. Grandparent buying a gift code
4. Chef Jeana Marie (admin content publisher)

## Static Core Requirements
- One buyer email = one family container, up to 6 avatar sub-profiles
- Weekly recipe drops, 4 age tiers, samples free
- COPPA-safe: no solo kid login, opt-in photo uploads, text-only default for under-13
- Journal saved read-only after subscription lapses

## Implemented (Feb 2026)
- Auth: JWT + bcrypt, min 8-char password, rate limiting on all 4 auth routes with X-Forwarded-For real-IP detection, forgot/reset password flow
- Object Storage integration (photos, printables assets, logo, PDFs)
- Feature flags system: admin-toggleable in /admin > Flags tab; MVP hides kid_photo_upload, adult_photo_upload, personalized_pdf_export, profile_pins, advanced_analytics, pwa_install, weekly_challenges
- Recipes CRUD (admin) + tiered browsing + search + samples + this-week + kitchen mode toggle
- Printables library with server-generated PDFs (5 kinds) branded with Recipe Book Stack logo mark
- Meal Costing interactive worksheet with live math + saved history
- Journal (notes) with paper-lined editor; PDF export flag-gated
- Redeem codes (admin generates; family redeems; stacks with active membership)
- Stripe checkout via claimable Emergent sandbox: monthly ($9.99), 3-month ($26.99), 6-month ($49.99), annual ($89.99); webhook + polling both grant membership
- Admin panel: Recipes / Printables / Codes / Families / Analytics / Flags / Branding (logo upload) / Export (CSV+JSON for 7 entities)
- Brand: Recipe Book Stack SVG logo (stacked cookbooks + chef hat + wooden spoon; terracotta/honey/sage/cream/espresso palette); favicon.svg + og-image.svg; admin-uploadable custom logo
- Test coverage: 36/36 backend tests passing (100%), frontend smoke test 100%

## Feb 2026 Update — Checkout Regression Closed
- Fixed checkout-flow routing so signed-in unpaid users can never loop back to the Create Account form:
  - `Landing.jsx` hero + samples CTAs now route to `/pricing` (was `/auth?mode=register`)
  - `Auth.jsx` mounts with a guard: if already logged in, redirect active members → `/app`, unpaid + plan param → checkout, unpaid + no plan → `/pricing`
  - `PaymentCancel.jsx` now offers signed-in users `cancel-retry` (→/pricing) and `cancel-dashboard` (→/app) instead of only "Back home"
- Password-reset endpoint already invalidates the reset token via `$unset` after a successful reset; single-use guarantee now verified in `test_checkout_regression.py`
- All 7 launch-readiness checkout scenarios verified end-to-end in iteration_13 (real Stripe test checkout URLs reached for scenarios 1, 2, 6)

## Feb 2026 Update — Manage Membership + Cancellation
- Added **Manage Membership** button on Dashboard (`dash-manage-membership`) that opens Stripe's hosted Customer Portal — active subscribers can update payment method, view invoices, cancel future renewals
- Cancellation configured as `cancel_at_period_end: true` — access continues through the paid billing period, then journal/notes flip to read-only while the account stays open
- "Cancels on [date]" pill (`dash-cancels-on`) shown on Dashboard when cancellation is pending
- Webhooks expanded: `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed` — auto-renewals extend `membership_expires_at` in sync with Stripe's `current_period_end`
- Journal POST/DELETE endpoints gated on `has_active_membership` → returns 402 read-only after expiry
- Pricing tagline updated on Landing + Pricing to explain cancellation semantics
- Terms → **Refund Policy** section added: 7-day full refund window from initial website purchase; non-refundable after; Etsy purchases follow Etsy listing terms
- Test suite: 10/10 pass (3 checkout regression + 7 cancellation covering monthly/3month/6month/annual)
- Production readiness checklist saved to `/app/memory/PRODUCTION_READINESS.md`

## Backlog (P1/P2)
- **P1**: Resend email delivery for drop notifications, receipts, password reset, code delivery
- **P1**: Push-to-GitHub (requires paid subscription plan)
- **P1**: Custom domain (club.JeanaMariePrivateChef.com) via Entri
- **P2**: PWA install prompt (flag ready)
- **P2**: Kid photo upload UI once opt-in flow is designed (backend + flag ready)
- **P2**: Journal PDF export UI polish (backend ready, flag off)
- **P2**: Etsy API automation
- **P3**: Live "Cook with Jeana Marie" video tier
- **P3**: Print-on-demand physical cookbook
