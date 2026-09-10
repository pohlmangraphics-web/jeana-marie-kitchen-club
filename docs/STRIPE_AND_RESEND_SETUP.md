# Stripe Claim & Resend DNS — Step-by-Step

Follow these two setups in parallel. Neither touches production; both prepare the credentials the platform will auto-inject on deploy.

---

## PART 1 — Claim the Stripe Sandbox (~10 minutes + Stripe review time)

The Kitchen Club is currently running on an Emergent-provided **claimable sandbox**. When Jeana claims it, the sandbox becomes her real Stripe account with:
- Zero data migration (existing test transactions and pricing catalog stay intact)
- No code changes on our side
- Automatic swap from `sk_test_…` to `sk_live_…` upon KYC approval

### Step 1 — Get the onboarding link
Two ways to find it:

**Option A — Emergent Payments tab (preferred)**
1. In Emergent chat, click **Republish** or open the **Payments** tab in the sidebar
2. Look for the message "Claim your Stripe account" with a link
3. Click through to Stripe's onboarding page

**Option B — Stripe email**
The onboarding link was also sent to the email address on the Emergent account when the sandbox was provisioned. Search inbox for `noreply@stripe.com` → "Claim your Stripe account".

### Step 2 — Complete Stripe onboarding
Jeana will need to provide:
- **Business type**: Sole proprietor / LLC / other — whichever matches her business filing
- **Legal business name**: Must match tax records
- **DBA (Doing Business As)**: `Jeana Marie's Kitchen Club`
- **EIN or SSN**: for US 1099 reporting
- **Business address**: physical mailing address (P.O. Box not accepted)
- **Bank account**: routing + account number for payout deposits (US ACH)
- **Personal verification**: driver's license or passport photo, date of birth, last-4 SSN
- **Support details**: business phone (can be Google Voice), support email → `support@club.jeanamarieprivatechef.com` (create this alias in Resend later)
- **Website URL**: `https://club.jeanamarieprivatechef.com`
- **Products/services description**: *"Digital homeschool cooking membership. Weekly recipes and printable learning worksheets delivered to families via web app. Recurring monthly, quarterly, semi-annual, or annual subscriptions."*
- **Tax code**: `txcd_10103001` (SaaS) — already set on your products

### Step 3 — Wait for Stripe review
- Typical review: **1-2 business days** for US-based sole proprietors
- Stripe may email requesting additional documents (business license, tax returns) — respond promptly
- While waiting, sandbox mode remains fully functional for preview testing

### Step 4 — Upon approval
- Stripe issues live keys automatically
- **Emergent detects the approval and auto-redeploys with live keys** — no manual env edits, no re-code
- You'll receive an Emergent notification: "Stripe live keys activated — production checkout is now real"

### Step 5 — Verify live webhook
After approval, verify in Stripe Dashboard → Developers → Webhooks:
- [ ] Endpoint `https://club.jeanamarieprivatechef.com/api/stripe/webhook` is listed
- [ ] Status: `Enabled`
- [ ] Events subscribed (send yourself a test event from the dashboard for each):
  - `checkout.session.completed`
  - `customer.subscription.created`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
  - `invoice.payment_succeeded`
  - `invoice.payment_failed`
- [ ] Click "Send test webhook" for `checkout.session.completed` → verify 200 OK in the Recent deliveries panel

### Tax mode confirmation
Your app is configured for **Stripe Managed Payments (full tax mode)** — Stripe handles tax calculation, collection, filing and remittance in ~80 countries at +3.5% per transaction. This is the recommended default for a digital subscription business.

Available alternatives (ask the agent to switch later if needed):
- **`calc_only`**: Stripe calculates tax at checkout only, you file returns yourself (+0.5% per transaction)
- **`diy`**: Stripe just processes payment, no tax help (cheapest but most work — you'd need to register for sales tax in every US state where you have nexus)

### Fee summary for planning
- Stripe processing: **2.9% + $0.30** per successful US card transaction
- Managed Payments (SMP) tax handling: **+3.5%** per transaction
- Effective take rate on a $9.99 monthly: ~$9.99 → Stripe keeps ~$0.94 → Jeana gets ~$9.05
- On annual $89.99: Stripe keeps ~$5.94 → Jeana gets ~$84.05

---

## PART 2 — Resend Domain Verification for `jeanamarieprivatechef.com` (~15 minutes DNS + 5-60 min propagation)

Goal: Send transactional email from `hello@club.jeanamarieprivatechef.com` (password resets, weekly recipe drops, receipt confirmations, gift certificate PDFs) with SPF/DKIM/DMARC that won't land in spam.

### Step 1 — Add domain in Resend
1. Log in to https://resend.com/domains
2. Click **Add Domain**
3. Enter **`jeanamarieprivatechef.com`** (the ROOT domain, not `club.` — this way any subdomain sender works)
4. Select **US** (or **EU** if Jeana is EU-based) for the sending region
5. Click **Add** — Resend now shows you 3 DNS records to add

### Step 2 — DNS records to add in GoDaddy

**⚠️ RULES:**
- Do NOT touch `A` records for `@` (root) — Jeana's existing website depends on it
- Do NOT touch `CNAME` for `www` — same reason
- Do NOT touch existing `MX` records (email delivery to root domain)
- **ADD new records** — never replace existing ones unless explicitly noted

In GoDaddy → My Products → Domains → `jeanamarieprivatechef.com` → DNS → Manage Zones → **Add** button for each of the following:

#### Record 1 — SPF (Sender Policy Framework)
Check if a `TXT` record already exists at `@` starting with `v=spf1`:
- **If NO existing SPF**: Add a new record.
- **If YES existing SPF**: MERGE — do NOT add a duplicate SPF (only one SPF allowed per domain). Edit the existing record and append `include:_spf.resend.com` before the `~all` or `-all` at the end.

| Field | Value |
|---|---|
| Type | `TXT` |
| Name / Host | `@` |
| Value | `v=spf1 include:_spf.resend.com ~all` *(if no existing SPF)* OR merged version |
| TTL | `1 hour` |

#### Record 2 — DKIM (DomainKeys Identified Mail)
Resend will show you a unique DKIM key. It looks like `p=MIGfMA0GCSq...` (a very long string). Copy it VERBATIM from Resend's UI.

| Field | Value |
|---|---|
| Type | `TXT` |
| Name / Host | `resend._domainkey` |
| Value | The full `k=rsa; p=MIGf...` string from Resend (do not add quotes; GoDaddy handles quoting) |
| TTL | `1 hour` |

#### Record 3 — DMARC (Domain-based Message Authentication)
Check if `_dmarc` already exists:
- **If NO**: Add the record below.
- **If YES**: leave the existing DMARC alone — do NOT overwrite. Resend will still verify.

| Field | Value |
|---|---|
| Type | `TXT` |
| Name / Host | `_dmarc` |
| Value | `v=DMARC1; p=none; rua=mailto:postmaster@jeanamarieprivatechef.com` |
| TTL | `1 hour` |

### Step 3 — Verify in Resend
1. Back in Resend → Domains → your domain → click **Verify DNS Records**
2. All three records must show ✅ (usually 5-60 min after GoDaddy save)
3. If any record shows ❌, click "Show diagnostic" — usually it's a typo or GoDaddy stripping the trailing dot; re-check the value character-for-character
4. Once all three ✅, the domain status flips to **Verified**

### Step 4 — Update backend `.env`
After verification:

```bash
# In Emergent → Secrets tab, add or update:
EMAIL_FROM=hello@club.jeanamarieprivatechef.com
RESEND_API_KEY=<your production Resend API key — see Credential Rotation doc>
```

Restart backend (`sudo supervisorctl restart backend`) and send a test password-reset email. Verify:
- Inbox arrival (not spam)
- `From:` reads `Jeana Marie's Kitchen Club <hello@club.jeanamarieprivatechef.com>`
- No SPF/DKIM warnings in Gmail's "show original" panel

### Step 5 — Optional: SES-style tracking
Resend has built-in open/click tracking. In Resend dashboard → your domain → Settings:
- **Open tracking**: Consider LEAVING OFF for password reset emails (adds a tracking pixel; some spam filters dislike)
- **Click tracking**: Can leave ON for weekly recipe drops (helps you measure engagement)

### Step 6 — Create the `hello@` sender alias (optional)
Resend uses the API key for authentication — there's no separate mailbox needed. But if Jeana wants to actually receive replies to `hello@club.jeanamarieprivatechef.com`, she'll need to configure email forwarding. Options:
- **GoDaddy Forwarding**: In DNS panel, add MX records for `club` subdomain pointing to a forwarding service. Simplest: enable GoDaddy's built-in email forwarding to Jeana's personal Gmail. Cost: free with domain registration.
- **Google Workspace**: If she wants a proper `hello@` mailbox with the interface, ~$6/month.

### Common Gotchas

| Problem | Fix |
|---|---|
| DKIM value gets split across lines in GoDaddy | Paste it as a single continuous string — GoDaddy will handle the underlying TXT chunking |
| SPF verification fails after adding | Check if Jeana had a Google Workspace SPF already (`include:_spf.google.com`) — you MUST merge, not replace: `v=spf1 include:_spf.google.com include:_spf.resend.com ~all` |
| Emails still land in spam after verification | Add DMARC monitoring (`p=quarantine` after 2 weeks of clean sends) and warm up the domain — send 20-50 emails/day for the first week |
| `EMAIL_FROM=noreply@...` looks impersonal | We use `hello@…` because Resend's playbook favors reply-able addresses for deliverability |

---

## Cross-check — Both Systems Wired?

Only proceed to production deploy when ALL of these are checked:

- [ ] Stripe status: **Live keys active** (visible in Emergent Payments tab)
- [ ] Stripe webhook: 6/6 event types receiving 200 OK on test deliveries
- [ ] Resend domain: **Verified** (green checks on SPF + DKIM + DMARC)
- [ ] Backend `.env` has: `EMAIL_FROM=hello@club.jeanamarieprivatechef.com`
- [ ] Test password-reset email lands in a personal Gmail inbox, not spam
- [ ] Preview `/pricing` → Stripe checkout URL now returns a `checkout.stripe.com/pay/cs_live_…` (with `_live_` not `_test_`) after live-key swap
