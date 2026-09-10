import Nav from "../components/Nav";
import Footer, { DISCLAIMER } from "../components/Footer";

export default function Terms() {
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-3xl mx-auto px-6 py-16 prose prose-espresso">
        <p className="script text-3xl text-terracotta">The Fine Print</p>
        <h1 className="serif text-4xl sm:text-5xl font-black text-espresso">Terms of Use</h1>

        <div data-testid="terms-disclaimer" className="mt-8 rounded-2xl bg-honey/30 border-2 border-honey p-6 text-sm text-espresso leading-relaxed">
          <p className="font-bold mb-2">Nature of the Service</p>
          <p>{DISCLAIMER}</p>
        </div>

        <section className="mt-10 space-y-6 text-espresso">
          <div>
            <h2 className="serif text-2xl font-bold">Membership</h2>
            <p className="mt-2 text-muted2">Memberships are sold monthly, quarterly, semi-annually or annually via Stripe on this website, or as redeem codes purchased on Etsy. A single family membership covers one household — up to six family members per account.</p>
          </div>
          <div>
            <h2 className="serif text-2xl font-bold">Family Members Under 13</h2>
            <p className="mt-2 text-muted2">Younger family members do not create their own accounts. All activity happens under a parent-controlled family account. Photo uploads for family members under 13 are disabled by default and are opt-in per parent decision.</p>
          </div>
          <div>
            <h2 className="serif text-2xl font-bold">Content Ownership</h2>
            <p className="mt-2 text-muted2">All recipes, printable activities, family learning guides and worksheets are the intellectual property of Jeana Marie's Kitchen Club. Members may print and use them for personal, family use. Redistribution or resale is not permitted.</p>
          </div>
          <div>
            <h2 className="serif text-2xl font-bold">Cancellation</h2>
            <p className="mt-2 text-muted2">You can cancel future renewals at any time from <strong>My Kitchen → Manage Membership</strong>. Cancellation is not immediate — your membership remains active through the end of your current paid billing period (monthly, 3-month, 6-month or annual, whichever applies). Once that date passes, your journal, favorites and "We Made This" history remain available in <strong>read-only</strong> mode while your account stays open. You can reactivate any time to resume adding new entries and receiving weekly recipe drops.</p>
          </div>
          <div data-testid="terms-refund-policy">
            <h2 className="serif text-2xl font-bold">Refund Policy</h2>
            <p className="mt-2 text-muted2">Customers may request a full refund within <strong>7 calendar days</strong> of their initial website membership purchase by contacting support. After 7 days, payments are non-refundable and no partial refunds are provided, except where required by law. Cancelling stops future renewals, while access continues through the paid billing period. Accidental renewal charges reported within 7 days of the renewal date may be reviewed by support on a case-by-case basis. Memberships purchased through Etsy redeem codes are subject to the refund terms displayed on the corresponding Etsy listing, not this policy.</p>
          </div>
          <div>
            <h2 className="serif text-2xl font-bold">Not an Accredited Program</h2>
            <p className="mt-2 text-muted2">Kitchen Club activities are supplemental family enrichment. We do not issue grades, credits, transcripts or certificates. Parents and guardians retain full authority and responsibility for how these activities are used within their homeschool.</p>
          </div>
          <div>
            <h2 className="serif text-2xl font-bold">Contact</h2>
            <p className="mt-2 text-muted2">Questions? Reach out through your account settings or the contact link at the bottom of any page.</p>
          </div>
        </section>
      </div>
      <Footer/>
    </div>
  );
}
