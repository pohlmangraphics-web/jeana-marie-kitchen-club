import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "./lib/auth";
import { FlagsProvider } from "./lib/flags";
import Landing from "./pages/Landing";
import Auth from "./pages/Auth";
import Redeem from "./pages/Redeem";
import Dashboard from "./pages/Dashboard";
import Book from "./pages/Book";
import Recipe from "./pages/Recipe";
import Journal from "./pages/Journal";
import Printables from "./pages/Printables";
import MealCosting from "./pages/MealCosting";
import Admin from "./pages/Admin";
import PaymentSuccess from "./pages/PaymentSuccess";
import PaymentCancel from "./pages/PaymentCancel";
import ForgotPassword from "./pages/ForgotPassword";
import ResetPassword from "./pages/ResetPassword";
import FAQ from "./pages/FAQ";
import Terms from "./pages/Terms";
import Privacy from "./pages/Privacy";
import GiftPage from "./pages/Gift";
import Library from "./pages/Library";
import Unsubscribe from "./pages/Unsubscribe";
import Pricing from "./pages/Pricing";

function Protected({ children, adminOnly }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-10">Loading…</div>;
  if (!user) return <Navigate to="/auth" replace/>;
  if (adminOnly && user.role !== "admin") return <Navigate to="/app" replace/>;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <FlagsProvider>
        <BrowserRouter>
          <Toaster position="top-center" richColors/>
          <Routes>
            <Route path="/" element={<Landing/>}/>
            <Route path="/auth" element={<Auth/>}/>
            <Route path="/redeem" element={<Redeem/>}/>
            <Route path="/forgot" element={<ForgotPassword/>}/>
            <Route path="/reset" element={<ResetPassword/>}/>
            <Route path="/faq" element={<FAQ/>}/>
            <Route path="/terms" element={<Terms/>}/>
            <Route path="/privacy" element={<Privacy/>}/>
            <Route path="/gift" element={<GiftPage/>}/>
            <Route path="/unsubscribe" element={<Unsubscribe/>}/>
            <Route path="/pricing" element={<Pricing/>}/>
            <Route path="/payment/success" element={<PaymentSuccess/>}/>
            <Route path="/payment/cancel" element={<PaymentCancel/>}/>
            <Route path="/app" element={<Protected><Dashboard/></Protected>}/>
            <Route path="/app/book/:tier" element={<Protected><Book/></Protected>}/>
            <Route path="/app/library" element={<Protected><Library/></Protected>}/>
            <Route path="/app/recipe/:id" element={<Protected><Recipe/></Protected>}/>
            <Route path="/app/journal" element={<Protected><Journal/></Protected>}/>
            <Route path="/app/printables" element={<Protected><Printables/></Protected>}/>
            <Route path="/app/meal-costing" element={<Protected><MealCosting/></Protected>}/>
            <Route path="/admin" element={<Protected adminOnly><Admin/></Protected>}/>
          </Routes>
        </BrowserRouter>
      </FlagsProvider>
    </AuthProvider>
  );
}
export default App;
