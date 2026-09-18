import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { WeeklyDropPreviewButton } from "./WeeklyDropPreviewButton";
import { api } from "../lib/api";
import { toast } from "sonner";

jest.mock("../lib/api", () => {
  const actual = jest.requireActual("../lib/api");
  return { api: { post: jest.fn(), get: jest.fn() }, errorMessage: actual.errorMessage };
});
jest.mock("sonner", () => ({ toast: { success: jest.fn(), error: jest.fn() } }));

const PREVIEW = "pohlmangraphics@gmail.com";
const recipient = (r = PREVIEW) => api.get.mockResolvedValueOnce({ data: { recipient: r } });
beforeEach(() => { jest.clearAllMocks(); window.confirm = jest.fn(() => true); });

test("confirmation shows the server-resolved recipient, not a login email", async () => {
  recipient();
  api.post.mockResolvedValueOnce({ data: { ok: true, provider: "resend", message_id: "m1", recipient: PREVIEW, recipe: "Sunday Soup" } });
  render(<WeeklyDropPreviewButton/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(window.confirm).toHaveBeenCalled());
  expect(api.get).toHaveBeenCalledWith("/admin/email/weekly-drop/preview-recipient");
  expect(window.confirm.mock.calls[0][0]).toContain(PREVIEW);
  expect(window.confirm.mock.calls[0][0]).not.toContain("admin@jeanamarie.club");
  expect(window.confirm.mock.calls[0][0]).toMatch(/Nothing is sent to families/);
  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  expect(toast.success.mock.calls[0][0]).toBe(`Preview sent to ${PREVIEW} via Resend — "Sunday Soup"`);
  expect(api.post).toHaveBeenCalledWith("/admin/email/weekly-drop/preview");
  expect(api.post.mock.calls[0].length).toBe(1); // no body → recipient can't be supplied
});

test("fallback recipient (admin) is shown when server resolves to it", async () => {
  recipient("admin@jeanamarie.club");
  api.post.mockResolvedValueOnce({ data: { ok: true, provider: "emergent", recipient: "admin@jeanamarie.club", recipe: "X" } });
  render(<WeeklyDropPreviewButton/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.success).toHaveBeenCalled());
  expect(window.confirm.mock.calls[0][0]).toContain("admin@jeanamarie.club");
  expect(toast.success.mock.calls[0][0]).toContain("via Emergent");
});

test("cancelling the confirmation sends nothing", async () => {
  recipient(); window.confirm = jest.fn(() => false);
  render(<WeeklyDropPreviewButton/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(window.confirm).toHaveBeenCalled());
  expect(api.post).not.toHaveBeenCalled();
  await waitFor(() => expect(screen.getByTestId("weekly-drop-preview")).not.toBeDisabled());
});

test("friendly failure with no raw objects", async () => {
  recipient();
  api.post.mockRejectedValueOnce({ response: { status: 429, data: { detail: "Too many attempts. Please wait and try again." } } });
  render(<WeeklyDropPreviewButton/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.error).toHaveBeenCalledWith("Too many attempts. Please wait and try again."));
  recipient();
  api.post.mockRejectedValueOnce({ response: { status: 502, data: { detail: [{ type: "x", loc: [], msg: "provider exploded", ctx: { key: "re_secret" } }] } } });
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(2));
  const msg = toast.error.mock.calls[1][0];
  expect(typeof msg).toBe("string");
  expect(msg).not.toContain("re_secret");
});

test("recipient lookup failure shows friendly message and sends nothing", async () => {
  api.get.mockRejectedValueOnce(new Error("Network Error"));
  render(<WeeklyDropPreviewButton/>);
  fireEvent.click(screen.getByTestId("weekly-drop-preview"));
  await waitFor(() => expect(toast.error).toHaveBeenCalled());
  expect(api.post).not.toHaveBeenCalled();
  expect(window.confirm).not.toHaveBeenCalled();
});

test("button disables while sending and cannot double-submit", async () => {
  recipient();
  let resolve;
  api.post.mockReturnValueOnce(new Promise((r) => { resolve = r; }));
  render(<WeeklyDropPreviewButton/>);
  const btn = screen.getByTestId("weekly-drop-preview");
  fireEvent.click(btn);
  await waitFor(() => expect(btn).toBeDisabled());
  expect(btn).toHaveTextContent("Sending preview…");
  fireEvent.click(btn); fireEvent.click(btn);
  await waitFor(() => expect(api.post).toHaveBeenCalledTimes(1));
  expect(api.get).toHaveBeenCalledTimes(1);
  resolve({ data: { ok: true, provider: "resend", recipient: PREVIEW, recipe: "X" } });
  await waitFor(() => expect(btn).not.toBeDisabled());
  expect(btn).toHaveTextContent("Send preview to me");
});
