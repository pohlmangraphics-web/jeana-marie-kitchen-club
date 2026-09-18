import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { WeeklyDropPreviewButton } from "./WeeklyDropPreviewButton";
import { api } from "../lib/api";
import { toast } from "sonner";

jest.mock("../lib/api", () => {
  const actual = jest.requireActual("../lib/api");
  return { api: { post: jest.fn() }, errorMessage: actual.errorMessage };
});
jest.mock("sonner", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const ADMIN = "admin@jeanamarie.club";
beforeEach(() => { jest.clearAllMocks(); window.confirm = jest.fn(() => true); });

test("confirmation shows admin email and success toast names provider", async () => {
  api.post.mockResolvedValueOnce({ data: { ok: true, provider: "resend", message_id: "m1", recipient: ADMIN, recipe: "Sunday Soup" } });
  render(<WeeklyDropPreviewButton adminEmail={ADMIN}/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  expect(window.confirm.mock.calls[0][0]).toContain(ADMIN);
  expect(window.confirm.mock.calls[0][0]).toMatch(/Nothing is sent to families/);
  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  expect(toast.success.mock.calls[0][0]).toBe(`Preview sent to ${ADMIN} via Resend — "Sunday Soup"`);
  expect(api.post).toHaveBeenCalledWith("/admin/email/weekly-drop/preview");
  expect(api.post.mock.calls[0].length).toBe(1); // no body → recipient can't be supplied
});

test("cancelling the confirmation sends nothing", () => {
  window.confirm = jest.fn(() => false);
  render(<WeeklyDropPreviewButton adminEmail={ADMIN}/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  expect(api.post).not.toHaveBeenCalled();
});

test("friendly failure with no raw objects", async () => {
  api.post.mockRejectedValueOnce({ response: { status: 429, data: { detail: "Too many attempts. Please wait and try again." } } });
  render(<WeeklyDropPreviewButton adminEmail={ADMIN}/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Too many attempts. Please wait and try again."));
  api.post.mockRejectedValueOnce({ response: { status: 502, data: { detail: [{ type: "x", loc: [], msg: "provider exploded", ctx: { key: "re_secret" } }] } } });
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(2));
  const msg = toast.error.mock.calls[1][0];
  expect(typeof msg).toBe("string");
  expect(msg).not.toContain("re_secret");
});

test("button disables while sending and cannot double-submit", async () => {
  let resolve;
  api.post.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
  render(<WeeklyDropPreviewButton adminEmail={ADMIN}/>);
  const btn = screen.getByTestId("weekly-drop-preview");
  fireEvent.click(btn);
  await waitFor(() => expect(btn).toBeDisabled());
  expect(btn).toHaveTextContent("Sending preview…");
  fireEvent.click(btn); fireEvent.click(btn);
  expect(api.post).toHaveBeenCalledTimes(1);
  resolve({ data: { ok: true, provider: "emergent", recipient: ADMIN, recipe: "X" } });
  await waitFor(() => expect(btn).not.toBeDisabled());
  expect(btn).toHaveTextContent("Send preview to me");
  expect(toast.success.mock.calls[0][0]).toContain("via Emergent");
});
