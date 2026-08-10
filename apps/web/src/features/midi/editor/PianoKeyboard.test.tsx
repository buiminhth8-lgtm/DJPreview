import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PianoKeyboard } from "./PianoKeyboard";

describe("PianoKeyboard semantics", () => {
  it("aligns top-to-bottom pitch order with the roll", () => {
    render(<PianoKeyboard minPitch={60} maxPitch={62} rowHeight={12} />);
    expect(Array.from(document.querySelectorAll("[data-midi-pitch]")).map((row) => row.getAttribute("data-midi-pitch"))).toEqual([
      "62", "61", "60",
    ]);
  });

  it("renders canonical GM semantic labels for a drum track", () => {
    render(<PianoKeyboard minPitch={36} maxPitch={51} rowHeight={12} isDrum />);
    for (const label of ["Kick", "Snare", "Closed Hat", "Open Hat", "Crash", "Ride"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(document.querySelector('[data-midi-pitch="36"]')).toHaveTextContent("Kick");
    expect(document.querySelector('[data-midi-pitch="51"]')).toHaveTextContent("Ride");
  });
});
