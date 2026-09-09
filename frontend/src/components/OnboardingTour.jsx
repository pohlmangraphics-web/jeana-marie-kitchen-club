import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { X, ChevronRight, ChevronLeft, Sparkles } from "lucide-react";

const STEPS = [
  {
    title: "Welcome to your kitchen",
    body: "This is your family's home base. Every profile you add keeps its own favorites, notes and 'We Made This' history.",
    cta: "Next",
  },
  {
    title: "Our Recipe Books",
    body: "You have access to all four books — Little Chefs, Junior Cooks, Teen Kitchen, and Mom & Dad. Open any one anytime, no profile needed.",
    cta: "Next",
  },
  {
    title: "Every week, something new",
    body: "Jeana Marie publishes new recipes and printable activities every week. Look for 'Jeana's Pick of the Week' on this page and download printables from the Printables Library.",
    cta: "Let's cook!",
  },
];

const LS_KEY = "jmk_onboarded";

export default function OnboardingTour({ forceOpen = false, onClose }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (forceOpen) { setOpen(true); setStep(0); return; }
    if (!localStorage.getItem(LS_KEY)) {
      const t = setTimeout(() => setOpen(true), 600);
      return () => clearTimeout(t);
    }
  }, [forceOpen]);

  const close = (completed) => {
    localStorage.setItem(LS_KEY, completed ? "done" : "skipped");
    setOpen(false);
    setStep(0);
    onClose && onClose();
  };

  if (!open) return null;
  const s = STEPS[step];
  const last = step === STEPS.length - 1;

  return (
    <div data-testid="onboarding-tour" className="fixed inset-0 z-50 bg-espresso/70 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-cream rounded-3xl max-w-lg w-full p-8 relative shadow-2xl">
        <button data-testid="onboarding-skip" onClick={() => close(false)}
          className="absolute top-4 right-4 text-muted2 hover:text-espresso flex items-center gap-1 text-xs">
          Skip <X className="w-3 h-3"/>
        </button>
        <div className="flex items-center gap-2 text-xs uppercase tracking-widest text-sage font-bold">
          <Sparkles className="w-3 h-3"/> Step {step + 1} of {STEPS.length}
        </div>
        <h3 className="mt-3 serif text-3xl font-black text-espresso">{s.title}</h3>
        <p className="mt-4 text-muted2 leading-relaxed">{s.body}</p>

        <div className="mt-6 flex gap-1">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1.5 flex-1 rounded-full ${i <= step ? "bg-terracotta" : "bg-terracotta/20"}`}/>
          ))}
        </div>

        <div className="mt-6 flex justify-between items-center">
          <button data-testid="onboarding-back" onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            className="btn-pill btn-outline !py-2 !px-4 text-sm disabled:opacity-40 disabled:cursor-not-allowed">
            <ChevronLeft className="w-4 h-4"/> Back
          </button>
          <button data-testid="onboarding-next" onClick={() => last ? close(true) : setStep(step + 1)}
            className="btn-pill btn-primary !py-2 !px-5 text-sm">
            {s.cta} {!last && <ChevronRight className="w-4 h-4"/>}
          </button>
        </div>
      </div>
    </div>
  );
}

export function replayTour() {
  localStorage.removeItem(LS_KEY);
}
