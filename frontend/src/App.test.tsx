import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

vi.mock("@foodbridge/shared/api/client", async () => {
  const actual = await vi.importActual<typeof import("@foodbridge/shared/api/client")>(
    "@foodbridge/shared/api/client"
  );
  return {
    ...actual,
    createApiClient: () => ({
      get: vi.fn().mockRejectedValue(new Error("offline")),
      post: vi.fn(),
      patch: vi.fn(),
    }),
  };
});

describe("Unified RescueFlow app", () => {
  it("renders shell navigation and dashboard", () => {
    render(<App />);
    expect(screen.getByText(/RescueFlow AI/i)).toBeTruthy();
    expect(screen.getByRole("navigation", { name: /Primary/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Dashboard$/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Donor Workspace$/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Recipient Workspace$/i })).toBeTruthy();
    expect(screen.getByRole("link", { name: /^Admin Dashboard$/ })).toBeTruthy();
    expect(screen.getByRole("heading", { name: /^Dashboard$/i })).toBeTruthy();
  });

  it("shows allocated vs pickup distinction on dashboard", () => {
    render(<App />);
    expect(
      screen.getByText(/Allocated ≠ pickup confirmed ≠ pickup completed/i)
    ).toBeTruthy();
  });

  it("shows dev demo role switcher in development", () => {
    render(<App />);
    expect(screen.getByText(/Dev demo role/i)).toBeTruthy();
  });
});
