import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { EmailProviderStatus, describeEmailStatus } from "./EmailProviderStatus";
import { api } from "../lib/api";

jest.mock("../lib/api", () => ({ api: { get: jest.fn() } }));

const ok = (data) => api.get.mockResolvedValueOnce({ data });

afterEach(() => jest.clearAllMocks());

test("Resend active", async () => {
  ok({ use_resend: true, resend_key_present: true, resend_active: true, provider_in_use: "resend" });
  render(<EmailProviderStatus/>);
  await waitFor(() => expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email: Resend"));
  expect(screen.getByTestId("email-provider-status")).toHaveAttribute("data-state", "resend");
  expect(screen.queryByTestId("email-provider-note")).toBeNull();
  expect(api.get).toHaveBeenCalledWith("/admin/email/status");
});

test("Emergent when Resend disabled", async () => {
  ok({ use_resend: false, resend_key_present: true, resend_active: false, provider_in_use: "emergent" });
  render(<EmailProviderStatus/>);
  await waitFor(() => expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email: Emergent"));
  expect(screen.getByTestId("email-provider-status")).toHaveAttribute("data-state", "emergent");
});

test("warning when use_resend=true but inactive", async () => {
  ok({ use_resend: true, resend_key_present: false, resend_active: false, provider_in_use: "emergent" });
  render(<EmailProviderStatus/>);
  await waitFor(() => expect(screen.getByTestId("email-provider-status")).toHaveAttribute("data-state", "warning"));
  expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email: Emergent (fallback)");
  expect(screen.getByTestId("email-provider-note")).toHaveTextContent(/not active/);
});

test("request failure shows unavailable without crashing", async () => {
  api.get.mockRejectedValueOnce({ response: { status: 500, data: { detail: [{ type: "x", loc: [], msg: "boom" }] } } });
  render(<EmailProviderStatus/>);
  await waitFor(() => expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email status unavailable"));
  expect(screen.getByTestId("email-provider-status")).toHaveAttribute("data-state", "unavailable");
  expect(screen.getByTestId("email-provider-status")).not.toHaveTextContent("boom");
});

test("refresh re-queries and recovers", async () => {
  api.get.mockRejectedValueOnce(new Error("Network Error"));
  render(<EmailProviderStatus/>);
  await waitFor(() => expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email status unavailable"));
  ok({ use_resend: true, resend_key_present: true, resend_active: true, provider_in_use: "resend" });
  fireEvent.click(screen.getByTestId("email-provider-refresh"));
  await waitFor(() => expect(screen.getByTestId("email-provider-label")).toHaveTextContent("Email: Resend"));
  expect(api.get).toHaveBeenCalledTimes(2);
});

test("describeEmailStatus never leaks values", () => {
  const s = describeEmailStatus({ use_resend: true, resend_active: true, resend_key_present: true, secret: "re_abc" });
  expect(JSON.stringify(s)).not.toContain("re_abc");
});
