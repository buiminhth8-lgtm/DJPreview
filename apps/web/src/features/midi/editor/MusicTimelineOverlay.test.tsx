import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TimelineHeader } from "./TimelineHeader";

const sections = [
  { id: "intro", name: "Intro", startBar: 1, bars: 2, startTick: 0, endTick: 3840, energy: 0.3 },
  { id: "verse", name: "Verse", startBar: 3, bars: 2, startTick: 3840, endTick: 7680, energy: 0.7 },
];
const chords = [
  { sectionId: "intro", symbol: "C", bar: 1, startTick: 0, endTick: 1920 },
  { sectionId: "intro", symbol: "G", bar: 2, startTick: 1920, endTick: 3840 },
];

describe("MusicTimelineOverlay", () => {
  it("shares canonical tick geometry with playhead and seeks from a section marker", () => {
    const onSeek = vi.fn();
    const { rerender } = render(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.5}
        currentTick={3840}
        sections={sections}
        chords={chords}
        showSections
        showChords
        onSeek={onSeek}
      />,
    );
    expect(screen.getByTestId("timeline-playhead")).toHaveStyle({ left: "1920px" });
    expect(document.querySelector('[data-section-id="verse"]')).toHaveStyle({ left: "1920px", width: "1920px" });
    expect(document.querySelector('[data-chord="G"]')).toHaveStyle({ left: "960px", width: "960px" });
    fireEvent.click(screen.getByRole("button", { name: "Verse" }));
    expect(onSeek).toHaveBeenCalledWith(3840);
    rerender(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.8}
        currentTick={3840}
        sections={sections}
        chords={chords}
        showSections
        showChords
        onSeek={onSeek}
      />,
    );
    expect(screen.getByTestId("timeline-playhead")).toHaveStyle({ left: "3072px" });
    expect(document.querySelector('[data-section-id="verse"]')).toHaveStyle({ left: "3072px" });
  });

  it("hides only the requested overlay without changing the timeline", () => {
    const { rerender } = render(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.5}
        sections={sections}
        chords={chords}
        showSections={false}
        showChords
      />,
    );
    expect(screen.queryByTestId("section-overlay")).toBeNull();
    expect(screen.getByTestId("chord-overlay")).toBeInTheDocument();
    rerender(
      <TimelineHeader
        ppq={480}
        meter={{ numerator: 4, denominator: 4 }}
        maxTick={7680}
        pixelsPerTick={0.5}
        sections={sections}
        chords={chords}
        showSections
        showChords={false}
      />,
    );
    expect(screen.getByTestId("section-overlay")).toBeInTheDocument();
    expect(screen.queryByTestId("chord-overlay")).toBeNull();
    expect(screen.getByRole("slider", { name: /MIDI 时间轴/ })).toBeInTheDocument();
  });
});
