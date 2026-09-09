import Nav from "../components/Nav";
import Footer, { DISCLAIMER } from "../components/Footer";

export default function Privacy() {
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-3xl mx-auto px-6 py-16">
        <p className="script text-3xl text-terracotta">Your Family's Privacy</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Privacy Policy</h1>
        <p className="mt-2 text-muted2 text-sm">Last updated: February 2026</p>

        <div className="mt-8 rounded-2xl bg-honey/30 border-2 border-honey p-6 text-sm text-espresso leading-relaxed">
          <p className="font-bold mb-2">Nature of the Service</p>
          <p>{DISCLAIMER}</p>
        </div>

        <section className="mt-10 space-y-8 text-espresso leading-relaxed">
          <div>
            <h2 className="serif text-2xl font-bold">Who this policy applies to</h2>
            <p className="mt-2 text-muted2">This policy describes how Jeana Marie's Kitchen Club (the "Club") collects, uses, and protects information from the parent or guardian who purchases and manages a family membership, and from family members who use the account under that adult's supervision.</p>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Children Under 13 (COPPA)</h2>
            <p className="mt-2 text-muted2">The Club is designed to be a family experience directed by a parent or guardian. We do not knowingly collect personal information directly from children under the age of 13.</p>
            <ul className="mt-3 space-y-2 text-muted2 list-disc list-inside">
              <li><span className="font-semibold text-espresso">No independent child accounts.</span> A child under 13 does not create their own account, does not receive their own login, and does not receive their own email. All activity happens inside a parent-controlled family account.</li>
              <li><span className="font-semibold text-espresso">No email, no birthdate, no last name.</span> Sub-profiles for children capture only a first name or nickname and an avatar chosen by the parent.</li>
              <li><span className="font-semibold text-espresso">Photo uploads are opt-in and off by default.</span> Photo upload for any sub-profile associated with a child under 13 is disabled at the account level and cannot be enabled without an explicit parent action.</li>
              <li><span className="font-semibold text-espresso">Text notes only, by default.</span> Journal entries created inside a young child's profile default to text only.</li>
              <li><span className="font-semibold text-espresso">No behavioral advertising.</span> We do not sell, share, or serve advertising to any family member.</li>
              <li><span className="font-semibold text-espresso">Parent control.</span> The parent or guardian who owns the family account can view, edit, or delete any sub-profile and any content associated with it at any time from their account settings.</li>
            </ul>
            <p className="mt-3 text-muted2">If you believe a child under 13 has provided us with personal information without your consent, contact us and we will delete it promptly.</p>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">What we collect from the parent account holder</h2>
            <ul className="mt-3 space-y-2 text-muted2 list-disc list-inside">
              <li>Email address and family name at signup.</li>
              <li>A password hash (we never store your password in plain text — passwords are hashed with bcrypt).</li>
              <li>Payment information is handled by Stripe. The Club never sees, stores, or transmits your full card number.</li>
              <li>Optional information you choose to enter: journal notes, favorites, meal costing entries, uploaded photos (adult-account only, when the feature is enabled).</li>
              <li>Basic technical logs (IP address, browser type) used for security and rate limiting.</li>
            </ul>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">How we use information</h2>
            <ul className="mt-3 space-y-2 text-muted2 list-disc list-inside">
              <li>To provide the membership experience: publish recipes, save your journal, deliver printables.</li>
              <li>To process subscription payments and Etsy redeem codes.</li>
              <li>To email you about your membership (receipts, renewals, and — when enabled — the weekly recipe drop).</li>
              <li>To prevent abuse (rate limiting, security monitoring).</li>
            </ul>
            <p className="mt-3 text-muted2">We do not sell your data. We do not run behavioral ads.</p>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Who we share information with</h2>
            <ul className="mt-3 space-y-2 text-muted2 list-disc list-inside">
              <li><span className="font-semibold text-espresso">Stripe</span> — to process subscription payments.</li>
              <li><span className="font-semibold text-espresso">Object storage provider</span> — to host recipe photos, printables, and (opt-in) uploaded photos.</li>
              <li><span className="font-semibold text-espresso">Email provider</span> — when email delivery is enabled, to send account and drop-day emails.</li>
              <li>We disclose information if legally required (subpoena, court order, or to protect the safety of users).</li>
            </ul>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Your rights and choices</h2>
            <ul className="mt-3 space-y-2 text-muted2 list-disc list-inside">
              <li>Export your family's journal and content at any time from your account settings.</li>
              <li>Request deletion of your account — email us and we will delete your account and content within 30 days, except for records we are legally required to retain (e.g., billing records).</li>
              <li>Toggle photo uploads on or off per sub-profile.</li>
              <li>Cancel your membership at any time. Journal notes remain in read-only mode.</li>
            </ul>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Data retention</h2>
            <p className="mt-2 text-muted2">We keep your account and family content for as long as your membership is active or in read-only lapsed state. On explicit deletion request we remove all personal content within 30 days.</p>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Contact</h2>
            <p className="mt-2 text-muted2">Privacy questions, deletion requests, or COPPA concerns: contact the account holder area of your family account. For urgent matters, reach out via the Etsy shop or Chef Jeana Marie's website.</p>
          </div>

          <div>
            <h2 className="serif text-2xl font-bold">Changes to this policy</h2>
            <p className="mt-2 text-muted2">We may update this policy occasionally. Material changes will be announced in-app or by email to active members.</p>
          </div>
        </section>
      </div>
      <Footer/>
    </div>
  );
}
