# Jeana Marie's Kitchen Club — Production Readiness Checklist
**As of Feb 2026 — before first live deploy**

This document is the single source of truth for what must be verified BEFORE clicking "Deploy". Preview + database will be preserved throughout. Nothing here changes production automatically.

---

## 1. Environment Variables

The following `.env` values MUST exist in the deployment secrets tab. Preview values are already wired; production values will be injected by the platform on deploy.

### Backend (`/app/backend/.env`)
| Key | Preview value | Production expectation |
|---|---|---|
| `MONGO_URL` | Emergent-managed cluster | **Rotated** managed cluster URI, injected by platform |
| `DB_NAME` | `test_database` | **Change** to `kitchen_club_prod` on first deploy |
| `JWT_SECRET` | 32-char random from preview | **Rotate** — generate a fresh 32+ char secret in Secrets tab |
| `STRIPE_SECRET_KEY` | `sk_test_…` (sandbox) | **Live `sk_live_…`** — auto-swapped by platform after Stripe KYC |
| `STRIPE_PUBLISHABLE_KEY` | `pk_test_…` | Auto-swap to live |
| `STRIPE_WEBHOOK_SECRET` | preview-generated | Auto-swap to live webhook secret |
| `RESEND_API_KEY` | `re_…` (dev) | **Rotate** to production API key from Resend dashboard |
| `EMAIL_FROM` | `noreply@localhost` | `hello@club.jeanamarieprivatechef.com` (after Resend domain verified) |
| `CORS_ORIGINS` | `*` | Set to `https://club.jeanamarieprivatechef.com,https://www.club.jeanamarieprivatechef.com` |

### Frontend (`/app/frontend/.env`)
| Key | Preview value | Production expectation |
|---|---|---|
| `REACT_APP_BACKEND_URL` | preview URL | Auto-set to `https://club.jeanamarieprivatechef.com` after custom domain link |

**Action:** Before deploy, open Emergent's Secrets tab and rotate `JWT_SECRET` and `RESEND_API_KEY`. Do NOT overwrite `STRIPE_*` — those swap automatically on Stripe KYC approval.

---

## 2. Rotated Credentials Checklist

- [ ] `JWT_SECRET` rotated from preview value (invalidates all existing tokens — users must re-login, which is desired for a clean prod launch)
- [ ] `RESEND_API_KEY` rotated to production key (dev key will 403 on production domain sends)
- [ ] Admin password rotated from `JeanaAdmin2026!` to a strong unique password (see §7 below)
- [ ] Demo family account `demo@family.com` removed (see §7)
- [ ] All `TEST_*` seed users purged (previous testing agent confirmed 29 already cleaned, run one final sweep)
- [ ] Any hardcoded API keys in the codebase (`grep -rn "sk_live\|sk_test\|re_" /app/backend /app/frontend/src`) return zero results

---

## 3. Stripe Ownership & Live Webhook

### Claim the sandbox
The current Stripe test integration is a **claimable sandbox** — Jeana can claim it in one click and it becomes her real Stripe account (no data loss, no code changes).

- [ ] Jeana visits the `onboarding_url` from her Stripe email OR from the Emergent → Payments tab
- [ ] Completes Stripe KYC (business info, bank account, tax ID)
- [ ] Once approved, Stripe auto-issues `sk_live_…` / `pk_live_…` keys
- [ ] Emergent platform triggers an automatic redeployment with live keys — **no manual env edit needed**

### Live webhook endpoint
- [ ] After live keys are live, the Emergent platform automatically registers the production webhook at `https://club.jeanamarieprivatechef.com/api/stripe/webhook`
- [ ] Confirm in Stripe Dashboard → Developers → Webhooks that the endpoint is listed and receiving events
- [ ] Ensure the following events are subscribed:
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
- [ ] Send a test event from Stripe Dashboard → verify 200 OK and no signature errors in backend logs

### Tax mode
Selected tax mode: **`full` (Stripe Managed Payments — Stripe handles tax calculation, collection, filing and remittance).** Applies in ~80 countries. Additional fee: +3.5% per transaction.

Available alternatives (switchable by asking the agent later):
- `calc_only` — Stripe calculates tax at checkout, you file returns yourself (+0.5% per transaction)
- `diy` — Stripe just processes payment, no tax help (cheapest, most manual work)

---

## 4. Resend Domain Verification

- [ ] In Resend dashboard, add domain `club.jeanamarieprivatechef.com` (or the root `jeanamarieprivatechef.com` if Jeana wants a shared sender)
- [ ] Add the DNS records Resend provides (typically 3 records: SPF `TXT`, DKIM `TXT` on `resend._domainkey`, DMARC `TXT` on `_dmarc`) — see §6 for exact GoDaddy instructions
- [ ] Wait for domain to show "Verified" in Resend (usually 5-60 min)
- [ ] Set `EMAIL_FROM=hello@club.jeanamarieprivatechef.com` in production `.env`
- [ ] Send a test password-reset email to a personal inbox — verify it lands, no spam flag, "From" reads correctly

---

## 5. Database Backup

- [ ] Emergent's managed MongoDB has automatic daily snapshots enabled by default. Confirm in Emergent → Database tab.
- [ ] Before flipping live, take an on-demand snapshot from the Database tab labeled `pre-launch-YYYY-MM-DD` for a clean rollback point.
- [ ] Document the restore process: Database tab → Snapshots → Select → Restore. Time to restore ~2-5 min.
- [ ] After the first week of production, verify at least one automated snapshot has been created.

---

## 6. Custom Domain — GoDaddy DNS (Manual)

**Target domain:** `club.jeanamarieprivatechef.com`
**DNS provider:** GoDaddy
**Constraint:** Do NOT change root `@` or `www` records — those point to Jeana's existing site.

### Step 1 — Add the CNAME
In GoDaddy → My Products → Domains → `jeanamarieprivatechef.com` → DNS → Manage Zones → Add a new record.

| Field | Value |
|---|---|
| **Type** | `CNAME` |
| **Name / Host** | `club` |
| **Value / Target** | `custom.emergent.host` *(exact CNAME target will be shown in Emergent → Deploy → Custom Domain after you initiate domain linking — copy verbatim from that dialog)* |
| **TTL** | `1 hour` (default) |

> ⚠️ Do NOT touch:
> - `A` record for `@` (root) — leave alone
> - `CNAME` for `www` — leave alone
> - `MX` records — leave alone
> - Any existing `TXT` records — leave alone (Resend records go IN ADDITION, not replacing)

### Step 2 — Resend DNS records (add to same zone, do not remove existing)
Resend will show 3 records after you add the domain. Add each as a new record:

| Type | Name / Host | Value | Notes |
|---|---|---|---|
| `TXT` | `@` (root) OR `club` | `v=spf1 include:_spf.resend.com ~all` | If root already has SPF, merge include; do NOT add a duplicate root SPF |
| `TXT` | `resend._domainkey` | (long DKIM key from Resend UI) | Copy verbatim |
| `TXT` | `_dmarc` | `v=DMARC1; p=none; rua=mailto:postmaster@jeanamarieprivatechef.com` | Only add if not already present |

### Step 3 — Verify + SSL
- [ ] After entering the CNAME, DNS typically propagates in 15 min – 4 hours
- [ ] In Emergent → Deploy → Custom Domain, click "Verify DNS" — waits for propagation
- [ ] Once verified, Emergent auto-provisions Let's Encrypt SSL (5–10 min)
- [ ] Test: `https://club.jeanamarieprivatechef.com` loads with a valid green-lock certificate

---

## 7. Remove Development Credentials

- [ ] Delete `demo@family.com` user from Mongo (`db.users.deleteOne({email:"demo@family.com"})`)
- [ ] Delete all `TEST_*@example.com` users (`db.users.deleteMany({email:/^TEST_/})`)
- [ ] Change admin email from `admin@jeanamarie.club` to Jeana's real business email (`db.users.updateOne({role:"admin"}, {$set:{email:"jeana@…"}})`)
- [ ] Rotate admin password: run `python /app/backend/seed.py --rotate-admin-password` (or manually update the `password_hash` via a bcrypt hash of a strong new password)
- [ ] Delete `/app/memory/test_credentials.md` after prod credentials are set (or move to a private note outside the repo)
- [ ] Purge `payment_transactions` collection of `status="initiated"` rows older than 24h from testing (they'll never complete)
- [ ] Purge any test `codes` entries (`db.codes.deleteMany({note:{$regex:/test/i}})`)

---

## 8. GitHub Sync

**Repo:** https://github.com/pohlmangraphics-web/jeana-marie-kitchen-club
**Branch:** `emergent-launch-prep` (NOT `main`)

**Prerequisite:** Save-to-GitHub requires a **paid Emergent plan** (Standard or above). Free plan can only view/copy code in VS Code editor. Upgrade first if needed.

**Steps:**
1. Home tab → **GitHub** → OAuth-connect the `pohlmangraphics-web` account
2. Save button in chat → **Save to GitHub**
3. Select account: `pohlmangraphics-web`
4. Select repo: `jeana-marie-kitchen-club`
5. Create new branch: `emergent-launch-prep` (do NOT push to `main`)
6. Click **Save to GitHub**

**What's excluded automatically (safe):**
- `backend/.env` (Mongo URL, JWT secret, Stripe keys, Resend key)
- `frontend/.env` (backend URL)
- `node_modules/`, `__pycache__/`, `.venv/`
- Emergent scans for exposed secrets and BLOCKS the push if any are detected

**After push, open a PR from `emergent-launch-prep` → `main` for review.**

---

## 9. Membership Cancellation — Verified

New in this snapshot:
- **Manage Membership button** on Dashboard opens Stripe's hosted Customer Portal (data-testid: `dash-manage-membership`)
- Portal allows: update payment method, view invoices, cancel future renewals
- Cancellation is `cancel_at_period_end: true` — access continues through the paid billing period
- "Cancels on [date]" pill on Dashboard when applicable (data-testid: `dash-cancels-on`)
- Webhooks handled: `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_succeeded`, `invoice.payment_failed`
- After period end, `has_active_membership` flips false → journal endpoints return 402, UI shows read-only banner

**Test results (`test_cancellation.py`, all 7 tests pass):**
- `test_portal_requires_stripe_customer` — PASS (400 when no customer_id)
- `test_checkout_url_for_all_four_tiers` — PASS (monthly / 3month / 6month / annual all produce Stripe URLs)
- `test_cancel_at_period_end_persists_for_each_tier` — PASS (4 tiers × cancel flag persists)
- `test_subscription_deleted_leaves_paid_period_intact` — PASS (4 tiers × membership_expires_at unchanged after delete)
- `test_cancelled_member_expires_after_period_end` — PASS (4 tiers × journal writes blocked with 402 after expiry)
- `test_subscription_updated_extends_membership_on_renewal` — PASS (4 tiers × auto-renewal extends access)
- `test_reactivation_after_cancel_via_undo` — PASS (undo cancel clears the flag)

**Combined test suite:** 10/10 pass (3 checkout regression + 7 cancellation).

---

## 10. Terms & Policy — Refund Language

`Terms.jsx` now includes an explicit **Refund Policy** section with:
- 7-day full refund window from initial website purchase
- Non-refundable after 7 days (except where required by law)
- Cancelling stops future renewals; access continues through paid period
- Accidental renewals reviewed case-by-case within 7 days
- Etsy purchases governed by Etsy listing terms

---

## 11. Copy Updates

Old: *"Cancel anytime. Journal & notes stay saved forever."*
New (both Landing pricing section and Pricing page): *"Cancel future renewals anytime. Your membership remains active through the end of your paid billing period, and your journal and notes remain available in read-only mode while your account stays open."*

---

## 12. Pre-Deploy Smoke Test Checklist

Before clicking Deploy, run this final verification on the preview:

- [ ] `/` loads, no console errors
- [ ] Sign in with rotated admin credentials succeeds
- [ ] Admin panel accessible; Recipes / Printables / Codes / Families / Analytics / Flags / Branding / Export tabs all render
- [ ] Landing `hero-cta-join` → `/pricing`
- [ ] Signed-in unpaid → `dash-upgrade` → `/pricing` → Stripe checkout URL
- [ ] Active subscriber → `dash-manage-membership` → Stripe Portal URL
- [ ] Password reset email arrives from correct domain
- [ ] Weekly recipe email broadcast dry-run to admin only
- [ ] 10/10 backend tests pass (`pytest tests/test_checkout_regression.py tests/test_cancellation.py`)

---

**When every box above is checked, you're launch-ready. Deploy from Emergent → Deploy → Production.**
