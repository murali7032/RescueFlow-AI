import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

describe("Recipient App", () => {
  it("renders invitation inbox chrome", () => {
    render(<App />);
    expect(screen.getByText(/Recipient inbox/i)).toBeTruthy();
    expect(screen.getByRole("heading", { name: /Invitations/i })).toBeTruthy();
  });
});
