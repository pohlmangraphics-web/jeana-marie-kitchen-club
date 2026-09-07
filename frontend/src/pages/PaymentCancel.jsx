import Nav from "../components/Nav";
import { Link } from "react-router-dom";

export default function PaymentCancel() {
  return (
    <div className="min-h-screen">
      <Nav/>
      <div className="max-w-md mx-auto px-6 py-20 text-center">
        <h1 className="serif text-3xl font-black text-espresso">Payment canceled</h1>
        <p className="mt-3 text-muted2">No charge was made. Come back whenever you're ready.</p>
        <Link data-testid="cancel-home" to="/" className="btn-pill btn-primary mt-8 inline-flex">Back home</Link>
      </div>
    </div>
  );
}
