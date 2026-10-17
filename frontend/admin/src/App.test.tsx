import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("Admin App", () => {
  it("renders dashboard and demo controls", () => {
    render(<App />);
    expect(screen.getByText(/Operations dashboard/i)).toBeTruthy();
    expect(screen.getByText(/Seed demo/i)).toBeTruthy();
    expect(
      screen.getByText(/Allocated portions are not meals served/i)
    ).toBeTruthy();
  });
});
