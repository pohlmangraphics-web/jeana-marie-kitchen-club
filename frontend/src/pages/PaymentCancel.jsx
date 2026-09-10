import Nav from "../components/Nav";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";

export default function PaymentCancel() {
  const { user } = useAuth();
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <h1 className="serif text-3xl font-black text-espresso">Payment canceled</h1>
        <p className="mt-3 text-muted2">No charge was made. Come back whenever you're ready.</p>
        {user ? (
          <div className="mt-8 flex flex-wrap gap-3 justify-center">
            <Link data-testid="cancel-retry" to="/pricing" className="btn-pill btn-primary">Choose a plan</Link>
            <Link data-testid="cancel-dashboard" to="/app" className="btn-pill btn-outline">Back to My Kitchen</Link>
          </div>
        ) : (
          <Link data-testid="cancel-home" to="/" className="btn-pill btn-primary mt-8 inline-flex">Back home</Link>
        )}
      </div>
    </div>
  );
}
