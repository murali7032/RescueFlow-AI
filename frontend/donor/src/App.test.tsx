import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("Donor App", () => {
  it("renders donation form validation cues", () => {
    render(<App />);
    expect(screen.getByText(/Donor workspace/i)).toBeTruthy();
    expect(screen.getByText(/Publish & match/i)).toBeTruthy();
    expect(screen.getByLabelText(/Portions/i)).toBeTruthy();
  });
});
