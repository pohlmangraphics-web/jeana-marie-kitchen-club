import { errorMessage } from "./api";

const mk = (detail, status = 422) => ({ response: { status, data: { detail } } });

test("string detail passes through", () => {
  expect(errorMessage(mk("Invalid or expired token", 400))).toBe("Invalid or expired token");
});

test("pydantic 422 array is flattened to a string, never an object", () => {
  const msg = errorMessage(mk([{ type: "string_too_short", loc: ["body", "new_password"],
    msg: "String should have at least 8 characters", input: "short", ctx: { min_length: 8 } }]));
  expect(typeof msg).toBe("string");
  expect(msg).toBe("Password must have at least 8 characters");
});

test("multiple field errors join", () => {
  const msg = errorMessage(mk([
    { loc: ["body", "email"], msg: "value is not a valid email address: An email address must have an @-sign." },
    { loc: ["body", "password"], msg: "String should have at least 8 characters" },
  ]));
  expect(msg).toContain("Email value is not a valid email address");
  expect(msg).toContain("Password must have at least 8 characters");
});

test("single object detail with msg", () => {
  expect(errorMessage(mk({ type: "x", loc: [], msg: "Bad thing", input: null, ctx: {} }))).toBe("Bad thing");
});

test("unknown shapes fall back", () => {
  expect(errorMessage(mk({ weird: 1 }), "Reset failed")).toBe("Reset failed");
  expect(errorMessage(mk(null, 500), "Reset failed")).toBe("Reset failed");
  expect(errorMessage(undefined, "Reset failed")).toBe("Reset failed");
  expect(errorMessage({}, "Reset failed")).toBe("Reset failed");
});

test("429 and network errors are friendly", () => {
  expect(errorMessage(mk(null, 429))).toMatch(/Too many attempts/);
  expect(errorMessage({ message: "Network Error" })).toMatch(/Can't reach the server/);
});

test("result is always a string for arbitrary inputs", () => {
  for (const d of [[], [{}], [{ loc: null, msg: 5 }], 42, true, [[1, 2]]]) {
    expect(typeof errorMessage(mk(d), "fallback")).toBe("string");
  }
});
