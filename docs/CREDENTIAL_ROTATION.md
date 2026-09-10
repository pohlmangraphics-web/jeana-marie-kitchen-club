# Credential Rotation — CRITICAL Before Production

**Context:** The initial development `.env` files may have entered Git history (via the previous `frontend/public/jeana-marie-kitchen-club.zip` backup that has now been removed) and were shared across preview iterations. Every secret listed below must be treated as **compromised** and **rotated** before flipping live traffic to the production domain.

This is not optional. Any of these values still in use in production would let an unauthorized party read/write your Mongo, forge JWT tokens, drain your Stripe account, or send email as your brand.

---

## Rotation Matrix

| # | Credential | Location | Where to rotate | Impact if leaked |
|---|---|---|---|---|
| 1 | `JWT_SECRET` | `backend/.env` | Emergent → Secrets tab → regenerate as 32+ random chars (`openssl rand -base64 48`) | Forged auth tokens → any account takeover, including admin |
| 2 | `MONGO_URL` (username + password portion) | `backend/.env` | Emergent → Database tab → "Rotate connection string" | Full DB read/write — every user, journal, payment record |
| 3 | `STRIPE_SECRET_KEY` (`sk_test_…` and later `sk_live_…`) | `backend/.env` | Stripe Dashboard → Developers → API keys → "Roll key" | Charge cards, refund arbitrarily, drain funds |
| 4 | `STRIPE_PUBLISHABLE_KEY` (`pk_test_…` / `pk_live_…`) | `backend/.env` | Auto-rotates with secret key roll | Low risk (publishable), but roll for consistency |
| 5 | `STRIPE_WEBHOOK_SECRET` (`whsec_…`) | `backend/.env` | Stripe Dashboard → Developers → Webhooks → your endpoint → "Roll signing secret" | Forged webhook events → fake membership grants |
| 6 | `RESEND_API_KEY` (`re_…`) | `backend/.env` | Resend Dashboard → API Keys → delete old key, create new | Send phishing emails as your domain |
| 7 | Emergent Object Storage credentials | Emergent-managed (via `storage.py`) | Emergent → Secrets tab → rotate `STORAGE_ACCESS_KEY` and `STORAGE_SECRET_KEY` if present | Read/overwrite user-uploaded photos, printable PDFs, logo |
| 8 | `EMERGENT_LLM_KEY` (if present) | Emergent-managed | Emergent → Profile → Manage Plan → Universal Key → "Rotate" | Drain your LLM credit balance |
| 9 | Admin password | Database (`users` collection) | See §Admin Rotation below | Full admin console access — publish/delete recipes, generate free codes, export user data |
| 10 | `admin@jeanamarie.club` email → real business email | Database (`users` collection) | See §Admin Rotation below | Reduces phishing surface (attacker who guessed old email now can't) |
| 11 | Demo family password (`DemoFamily123!`) | Database | Delete the demo account entirely after final preview testing | Login as a "real family" and see the app from a user's POV |
| 12 | Pre-seeded Etsy `codes` used during testing | Database (`codes` collection) | Delete test batches | Attacker with a leaked test code redeems a free membership |

---

## Rotation Order (do it in this exact order to avoid downtime)

### Step 1 — Rotate BEFORE any DNS switch or deploy
1. **`JWT_SECRET`** — regenerate in Emergent Secrets tab. Every existing token invalidates → all users must re-login. That's OK for a clean prod launch (no real users yet).
2. **`RESEND_API_KEY`** — create a new production key in Resend, paste it into Emergent Secrets, delete the old one from Resend. Password-reset emails and weekly drops will use the new key on next backend restart.
3. **Emergent Object Storage keys** (if you have separate `STORAGE_*` values in `.env`) — rotate via Emergent Secrets tab.
4. **`EMERGENT_LLM_KEY`** — rotate via Profile → Manage Plan → Universal Key.

### Step 2 — Stripe (happens automatically on KYC approval)
5. **`STRIPE_SECRET_KEY` + `STRIPE_PUBLISHABLE_KEY`** — do NOT manually rotate. Once Jeana claims the sandbox and completes KYC:
   - Stripe issues fresh live keys (`sk_live_…`, `pk_live_…`)
   - Emergent platform auto-swaps them into production `.env`
   - Old sandbox `sk_test_emergent` is left behind (harmless, sandbox-only)
6. **`STRIPE_WEBHOOK_SECRET`** — Emergent auto-registers the new production webhook and injects the new `whsec_…` secret. If you ever manually re-create the webhook, roll this too.

### Step 3 — Mongo (last, so the app stays up during rotation)
7. **`MONGO_URL`** — Emergent → Database tab → Rotate. This triggers a rolling restart of the backend pods with the new URI. Zero-downtime because Emergent stages the new pod before killing the old.

### Step 4 — Admin & Demo Cleanup (only AFTER final preview E2E test passes — you asked to defer this)
Run these ONE-OFF in the Emergent → Database → Query panel (or via a temporary admin endpoint):

```javascript
// Rename admin email to Jeana's real business email
db.users.updateOne(
  { role: "admin", email: "admin@jeanamarie.club" },
  { $set: { email: "jeana@jeanamarieprivatechef.com" } }
);

// Set a fresh strong password (generate one, then hash — do NOT store plain text)
// From backend shell:  python -c "import bcrypt; print(bcrypt.hashpw(b'YOUR_NEW_STRONG_PASSWORD', bcrypt.gensalt()).decode())"
db.users.updateOne(
  { role: "admin" },
  { $set: { password_hash: "<paste_bcrypt_hash_here>" } }
);

// Delete demo family + all TEST_* accounts + orphaned test payment transactions
db.users.deleteOne({ email: "demo@family.com" });
db.users.deleteMany({ email: { $regex: /^TEST_/ } });
db.payment_transactions.deleteMany({ status: "initiated", created_at: { $lt: new Date(Date.now() - 24*60*60*1000) } });

// Delete any test-batch redeem codes (they'll have `note` containing "test")
db.codes.deleteMany({ note: { $regex: /test/i } });

// Remove any seed profiles under demo family (cascade)
db.profiles.deleteMany({ user_id: { $exists: false } });  // orphans
```

**Do NOT run Step 4 until you've completed final preview testing** — you'll need the demo account and test users to verify the six checkout scenarios and cancellation flows one last time against the production-domain preview.

### Step 5 — Remove the local test-credentials file
```bash
# After Step 4, remove this file so it can't leak via a future zip export
rm /app/memory/test_credentials.md
```

---

## Post-Rotation Verification

After all rotations, verify each:

- [ ] Backend logs show `Object storage initialized` on restart (Mongo + storage keys valid)
- [ ] `curl -X POST https://club.jeanamarieprivatechef.com/api/auth/login` with rotated admin creds returns a valid JWT
- [ ] Trigger a password reset — email arrives from `hello@club.jeanamarieprivatechef.com` (proves Resend rotation worked)
- [ ] Complete a real $9.99 monthly checkout with a Stripe test card in the LIVE Stripe test mode ($ zero-dollar sandbox) — verify webhook fires and `membership_expires_at` is set correctly (proves Stripe rotation worked)
- [ ] Click Manage Membership → Stripe Portal opens (proves customer + subscription plumbing survived the rotation)
- [ ] Old `admin@jeanamarie.club` / `JeanaAdmin2026!` login returns 401 (proves rotation actually took)
- [ ] `db.users.find({email: "demo@family.com"}).count()` returns 0 (proves demo cleanup succeeded)

---

## Why Every One of These Must Be Rotated

The `frontend/public/jeana-marie-kitchen-club.zip` that was previously in the repo/preview may have contained (or could have been inspected to contain) references to the `.env` values via the Emergent snapshot process. Even if the specific bytes were not exposed publicly, any snapshot of the preview environment that ever left the Emergent perimeter is untrusted for production use.

**Cost of rotating: 5-10 minutes total, zero downtime.**
**Cost of not rotating: potential total account compromise once the domain goes live and is indexed.**

Do it.
